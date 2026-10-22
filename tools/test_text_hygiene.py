"""Unit tests for the retired-wording scan (no repository files touched)."""
import unittest

from validate_text_hygiene import scan_text


class RetiredWordingTest(unittest.TestCase):
    def test_concept_link(self):
        self.assertTrue(scan_text("x [Concept('hbe_term_water', '水权储备')|e] y"))

    def test_icon(self):
        self.assertTrue(scan_text("x @hbe_salt! y"))

    def test_concept_definition(self):
        self.assertTrue(scan_text(' game_concept_hbe_term_river: "江运互保"'))

    def test_old_rule_sentence(self):
        self.assertTrue(scan_text(' game_concept_hbe_term_grain_desc: "开局20，上限100。"'))

    def test_current_wording_passes(self):
        self.assertFalse(scan_text(' hbe_BAE_scenario_desc: "以真实渠务办成本圈地方事业。"'))


if __name__ == '__main__':
    unittest.main()
