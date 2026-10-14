"""Validate configuration before reading data, then evaluate every configured check."""
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re


class ConfigError(ValueError):
    """Contract cannot be interpreted safely."""


class InputError(ValueError):
    """Input cannot be read or parsed safely."""


TIMESTAMP = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$')
NUMBER = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$')


def aware_time(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ValueError('expected ISO8601 datetime with seconds and timezone')
    # datetime accepts +24:00 only via rejection and can normalize bad minutes;
    # enforce actual offset clock components rather than that normalization.
    if not value.endswith('Z') and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise ValueError('invalid timezone offset')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('timezone required')
    return parsed


def number(value):
    text = str(value).strip()
    if isinstance(value, bool) or not NUMBER.fullmatch(text):
        raise ValueError('expected finite decimal number')
    try:
        parsed = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError('expected finite decimal number') from exc
    if not parsed.is_finite():
        raise ValueError('expected finite decimal number')
    return parsed


def nonempty_string(value):
    return isinstance(value, str) and bool(value.strip())


def names(value):
    return isinstance(value, list) and bool(value) and all(nonempty_string(v) for v in value) and len(set(value)) == len(value)


def keys(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= obj.keys() or set(obj) - set(required) - set(optional):
        raise ConfigError('missing or unknown contract settings')


def validate_contract(contract):
    keys(contract, ('version', 'required_columns', 'empty_policy', 'checks'))
    if type(contract['version']) is not int or contract['version'] != 1:
        raise ConfigError('version must be integer 1')
    if not names(contract['required_columns']):
        raise ConfigError('required_columns must be nonempty distinct names')
    if contract['empty_policy'] not in ('fail', 'allow'):
        raise ConfigError('empty_policy must be fail or allow')
    if not isinstance(contract['checks'], list):
        raise ConfigError('checks must be a list')
    seen = set()
    specs = {
        'not_null': (('columns',), ()), 'unique': (('columns',), ()),
        'numeric_range': (('column',), ('min', 'max')),
        'allowed_values': (('column', 'values'), ()),
        'foreign_key': (('column', 'reference_file', 'reference_column'), ()),
        'freshness': (('column', 'max_age_seconds'), ())}
    for check in contract['checks']:
        if not isinstance(check, dict) or not isinstance(check.get('type'), str) or check['type'] not in specs:
            raise ConfigError('unknown check type')
        required, optional = specs[check['type']]
        keys(check, ('id', 'type') + required, optional)
        if not nonempty_string(check['id']) or check['id'] in seen:
            raise ConfigError('check ids must be nonempty and unique')
        seen.add(check['id'])
        columns = check.get('columns', [check.get('column')])
        if not names(columns) or any(c not in contract['required_columns'] for c in columns):
            raise ConfigError('check columns must exist in required_columns')
        kind = check['type']
        if kind == 'numeric_range':
            if 'min' not in check and 'max' not in check:
                raise ConfigError('numeric_range needs min or max')
            for key in ('min', 'max'):
                if key in check:
                    if type(check[key]) not in (int, float):
                        raise ConfigError('bounds must be JSON numbers')
                    try: number(check[key])
                    except ValueError as exc: raise ConfigError(str(exc)) from exc
            if 'min' in check and 'max' in check and number(check['min']) > number(check['max']):
                raise ConfigError('min must not exceed max')
        elif kind == 'allowed_values':
            if not names(check['values']):
                raise ConfigError('values must be nonempty distinct nonblank strings')
        elif kind == 'foreign_key':
            if not nonempty_string(check['reference_file']) or '\x00' in check['reference_file'] or not nonempty_string(check['reference_column']):
                raise ConfigError('reference file and column must be nonempty strings')
        elif kind == 'freshness':
            value = check['max_age_seconds']
            try:
                if type(value) not in (int, float) or number(value) < 0:
                    raise ValueError('max_age_seconds must be finite nonnegative number')
            except ValueError as exc: raise ConfigError(str(exc)) from exc


def read_csv(path):
    try:
        with Path(path).open(encoding='utf-8', newline='') as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, None)
            if not header or not all(nonempty_string(v) for v in header) or len(set(header)) != len(header):
                raise InputError(f'{path}: missing, blank or duplicate CSV headers')
            rows = []
            for record_number, values in enumerate(reader, 2):
                if len(values) != len(header):
                    raise InputError(f'{path}: CSV record {record_number} has wrong field count')
                rows.append(dict(zip(header, values)))
            return header, rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise InputError(f'{path}: {exc}') from exc


def null(value):
    return not value.strip()


def evaluate(contract, data_path, reference_time, base_dir):
    """Return a JSON-compatible report; throw on invalid config or unreadable inputs."""
    validate_contract(contract)
    try: now = aware_time(reference_time)
    except ValueError as exc: raise InputError(f'invalid reference time: {exc}') from exc
    references = {}
    for check in contract['checks']:
        if check['type'] == 'foreign_key':
            path = Path(base_dir) / check['reference_file']
            header, rows = read_csv(path)
            if check['reference_column'] not in header:
                raise InputError(f'{path}: missing reference column {check["reference_column"]}')
            references[check['id']] = {row[check['reference_column']] for row in rows if not null(row[check['reference_column']])}
    header, rows = read_csv(data_path)
    missing = [col for col in contract['required_columns'] if col not in header]
    report = {'status': 'passed', 'rows': len(rows), 'reference_time': now.isoformat(),
              'missing_columns': missing, 'empty_violation': not rows and contract['empty_policy'] == 'fail', 'checks': []}
    if missing or report['empty_violation']:
        report['status'] = 'failed'
    if missing:
        return report
    for check in contract['checks']:
        bad_rows = []
        seen = set()
        kind = check['type']
        for record, row in enumerate(rows, 2):
            value = row.get(check.get('column'))
            bad = False
            if kind == 'not_null':
                bad = any(null(row[col]) for col in check['columns'])
            elif kind == 'unique':
                key = tuple('' if null(row[col]) else row[col] for col in check['columns'])
                bad = key in seen
                seen.add(key)
            elif kind == 'numeric_range':
                try:
                    numeric = number(value)
                    bad = ('min' in check and numeric < number(check['min'])) or ('max' in check and numeric > number(check['max']))
                except ValueError: bad = True
            elif kind == 'allowed_values':
                bad = null(value) or value not in check['values']
            elif kind == 'foreign_key':
                bad = null(value) or value not in references[check['id']]
            elif kind == 'freshness':
                try:
                    delta = now - aware_time(value)
                    age = Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / Decimal(1000000)
                    bad = age < 0 or age > number(check['max_age_seconds'])
                except (ValueError, OverflowError): bad = True
            if bad: bad_rows.append(record)
        report['checks'].append({'id': check['id'], 'type': kind, 'violations': len(bad_rows), 'rows': bad_rows})
        if bad_rows: report['status'] = 'failed'
    return report
