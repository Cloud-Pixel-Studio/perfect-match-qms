from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import PROFILE_CODE, post_init_hook


@tagged("-at_install", "post_install")
class TestPmQmsIso9001TransitionAction(TransactionCase):
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
        manager_group = self.env.ref("pm_qms_core.group_pm_qms_manager")
        self.verifier = self.env["res.users"].create(
            {
                "name": "Independent Action Verifier",
                "login": "iso.action.verifier@example.invalid",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "groups_id": [Command.set(manager_group.ids)],
            }
        )

    def _completed_assessment(self):
        assessment = self.env["pm.qms.iso9001.gap.assessment"].create(
            {
                "name": "Actionable 2015 to 2026 assessment",
                "scenario_id": self.scenario.id,
                "source_profile_id": self.source_profile.id,
            }
        )
        assessment.action_start()
        assessment.line_ids.write({"status": "conforming"})
        deadline = fields.Date.today() + timedelta(days=30)
        partial_line = assessment.line_ids[0]
        gap_line = assessment.line_ids[1]
        partial_line.write(
            {
                "status": "partial",
                "gap_description": "Evidence exists but is not consistently controlled.",
                "action_plan": "Standardize the evidence review and approval workflow.",
                "responsible_id": self.env.user.id,
                "target_date": deadline,
            }
        )
        gap_line.write(
            {
                "status": "gap",
                "gap_description": "No controlled transition governance review exists.",
                "action_plan": "Approve and execute a transition governance review.",
                "responsible_id": self.env.user.id,
                "target_date": deadline,
            }
        )
        assessment.action_complete()
        return assessment, partial_line, gap_line

    def test_completed_assessment_generates_idempotent_transition_plan(self):
        assessment, partial_line, gap_line = self._completed_assessment()

        assessment.action_generate_transition_plan()
        assessment.action_generate_transition_plan()

        actions = assessment.transition_action_ids
        self.assertEqual(len(actions), 2)
        self.assertEqual(
            set(actions.mapped("assessment_line_id").ids),
            {partial_line.id, gap_line.id},
        )
        self.assertEqual(
            actions.filtered(lambda action: action.assessment_line_id == partial_line).priority,
            "1",
        )
        self.assertEqual(
            actions.filtered(lambda action: action.assessment_line_id == gap_line).priority,
            "2",
        )
        self.assertTrue(all(action.code.startswith("ISO-ACT-") for action in actions))
        self.assertEqual(set(actions.mapped("company_id").ids), {self.env.company.id})

    def test_transition_action_snapshots_are_preserved(self):
        assessment, _partial_line, gap_line = self._completed_assessment()
        assessment.action_generate_transition_plan()
        action = assessment.transition_action_ids.filtered(
            lambda item: item.assessment_line_id == gap_line
        )

        self.assertEqual(action.focus_code_snapshot, gap_line.focus_code)
        self.assertEqual(action.gap_description_snapshot, gap_line.gap_description)
        self.assertEqual(action.action_plan_snapshot, gap_line.action_plan)
        self.assertEqual(action.source_status_snapshot, "gap")

        with self.assertRaises(AccessError):
            action.write({"gap_description_snapshot": "Caller-controlled rewrite"})

    def test_direct_creation_and_forged_workflow_write_are_rejected(self):
        assessment, _partial_line, gap_line = self._completed_assessment()
        Action = self.env["pm.qms.iso9001.transition.action"]

        with self.assertRaises(AccessError):
            Action.create(
                {
                    "name": "Uncontrolled transition action",
                    "code": "FORGED",
                    "assessment_id": assessment.id,
                    "assessment_line_id": gap_line.id,
                    "company_id": self.env.company.id,
                    "focus_code_snapshot": gap_line.focus_code,
                    "focus_name_snapshot": gap_line.focus_name_snapshot,
                    "gap_description_snapshot": gap_line.gap_description,
                    "action_plan_snapshot": gap_line.action_plan,
                    "source_status_snapshot": "gap",
                    "owner_id": self.env.user.id,
                    "target_date": fields.Date.today(),
                }
            )

        assessment.action_generate_transition_plan()
        action = assessment.transition_action_ids[:1]
        with self.assertRaises(AccessError):
            action.with_context(pm_qms_transition_workflow=True).write(
                {"state": "completed", "verified_by_id": self.env.user.id}
            )
        self.assertEqual(action.state, "draft")

    def test_verification_requires_completion_evidence_and_completion_is_immutable(self):
        assessment, _partial_line, _gap_line = self._completed_assessment()
        assessment.action_generate_transition_plan()
        action = assessment.transition_action_ids[:1]

        action.action_start()
        with self.assertRaises(UserError):
            action.action_submit_verification()

        action.write(
            {
                "completion_summary": "The approved transition control was implemented.",
                "verification_evidence": "Reviewed approval record and effectiveness check.",
            }
        )
        action.action_submit_verification()
        self.assertEqual(action.state, "verification")
        self.assertEqual(action.submitted_by_id, self.env.user)

        with self.assertRaises(AccessError):
            action.action_complete()
        action.with_user(self.verifier).action_complete()
        self.assertEqual(action.state, "completed")
        self.assertEqual(action.verified_by_id, self.verifier)
        self.assertNotEqual(action.submitted_by_id, action.verified_by_id)
        with self.assertRaises(AccessError):
            action.write({"progress_notes": "Historical rewrite"})

    def test_plan_generation_requires_completed_assessment_and_actionable_lines(self):
        assessment = self.env["pm.qms.iso9001.gap.assessment"].create(
            {
                "name": "Conforming assessment",
                "scenario_id": self.scenario.id,
                "source_profile_id": self.source_profile.id,
            }
        )
        with self.assertRaises(UserError):
            assessment.action_generate_transition_plan()

        assessment.action_start()
        assessment.line_ids.write({"status": "conforming"})
        assessment.action_complete()
        with self.assertRaises(UserError):
            assessment.action_generate_transition_plan()
