from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    PROFILE_2026_CODE,
    PROFILE_2026_EDITION,
    PROFILE_CODE,
    PROFILE_EDITION,
    post_init_hook,
    seed_iso9001_transition_scenarios,
)


EXPECTED_SCENARIO_SEQUENCES = {
    "ISO9001-2026-INITIAL": 10,
    "ISO9001-2026-TRANSITION-2015": 11,
    "ISO9001-2026-LEGACY": 12,
    "ISO9001-2026-RECERTIFICATION": 13,
    "ISO9001-2026-SCOPE-EXPANSION": 14,
    "ISO9001-2026-MULTI-SITE": 15,
    "ISO9001-2026-INTEGRATED": 16,
    "ISO9001-2026-PARTIAL": 17,
    "ISO9001-2026-RECERTIFICATION-SAME-EDITION": 18,
}


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
        self.assertFalse(
            any(
                profile.mapping_ids.filtered(lambda mapping: mapping.review_status == "approved")
                for profile in profiles
            )
        )

    def test_all_supported_transition_scenarios_target_2026_profile(self):
        scenarios = self.env["pm.qms.iso9001.transition.scenario"].search(
            [("company_id", "=", self.env.company.id), ("state", "=", "active")]
        )
        self.assertEqual(len(scenarios), 9)
        self.assertEqual(set(scenarios.mapped("code")), set(EXPECTED_SCENARIO_SEQUENCES))
        self.assertEqual(
            {scenario.scenario_type for scenario in scenarios},
            {
                "initial",
                "transition",
                "legacy",
                "recertification",
                "scope_expansion",
                "multi_site",
                "integrated",
                "partial",
            },
        )
        self.assertEqual(
            {scenario.code: scenario.sequence for scenario in scenarios},
            EXPECTED_SCENARIO_SEQUENCES,
        )
        self.assertTrue(all(scenario.target_edition == "2026" for scenario in scenarios))
        self.assertTrue(all(scenario.profile_id.code == PROFILE_2026_CODE for scenario in scenarios))

    def test_scenario_seed_is_idempotent(self):
        seed_iso9001_transition_scenarios(self.env)
        Scenario = self.env["pm.qms.iso9001.transition.scenario"]
        self.assertEqual(
            Scenario.search_count([("company_id", "=", self.env.company.id)]),
            9,
        )

    def test_upgrade_preserves_historical_scenario_sequences(self):
        Scenario = self.env["pm.qms.iso9001.transition.scenario"]
        existing = Scenario.search(
            [
                ("company_id", "=", self.env.company.id),
                ("code", "in", list(EXPECTED_SCENARIO_SEQUENCES)),
            ]
        )
        for scenario in existing:
            scenario.with_context(module=True).write(
                {"sequence": EXPECTED_SCENARIO_SEQUENCES[scenario.code]}
            )

        seed_iso9001_transition_scenarios(self.env)

        self.assertEqual(
            {scenario.code: scenario.sequence for scenario in existing},
            {code: sequence for code, sequence in EXPECTED_SCENARIO_SEQUENCES.items()
             if code != "ISO9001-2026-RECERTIFICATION-SAME-EDITION"},
        )
