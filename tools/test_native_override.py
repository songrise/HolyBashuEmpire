"""Repeated builds accept formatting cleanup without accepting foreign gameplay."""
import unittest
from build_age2_military import supported_override


class NativeOverrideTest(unittest.TestCase):
    def test_finished_artifact_formatting_is_accepted(self):
        native = 'armory = {\n\n research_cost = 2\n}\n'
        patched = 'armory = {\n\n research_cost = 2\n unlock_unit = hbe_guard\n}\n'
        self.assertTrue(supported_override(patched.replace('\n\n','\n'), native, patched))
        self.assertTrue(supported_override(native, native, patched))

    def test_foreign_gameplay_change_is_rejected(self):
        native = 'armory = { research_cost = 2 }'
        patched = 'armory = { research_cost = 2 unlock_unit = hbe_guard }'
        self.assertFalse(supported_override(patched.replace('research_cost = 2','research_cost = 1'), native, patched))
        self.assertFalse(supported_override(patched+' extra = { unlock_unit = foreign_guard }', native, patched))


if __name__ == '__main__':
    unittest.main()
