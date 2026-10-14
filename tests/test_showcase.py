"""Verify exported evidence against literal fixture expectations."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_showcase', ROOT / 'scripts/build_showcase.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ShowcaseTests(unittest.TestCase):
    def test_dirty_counts_and_exact_samples(self):
        data = exporter.build()
        dirty = data['fixtures']['dirty']
        self.assertEqual(dirty['exit_code'], 1)
        self.assertEqual(dirty['report']['status'], 'failed')
        self.assertEqual([c['violations'] for c in dirty['checks']], [1, 1, 3, 2, 2, 3])
        self.assertEqual([c['rows'] for c in dirty['checks']], [[4], [3], [2, 3, 4], [2, 4], [2, 4], [2, 3, 4]])
        self.assertEqual(dirty['violation_total'], 12)
        self.assertEqual(dirty['distinct_bad_records'], [2, 3, 4])
        self.assertEqual(dirty['distinct_bad_count'], 3)
        for check in dirty['checks']:
            self.assertEqual([s['record'] for s in check['samples']], check['rows'])
        self.assertEqual(dirty['checks'][0]['samples'][0]['values']['id'], ' ')
        self.assertEqual(dirty['checks'][2]['samples'][1]['values']['score'], 'bad')
        self.assertEqual(dirty['checks'][5]['samples'][2]['values']['updated_at'], '2026-10-15T12:00:00')

    def test_clean_and_saved_export_are_reproducible(self):
        data = exporter.build()
        clean = data['fixtures']['clean']
        self.assertEqual(clean['exit_code'], 0)
        self.assertEqual(clean['report']['status'], 'passed')
        self.assertEqual(clean['report']['rows'], 2)
        self.assertEqual(clean['distinct_bad_records'], [])
        self.assertEqual(clean['violation_total'], 0)
        self.assertTrue(all(c['samples'] == [] for c in clean['checks']))
        self.assertEqual(data['reference_time'], '2026-10-15T12:00:00Z')
        self.assertEqual(json.loads((ROOT / 'docs/showcase-data.json').read_text()), data)
