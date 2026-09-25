from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    PROFILE_2026_CODE,
    PROFILE_2026_EDITION,
    PROFILE_CODE,
    PROFILE_EDITION,
    post_init_hook,
)


@tagged("-at_install", "post_install")
class TestPmQmsIso9001TransitionScenarios(TransactionCase):
    def setUp(self):
        super().setUp()
        post_init_hook(self.env)

    def test_2015_and_2026_profiles_coexist_without_approved_mappings(self):
        profiles = self.env["pm.qms.mapping.profile"].search(
            [("standard_name", "=", "ISO 9001"), ("company_id", "=", self.env.company.id)]
        )
        self.assertEqual(
            {(profile.code, profile.edition) for profile in profiles},
            {(PROFILE_CODE, PROFILE_EDITION), (PROFILE_2026_CODE, PROFILE_2026_EDITION)},
        )
        self.assertFalse(any(profile.mapping_ids.filtered(lambda mapping: mapping.review_status == "approved") for profile in profiles))

    def test_all_supported_transition_scenarios_target_2026_profile(self):
        scenarios = self.env["pm.qms.iso9001.transition.scenario"].search(
            [("company_id", "=", self.env.company.id), ("state", "=", "active")]
        )
        self.assertEqual(len(scenarios), 8)
        self.assertEqual(
            {scenario.scenario_type for scenario in scenarios},
            {"initial", "transition", "legacy", "recertification", "scope_expansion", "multi_site", "integrated", "partial"},
        )
        self.assertTrue(all(scenario.target_edition == "2026" for scenario in scenarios))
        self.assertTrue(all(scenario.profile_id.code == PROFILE_2026_CODE for scenario in scenarios))

    def test_scenario_seed_is_idempotent(self):
        post_init_hook(self.env)
        Scenario = self.env["pm.qms.iso9001.transition.scenario"]
        self.assertEqual(
            Scenario.search_count([("company_id", "=", self.env.company.id)]),
            8,
        )
