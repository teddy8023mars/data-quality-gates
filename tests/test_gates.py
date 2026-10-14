"""Literal expectations catch skipped validation, wrong boundaries, and exit-code conflation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from data_quality_gates import ConfigError, InputError, evaluate

NOW = '2026-10-15T12:00:00+00:00'


def contract():
    return {'version': 1, 'required_columns': ['id', 'score', 'team', 'updated_at'],
            'empty_policy': 'fail', 'checks': [
                {'id': 'id_present', 'type': 'not_null', 'columns': ['id']},
                {'id': 'id_unique', 'type': 'unique', 'columns': ['id']},
                {'id': 'score_bounds', 'type': 'numeric_range', 'column': 'score', 'min': 0, 'max': 100},
                {'id': 'team_values', 'type': 'allowed_values', 'column': 'team', 'values': ['red', 'blue']},
                {'id': 'team_fk', 'type': 'foreign_key', 'column': 'team', 'reference_file': 'teams.csv', 'reference_column': 'team'},
                {'id': 'fresh', 'type': 'freshness', 'column': 'updated_at', 'max_age_seconds': 3600}]}


class GatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        (self.base / 'teams.csv').write_text('team\nred\nblue\n', encoding='utf-8')
        self.data = self.base / 'data.csv'

    def run_data(self, rows, cfg=None, now=NOW):
        self.data.write_text('id,score,team,updated_at\n' + rows, encoding='utf-8')
        return evaluate(cfg or contract(), self.data, now, self.base)

    def test_clean_inclusive_bounds_and_timezone_conversion(self):
        report = self.run_data('a,0,red,2026-10-15T19:00:00+08:00\nb,100,blue,2026-10-15T12:00:00Z\n')
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['rows'], 2)
        self.assertEqual([c['violations'] for c in report['checks']], [0, 0, 0, 0, 0, 0])

    def test_dirty_has_exact_violation_records(self):
        report = self.run_data('a,101,green,2026-10-15T10:00:00Z\na,bad,red,2026-10-15T12:00:01Z\n ,NaN,,2026-10-15T12:00:00\n')
        self.assertEqual(report['status'], 'failed')
        self.assertEqual([c['violations'] for c in report['checks']], [1, 1, 3, 2, 2, 3])
        self.assertEqual(report['checks'][1]['rows'], [3])
        self.assertEqual(report['checks'][5]['rows'], [2, 3, 4])

    def test_empty_policy_and_zero_byte_file(self):
        self.assertEqual(self.run_data('')['status'], 'failed')
        cfg = contract(); cfg['empty_policy'] = 'allow'
        self.assertEqual(self.run_data('', cfg)['status'], 'passed')
        self.data.write_text('')
        with self.assertRaises(InputError):
            evaluate(cfg, self.data, NOW, self.base)

    def test_missing_schema_is_quality_failure(self):
        self.data.write_text('id\na\n')
        report = evaluate(contract(), self.data, NOW, self.base)
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['missing_columns'], ['score', 'team', 'updated_at'])
        self.assertEqual(report['checks'], [])

    def test_bad_csv_shape_headers_and_utf8_are_input_errors(self):
        for text in ['id,id\na,b\n', 'id,\na,b\n', 'id,score,team,updated_at\na,1,red\n', 'id,score,team,updated_at\n"unterminated']:
            with self.subTest(text=text):
                self.data.write_text(text)
                with self.assertRaises(InputError): evaluate(contract(), self.data, NOW, self.base)
        self.data.write_bytes(b'\xff')
        with self.assertRaises(InputError): evaluate(contract(), self.data, NOW, self.base)

    def test_invalid_config_never_silently_passes(self):
        mutations = [lambda c: c.update(extra=True), lambda c: c.update(version=True),
                     lambda c: c.update(empty_policy='ignore'), lambda c: c.update(required_columns=[]),
                     lambda c: c['checks'][0].update(columns=[]), lambda c: c['checks'][0].update(type='typo'),
                     lambda c: c['checks'][0].update(columns=['absent']), lambda c: c['checks'][1].update(id='id_present'),
                     lambda c: c['checks'][2].update(min=True), lambda c: c['checks'][2].update(max=float('inf')),
                     lambda c: c['checks'][2].update(min=101), lambda c: c['checks'][3].update(values=[]),
                     lambda c: c['checks'][4].update(reference_column=''), lambda c: c['checks'][5].update(max_age_seconds=-1),
                     lambda c: c['checks'][5].update(extra=True)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                cfg = contract(); mutate(cfg)
                with self.assertRaises(ConfigError): self.run_data('', cfg)

    def test_invalid_reference_time_is_input_error(self):
        for now in ['2026-10-15T12:00:00', 'garbage', '2026-10-15']:
            with self.subTest(now=now):
                with self.assertRaises(InputError): self.run_data('', now=now)

    def test_nonfinite_and_malformed_numeric_values_fail_quality(self):
        report = self.run_data('a,Infinity,red,2026-10-15T12:00:00Z\nb,-1,red,2026-10-15T12:00:00Z\nc,,red,2026-10-15T12:00:00Z\n')
        self.assertEqual(report['checks'][2]['violations'], 3)

    def test_fk_missing_file_or_schema_is_input_error_even_empty(self):
        (self.base / 'teams.csv').unlink()
        with self.assertRaises(InputError): self.run_data('')
        (self.base / 'teams.csv').write_text('other\nred\n')
        with self.assertRaises(InputError): self.run_data('')

    def test_composite_unique_counts_subsequent_rows(self):
        cfg = contract(); cfg['checks'] = [{'id': 'pair', 'type': 'unique', 'columns': ['id', 'team']}]
        report = self.run_data('a,1,red,x\na,2,blue,x\na,3,red,x\n,4,blue,x\n ,5,blue,x\n', cfg)
        self.assertEqual(report['checks'][0]['rows'], [4, 6])

    def test_null_byte_reference_path_is_config_error(self):
        cfg = contract(); cfg['checks'][4]['reference_file'] = 'teams\x00.csv'
        with self.assertRaises(ConfigError): self.run_data('', cfg)

    def test_invalid_timezone_and_stale_boundary(self):
        report = self.run_data('a,1,red,2026-10-15T12:00:00+01:99\n'
                               'b,1,red,2026-10-15T12:00:00+24:00\n'
                               'c,1,red,2026-10-15T10:59:59.999999Z\n')
        self.assertEqual(report['checks'][5]['rows'], [2, 3, 4])

    def test_json_nonfinite_and_malformed_contract_errors(self):
        for text in ['{"version":NaN}', '{"version":Infinity}', '{bad', '[]']:
            with self.subTest(text=text):
                path = self.base/'bad.json'; path.write_text(text)
                proc = subprocess.run([sys.executable, '-m', 'data_quality_gates', '--contract', str(path), '--data', str(self.data), '--reference-time', NOW], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(json.loads(proc.stdout)['status'], 'config_error')

    def cli(self, cfg=contract(), rows='a,1,red,2026-10-15T12:00:00Z\n'):
        self.data.write_text('id,score,team,updated_at\n' + rows, encoding='utf-8')
        path = self.base / 'contract.json'; path.write_text(json.dumps(cfg))
        return subprocess.run([sys.executable, '-m', 'data_quality_gates', '--contract', str(path), '--data', str(self.data), '--reference-time', NOW, '--report', str(self.base/'report.json')], capture_output=True, text=True)

    def test_cli_exit_codes_and_report_file(self):
        for rows, expected in [('a,1,red,2026-10-15T12:00:00Z\n', 0), ('a,101,red,2026-10-15T12:00:00Z\n', 1)]:
            proc = self.cli(rows=rows)
            self.assertEqual(proc.returncode, expected, proc.stderr)
            self.assertEqual(json.loads(proc.stdout), json.loads((self.base/'report.json').read_text()))
        cfg = contract(); cfg['unexpected'] = True
        proc = self.cli(cfg)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)['status'], 'config_error')
        proc = self.cli(rows='a,1,red\n')
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(json.loads(proc.stdout)['status'], 'input_error')

    def test_cli_duplicate_json_keys_are_config_error(self):
        path = self.base/'contract.json'; path.write_text('{"version":1,"version":1}')
        proc = subprocess.run([sys.executable, '-m', 'data_quality_gates', '--contract', str(path), '--data', str(self.data), '--reference-time', NOW], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)['status'], 'config_error')


if __name__ == '__main__': unittest.main()
