"""Focused source-to-catalogue integrity checks; does not launch the game."""
import re
import unittest
from catalog import build_catalog, parse, field
from server import default_mod

class CatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = default_mod()
        cls.data = build_catalog(cls.mod)
        cls.events = {e['id']: e for e in cls.data['events']}

    def test_every_source_event_and_option_is_indexed(self):
        ids, option_count = [], 0
        for path in (self.mod / 'in_game/events').glob('*.txt'):
            text = path.read_text(encoding='utf-8-sig')
            ids += re.findall(r'(?m)^\s*(\w+\.\d+)\s*=\s*\{', text)
            option_count += len(re.findall(r'\boption\s*=\s*\{', text))
        self.assertEqual(sorted(ids), sorted(self.events))
        self.assertEqual(option_count, self.data['stats']['options'])

    def test_operators_repeated_keys_and_nested_scopes(self):
        nodes = parse('gold >= 6 x = 1 x = 2 scope:test ?= { if = { limit = { NOT = { flag = yes } } add_gold = 4 } }')
        self.assertEqual(nodes[0]['op'], '>=')
        self.assertEqual([n['value'] for n in nodes if n['key']=='x'], ['1','2'])
        self.assertEqual(nodes[-1]['op'], '?=')
        self.assertEqual(nodes[-1]['value'][0]['key'], 'if')

    def test_water_event_has_localized_tradeoffs_and_expanded_modifiers(self):
        e = self.events['hbe.100']
        self.assertEqual(e['title'], '争水')
        self.assertEqual(len(e['options']), 3)
        self.assertEqual(field(e['options'][1]['effects'], 'add_gold'), '-6')
        self.assertIn('gold >= 6', e['options'][1]['trigger'])
        self.assertIn('hbe_choice_chengdu_plain_2', self.data['definitions'])
        self.assertEqual(e['regions'], ['chengdu_plain'])
        self.assertTrue(e['incoming'])

    def test_maintenance_and_notification_remain_distinct(self):
        e = self.events['hbe_opening_family.1']
        self.assertTrue(e['hidden'])
        self.assertEqual(e['options'], [])
        self.assertTrue(e['immediate'])
        self.assertFalse(self.events['hbe.1']['hidden'])

    def test_no_missing_localization_and_valid_relations(self):
        self.assertFalse([w for w in self.data['warnings'] if '缺失' in w])
        for event in self.events.values():
            for target in event['outgoing']:
                self.assertIn(target, self.events)

    def test_scope_conditional_rewards_not_flattened(self):
        e = self.events['hbe_civic.100']['options'][2]['effects']
        scoped = next(n for n in e if n['key']=='every_owned_location')
        self.assertTrue(field(scoped['value'], 'limit'))
        self.assertTrue(field(scoped['value'], 'add_location_modifier'))

if __name__ == '__main__':
    unittest.main()
