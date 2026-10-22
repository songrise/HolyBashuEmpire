"""Adapter regressions using a fake SDK and real local fixture assets."""
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from devkit.common import read_json, write_json
from devkit.media import compose, check_preserved
from devkit.steam import Steam
from devkit.telemetry import instrument_affairs
from devkit.reporting import controlled_assertions


class AdapterTests(unittest.TestCase):
    def test_low_level_content_update_has_no_description_or_presentation_setters(self):
        steam = Steam.__new__(Steam)
        steam.app_id, steam.item_id, steam.ugc = 1, 2, 3
        calls = []
        def function(name, *signature):
            def call(*args):
                calls.append((name, args))
                return 99 if name in ('ISteamUGC_StartItemUpdate', 'ISteamUGC_SubmitItemUpdate') else True
            return call
        steam.f = function
        steam.wait = lambda call: (0, struct.pack('<i?', 1, False))
        steam.submit(content='distribution', metadata='{}', note='content only')
        names = [name for name, _ in calls]
        self.assertIn('ISteamUGC_SetItemContent', names)
        self.assertFalse(any('Description' in n or 'Preview' in n or 'Visibility' in n or 'Title' in n for n in names))
        steam.wait = lambda call: (0, struct.pack('<i?', 1, True))
        with self.assertRaisesRegex(RuntimeError, 'legal'):
            steam.submit(content='distribution', note='test')

    def test_description_update_language_and_no_content(self):
        steam = Steam.__new__(Steam); steam.app_id, steam.item_id, steam.ugc = 1, 2, 3
        names = []
        steam.f = lambda name, *sig: lambda *args: names.append(name) or 99
        steam.wait = lambda call: (0, struct.pack('<i?', 1, False))
        steam.submit(description='测试说明', language='schinese', note='description')
        self.assertLess(names.index('ISteamUGC_SetItemUpdateLanguage'), names.index('ISteamUGC_SetItemDescription'))
        self.assertNotIn('ISteamUGC_SetItemContent', names)

    def test_passive_probe_source_unchanged_and_anchor_failure_is_atomic(self):
        root = Path(__file__).resolve().parents[1]
        source = root / 'mod/holy_bashu_empire/in_game/common/scripted_effects/hbe_af_effects.txt'
        original = source.read_bytes()
        catalogue = read_json(root / 'data/local_affairs_projects.json')
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp); target = mod / source.relative_to(root / 'mod/holy_bashu_empire')
            target.parent.mkdir(parents=True); target.write_bytes(original)
            result = instrument_affairs(mod, catalogue)
            self.assertIn('hbe_probe_eligible_active', result['counters'])
            self.assertNotIn('hbe_probe_peak_burden', result['counters'])
            self.assertEqual(source.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'already'): instrument_affairs(mod, catalogue)
            bad = original.replace(b'hbe_af_initialize', b'hbe_af_removed')
            target.write_bytes(bad)
            with self.assertRaisesRegex(ValueError, 'Initialization'): instrument_affairs(mod, catalogue)
            self.assertEqual(target.read_bytes(), bad)

    def test_controlled_rules_distinguish_absence_zero_and_missing_country(self):
        definitions = [dict(name='set', country='A', variable='flag', equals=True),
                       dict(name='not failed', country='A', variable='failed', absent=True)]
        snapshot = dict(countries=[dict(tag='A', alive=True, variables=dict(flag=True))])
        self.assertEqual(controlled_assertions(snapshot, definitions)['status'], 'passed')
        snapshot['countries'][0]['variables']['failed'] = 0
        self.assertEqual(controlled_assertions(snapshot, definitions)['status'], 'failed')
        self.assertEqual(controlled_assertions(None, definitions)['status'], 'failed')

    def test_media_composition_changes_only_declared_box_and_rejects_wrong_dimensions(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = Image.new('RGB', (80, 60), (230, 220, 190)); base.save(root / 'base.png')
            Image.new('RGB', (10, 20), (30, 40, 50)).save(root / 'shot.png')
            spec = dict(schema_version=1, base='base.png', size=[80, 60],
                        operations=[dict(type='inset', source='shot.png', box=[10, 10, 40, 50])])
            write_json(root / 'template.json', spec)
            result = compose(root / 'template.json', root / 'result')
            self.assertTrue(result['outside_regions_pixel_identical'])
            with Image.open(root / 'result.png') as image:
                check_preserved(base, image, [[10, 10, 40, 50]])
            with self.assertRaises(FileExistsError): compose(root / 'template.json', root / 'result')
            spec['size'] = [90, 60]; write_json(root / 'template.json', spec)
            with self.assertRaisesRegex(ValueError, 'dimensions'): compose(root / 'template.json', root / 'other')

    def test_process_identity_can_read_own_windows_process_without_cim(self):
        import os
        if os.name != 'nt': self.skipTest('Windows process API')
        from devkit.processes import identity, command_arguments
        info = identity(os.getpid())
        self.assertEqual(info['pid'], os.getpid())
        self.assertTrue(info['created'])
        self.assertIn('python', info['executable'].lower())
        self.assertTrue(command_arguments(info['command_line']))


if __name__ == '__main__': unittest.main()
