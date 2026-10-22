"""Unit tests for the write-only variable scan."""
import unittest

from validate_variable_hygiene import orphans_in, unwritten_in, READ, WRITE


class VariableHygieneTest(unittest.TestCase):
    def test_plain_orphan(self):
        writes = {'hbe_a': {'x.txt'}}
        self.assertEqual(orphans_in(writes, {}), ['hbe_a'])

    def test_read_by_has_variable(self):
        self.assertEqual(orphans_in({'hbe_a': {'x.txt'}}, {'hbe_a': {'y.txt'}}), [])

    def test_deletion_is_not_a_read(self):
        reads = {name: {'legacy.txt'} for name in READ.findall('remove_variable = hbe_a')}
        self.assertEqual(orphans_in({'hbe_a': {'x.txt'}}, reads), ['hbe_a'])

    def test_retired_resources_have_no_exemption(self):
        self.assertEqual(orphans_in({'hbe_water': {'x.txt'}}, {}), ['hbe_water'])

    def test_sorted_output(self):
        self.assertEqual(orphans_in({'hbe_b': {'x'}, 'hbe_a': {'x'}}, {}), ['hbe_a', 'hbe_b'])

    def test_condition_read_without_writer(self):
        self.assertEqual(unwritten_in({}, {'hbe_a': {'x.txt'}}), ['hbe_a'])

    def test_condition_read_with_writer(self):
        self.assertEqual(unwritten_in({'hbe_a': {'x.txt'}}, {'hbe_a': {'x.txt'}}), [])

    def test_unwritten_legacy_conditions_have_no_exemption(self):
        self.assertEqual(unwritten_in({}, {'hbe_work_burst_cooldown': {'x.txt'}}), ['hbe_work_burst_cooldown'])

    def test_macro_prefix_is_not_a_standalone_variable(self):
        self.assertEqual(READ.findall('has_variable = hbe_opening_truce_$TAG$'), [])
        self.assertFalse(WRITE.search('set_variable = hbe_opening_truce_$TAG$'))

    def test_sorted_unwritten_output(self):
        self.assertEqual(unwritten_in({}, {'hbe_b': {'x'}, 'hbe_a': {'x'}}), ['hbe_a', 'hbe_b'])


if __name__ == '__main__':
    unittest.main()
