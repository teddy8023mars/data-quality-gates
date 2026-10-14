"""Export a fixed synthetic run directly from the public evaluator."""
import json
from pathlib import Path
from data_quality_gates import evaluate
from data_quality_gates.engine import read_csv

ROOT = Path(__file__).resolve().parents[1]
REFERENCE_TIME = '2026-10-15T12:00:00Z'
LABELS = ['ID present', 'ID unique', 'Score bounds', 'Allowed team', 'Team reference', 'Freshness']
DESCRIPTIONS = ['ID cannot be blank or whitespace.', 'Every ID after its first occurrence is a violation.', 'Score must be a finite number from 0 to 100, inclusive.', 'Team must be exactly red or blue.', 'Team must exist in the synthetic teams.csv reference.', 'Timestamp must include a timezone and be between 0 and 3,600 seconds old.']


def build():
    contract = json.loads((ROOT / 'examples/contract.json').read_text())
    result = {'synthetic': True, 'reference_time': REFERENCE_TIME, 'contract': contract, 'fixtures': {}}
    for fixture in ('clean', 'dirty'):
        path = ROOT / f'examples/{fixture}.csv'
        report = evaluate(contract, path, REFERENCE_TIME, ROOT / 'examples')
        columns, rows = read_csv(path)
        records = [{'record': n, 'values': row} for n, row in enumerate(rows, 2)]
        checks = []
        for check, label, description in zip(report['checks'], LABELS, DESCRIPTIONS):
            checks.append({**check, 'label': label, 'description': description,
                           'samples': [record for record in records if record['record'] in check['rows']]})
        union = sorted({n for check in checks for n in check['rows']})
        result['fixtures'][fixture] = {'report': report, 'exit_code': 0 if report['status'] == 'passed' else 1,
                                      'columns': columns, 'records': records, 'checks': checks,
                                      'violation_total': sum(c['violations'] for c in checks),
                                      'distinct_bad_records': union, 'distinct_bad_count': len(union)}
    return result


if __name__ == '__main__':
    target = ROOT / 'docs/showcase-data.json'
    target.write_text(json.dumps(build(), indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {target}')
