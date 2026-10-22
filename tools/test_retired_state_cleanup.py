"""Removal must preserve current payment, award and initialization behavior."""
import unittest
from cleanup_retired_state import clean_script


class RetiredStateCleanupTest(unittest.TestCase):
    def test_obsolete_reward_does_not_remove_real_rewards(self):
        before='option = { add_gold = 5 change_variable = { name = hbe_contribution add = 1 } change_variable = { name = hbe_yiqi add = 2 } }'
        after=clean_script(before)
        self.assertNotIn('hbe_contribution',after)
        self.assertIn('add_gold = 5',after)
        self.assertIn('name = hbe_yiqi add = 2',after)

    def test_only_retired_cooldown_is_removed(self):
        after=clean_script('x = { if = { limit = { NOT = { at_war = yes } NOT = { has_variable = hbe_work_burst_cooldown } } change_variable = { name = hbe_burden add = -3 } } }')
        self.assertNotIn('hbe_work_burst_cooldown',after)
        self.assertIn('NOT = { at_war = yes }',after)
        self.assertIn('name = hbe_burden add = -3',after)

    def test_salary_debt_and_current_guards_survive(self):
        before='x = { set_variable = hbe_salt_debt remove_variable = hbe_af_credit_recorded set_variable = hbe_af_ai_last_month remove_variable = hbe_feast_helped }'
        after=clean_script(before)
        for key in ('hbe_salt_debt','hbe_af_credit_recorded','hbe_af_ai_last_month'):self.assertIn(key,after)
        self.assertNotIn('hbe_feast_helped',after)
        self.assertEqual(after,clean_script(after))

    def test_empty_chapter_branch_disappears(self):
        after=clean_script('x = { if = { limit = { current_year >= 1352 } set_variable = { name = hbe_chapter value = 2 } } hbe_open_accounts = yes }')
        self.assertNotIn('current_year',after)
        self.assertIn('hbe_open_accounts = yes',after)


if __name__=='__main__':unittest.main()
