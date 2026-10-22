"""Opt-in report regression over an archived observation, without raw-save helpers."""
import os
from pathlib import Path
import tempfile
import unittest

from devkit.common import read_json
from devkit.reporting import analyze_run


@unittest.skipUnless(os.environ.get('HBE_OBSERVATION_PROFILE') and os.environ.get('HBE_OBSERVATION_REFERENCE'),
                     'Set HBE_OBSERVATION_PROFILE and HBE_OBSERVATION_REFERENCE for archived-run regression')
class ObservationReportIntegrationTests(unittest.TestCase):
    def test_all_points_personalities_and_archived_state(self):
        root = Path(__file__).resolve().parents[1]
        profile = Path(os.environ['HBE_OBSERVATION_PROFILE'])
        expected = read_json(os.environ['HBE_OBSERVATION_REFERENCE'])
        original_status = (profile / 'status.json').read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            report = analyze_run(profile, output=tmp, cache_dir=root / 'work/save-cache')
            self.assertEqual(report['analysis_errors'], [])
            self.assertEqual([s['date'] for s in report['snapshots']], [s['date'] for s in expected['snapshots']])
            for actual, previous in zip(report['snapshots'], expected['snapshots']):
                with self.subTest(date=actual['date']):
                    self.assertEqual(actual['playthrough_id'], previous['playthrough_id'])
                    for field in ('alive', 'completed_all', 'completed_live', 'active', 'paused', 'locations',
                                  'gold_total', 'population_total', 'burden_mean', 'burden_max', 'buildings', 'wars'):
                        self.assertAlmostEqual(actual['summary'][field], previous['summary'][field], delta=.0051, msg=field)
            last = expected['snapshots'][-1]
            for label, row in report['projects']['personalities'].items():
                self.assertEqual(row['eligible'], last['personalities'][label]['eligible'])
                self.assertEqual(row['accepted'], last['personalities'][label]['accepted'])
            self.assertEqual(report['run_state'], 'stopped_by_user')
            self.assertFalse(report['observation']['target_reached'])
            self.assertEqual(report['engine']['wrapper_status'], 'failed')
            self.assertEqual(original_status, (profile / 'status.json').read_bytes())


if __name__ == '__main__': unittest.main()
