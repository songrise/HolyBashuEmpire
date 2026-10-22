"""Unit tests for the retired-counter gate repair."""
import unittest

from build_local_affairs import unvacuum
from validate_local_affairs import implied_basis

OPERATING = {
    'chengdu_plain': ['hbe_operating_canal_office = yes', 'hbe_operating_brocade_school = yes'],
    'southern_salt_wine': ['hbe_operating_salt_office = yes'],
}
BASIS = {f'hbe_af_basis_{k}': {op.removesuffix(' = yes') for op in v} for k, v in OPERATING.items()}


class UnvacuumTest(unittest.TestCase):
    def test_implied_basis_becomes_completed_project(self):
        text = 'x = { limit = { hbe_operating_canal_office = yes hbe_af_basis_chengdu_plain = yes } }'
        out = unvacuum(text, OPERATING)
        self.assertIn('has_variable = hbe_af_done_chengdu_plain', out)
        self.assertNotIn('hbe_af_basis_chengdu_plain', out)

    def test_second_building_also_implies(self):
        text = 'x = { allow = { hbe_operating_brocade_school = yes hbe_af_basis_chengdu_plain = yes } }'
        self.assertIn('hbe_af_done_chengdu_plain', unvacuum(text, OPERATING))

    def test_basis_without_building_is_kept(self):
        text = 'x = { allow = { gold >= 5 hbe_af_basis_chengdu_plain = yes } }'
        self.assertEqual(unvacuum(text, OPERATING), text)

    def test_building_in_a_sibling_block_does_not_count(self):
        text = 'x = { a = { hbe_operating_canal_office = yes } b = { hbe_af_basis_chengdu_plain = yes } }'
        self.assertEqual(unvacuum(text, OPERATING), text)

    def test_only_the_matching_circle_is_rewritten(self):
        text = ('x = { limit = { hbe_operating_canal_office = yes '
                'hbe_af_basis_chengdu_plain = yes hbe_af_basis_southern_salt_wine = yes } }')
        out = unvacuum(text, OPERATING)
        self.assertIn('hbe_af_done_chengdu_plain', out)
        self.assertIn('hbe_af_basis_southern_salt_wine = yes', out)

    def test_unknown_circle_is_left_alone(self):
        text = 'x = { limit = { hbe_af_basis_valleys = yes } }'
        self.assertEqual(unvacuum(text, OPERATING), text)

    def test_no_basis_returns_the_same_object(self):
        text = 'x = { limit = { always = yes } }'
        self.assertEqual(unvacuum(text, OPERATING), text)


class ImpliedBasisTest(unittest.TestCase):
    def test_vacuous_gate_is_reported(self):
        text = 'x = { limit = { hbe_operating_canal_office = yes hbe_af_basis_chengdu_plain = yes } }'
        self.assertEqual(implied_basis([('f.txt', text)], BASIS), ['f.txt:hbe_af_basis_chengdu_plain'])

    def test_real_gate_is_not_reported(self):
        text = 'x = { allow = { gold >= 5 hbe_af_basis_chengdu_plain = yes } }'
        self.assertEqual(implied_basis([('f.txt', text)], BASIS), [])

    def test_building_in_a_sibling_block_is_not_reported(self):
        text = 'x = { a = { hbe_operating_canal_office = yes } b = { hbe_af_basis_chengdu_plain = yes } }'
        self.assertEqual(implied_basis([('f.txt', text)], BASIS), [])

    def test_files_without_basis_are_skipped(self):
        self.assertEqual(implied_basis([('f.txt', 'x = { always = yes }')], BASIS), [])


if __name__ == '__main__':
    unittest.main()
