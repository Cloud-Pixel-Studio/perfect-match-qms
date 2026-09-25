from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import PROFILE_CODE, post_init_hook
from odoo.addons.pm_qms_iso9001.models.gap_assessment import GAP_FOCUS_DEFINITIONS


@tagged("-at_install", "post_install")
class TestPmQmsIso9001GapAssessment(TransactionCase):
    def setUp(self):
        super().setUp()
        post_init_hook(self.env)
        self.scenario = self.env["pm.qms.iso9001.transition.scenario"].search(
            [
                ("code", "=", "ISO9001-2026-TRANSITION-2015"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        self.source_profile = self.env["pm.qms.mapping.profile"].search(
            [
                ("code", "=", PROFILE_CODE),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    def _assessment(self):
        return self.env["pm.qms.iso9001.gap.assessment"].create(
            {
                "name": "Controlled 2015 to 2026 assessment",
                "scenario_id": self.scenario.id,
                "source_profile_id": self.source_profile.id,
            }
        )

    def test_assessment_initializes_controlled_authored_focus_areas(self):
        assessment = self._assessment()
        assessment.action_start()

        self.assertEqual(assessment.state, "in_progress")
        self.assertEqual(len(assessment.line_ids), len(GAP_FOCUS_DEFINITIONS))
        self.assertEqual(
            set(assessment.line_ids.mapped("focus_code")),
            {definition[0] for definition in GAP_FOCUS_DEFINITIONS},
        )
        self.assertEqual(assessment.source_edition_snapshot, "2015")
        self.assertEqual(assessment.target_edition_snapshot, "2026")
        self.assertEqual(assessment.readiness_percent, 0.0)

    def test_completion_requires_every_area_disposition(self):
        assessment = self._assessment()
        assessment.action_start()

        with self.assertRaises(UserError):
            assessment.action_complete()

        assessment.line_ids.write({"status": "conforming"})
        assessment.action_complete()

        self.assertEqual(assessment.state, "completed")
        self.assertEqual(assessment.readiness_percent, 100.0)
        self.assertEqual(assessment.completed_by_id, self.env.user)
        with self.assertRaises(AccessError):
            assessment.write({"conclusion": "Historical content must remain immutable."})

    def test_partial_or_gap_area_requires_action_owner_and_date(self):
        assessment = self._assessment()
        assessment.action_start()
        assessment.line_ids.write({"status": "conforming"})
        gap_line = assessment.line_ids[:1]
        gap_line.write({"status": "gap", "gap_description": "A controlled product-authored gap."})

        with self.assertRaises(UserError):
            assessment.action_complete()

        gap_line.write(
            {
                "action_plan": "Approve and implement a controlled remediation plan.",
                "responsible_id": self.env.user.id,
                "target_date": fields.Date.today(),
            }
        )
        assessment.action_complete()

        self.assertEqual(assessment.state, "completed")
        self.assertEqual(assessment.gap_area_count, 1)
        self.assertLess(assessment.readiness_percent, 100.0)

    def test_scenario_action_creates_and_starts_assessment(self):
        before = len(self.scenario.assessment_ids)
        action = self.scenario.action_create_gap_assessment()
        assessment = self.env["pm.qms.iso9001.gap.assessment"].browse(action["res_id"])

        self.assertEqual(len(self.scenario.assessment_ids), before + 1)
        self.assertEqual(assessment.state, "in_progress")
        self.assertEqual(assessment.source_profile_id, self.source_profile)
        self.assertEqual(action["res_model"], "pm.qms.iso9001.gap.assessment")

    def test_cancelled_or_completed_assessments_cannot_be_restarted(self):
        assessment = self._assessment()
        assessment.action_cancel()

        with self.assertRaises(UserError):
            assessment.action_start()
