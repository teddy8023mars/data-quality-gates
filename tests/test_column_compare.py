import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from data_quality_gates import evaluate, ConfigError

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-15T12:00:00Z'

class ColumnCompareTests(unittest.TestCase):
    def contract(self, op='<='):
        return {'version': 1, 'required_columns': ['left', 'right'], 'empty_policy': 'allow',
                'checks': [{'id': 'comparison', 'type': 'column_compare',
                            'left_column': 'left', 'right_column': 'right', 'operator': op}]}

    def report(self, text, contract):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.csv'
            path.write_text(text)
            return evaluate(contract, path, NOW, directory)

    def test_inclusive_numeric_comparisons(self):
        for op, expected in [('<=', [4]), ('>=', [2]), ('==', [2, 4])]:
            with self.subTest(op=op):
                result = self.report('left,right\n2,3\n3,3\n4,3\n10,1e1\n', self.contract(op))
                self.assertEqual(result['checks'][0]['rows'], expected)
                self.assertEqual(result['checks'][0]['violations'], len(expected))

    def test_bad_numeric_cells_fail_on_either_side(self):
        result = self.report('left,right\n,3\n2,NaN\nInf,3\n2,nope\n 2 , 3 \n', self.contract())
        self.assertEqual(result['checks'][0]['rows'], [2, 3, 4, 5])
        self.assertEqual(result['status'], 'failed')

    def test_invalid_configuration_rejected_even_for_empty_input(self):
        for change in [{'operator': '<'}, {'operator': []}, {'right_column': 'unknown'},
                       {'left_column': 'right'}, {'left_column': None}, {'expression': 'left <= right'}]:
            with self.subTest(change=change):
                contract = self.contract()
                contract['checks'][0].update(change)
                with self.assertRaises(ConfigError):
                    self.report('left,right\n', contract)
        contract = self.contract()
        del contract['checks'][0]['operator']
        with self.assertRaises(ConfigError):
            self.report('left,right\n', contract)

    def test_retention_cli_exposes_business_violation_and_exit_code(self):
        folder = ROOT / 'examples/moba-retention'
        for fixture, code, counts, records in [('clean', 0, [0]*7, []),
                                             ('dirty', 1, [0, 0, 0, 0, 0, 0, 1], [2])]:
            with self.subTest(fixture=fixture):
                proc = subprocess.run([sys.executable, '-m', 'data_quality_gates',
                    '--contract', str(folder / 'contract.json'), '--data', str(folder / (fixture+'.csv')),
                    '--reference-time', NOW], capture_output=True, text=True,
                    env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')})
                self.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
                report = json.loads(proc.stdout)
                self.assertEqual(report['rows'], 8)
                self.assertEqual([check['violations'] for check in report['checks']], counts)
                self.assertEqual(report['checks'][-1]['rows'], records)

if __name__ == '__main__':
    unittest.main()
