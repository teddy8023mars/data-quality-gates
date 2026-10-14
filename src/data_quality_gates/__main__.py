"""CLI: JSON to stdout and optionally a report file; documented exit taxonomy."""
import argparse
import json
from pathlib import Path
from .engine import ConfigError, InputError, evaluate


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def reject_constant(value):
    raise ConfigError(f'non-finite JSON number: {value}')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Evaluate declarative CSV quality gates.')
    parser.add_argument('--contract', required=True, type=Path)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--reference-time', required=True)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    try:
        try:
            contract = json.loads(args.contract.read_text(encoding='utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConfigError(f'invalid contract: {exc}') from exc
        report = evaluate(contract, args.data, args.reference_time, args.contract.parent)
        code = 0 if report['status'] == 'passed' else 1
    except ConfigError as exc:
        report, code = {'status': 'config_error', 'error': str(exc)}, 2
    except InputError as exc:
        report, code = {'status': 'input_error', 'error': str(exc)}, 3
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    if args.report:
        try: args.report.write_text(rendered, encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            report, code = {'status': 'input_error', 'error': f'cannot write report: {exc}'}, 3
            rendered = json.dumps(report, indent=2) + '\n'
    print(rendered, end='')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
