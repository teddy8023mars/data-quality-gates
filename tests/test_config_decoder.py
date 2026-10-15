"""Malformed contract files must keep the public CLI error taxonomy."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConfigDecoderTests(unittest.TestCase):
    def check_contract(self, raw):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            contract = folder / 'contract.json'
            contract.write_text(raw)
            data = folder / 'rows.csv'
            data.write_text('id\na\n')
            report = folder / 'report.json'
            proc = subprocess.run([sys.executable, '-m', 'data_quality_gates',
                                   '--contract', str(contract), '--data', str(data),
                                   '--reference-time', '2026-10-15T05:37:22Z', '--report', str(report)],
                                  cwd=folder, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'),
                                                   'PYTHONINTMAXSTRDIGITS': '4300'},
                                  capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
            parsed = json.loads(proc.stdout)
            self.assertEqual(parsed['status'], 'config_error')
            self.assertTrue(parsed['error'])
            self.assertEqual(json.loads(report.read_text()), parsed)
            self.assertNotIn('Traceback', proc.stderr)

    def test_deep_contract_is_config_error(self):
        self.check_contract('[' * 20000 + '0' + ']' * 20000)

    def test_oversized_integer_is_config_error(self):
        self.check_contract('{"version":' + '9' * 10000 + '}')


if __name__ == '__main__':
    unittest.main()
