from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import PROFILE_CODE, post_init_hook


@tagged("-at_install", "post_install")
class TestPmQmsIso9001TransitionReview(TransactionCase):
    def setUp(self):
        super().setUp()
        post_init_hook(self.env)
        manager_group = self.env.ref("pm_qms_core.group_pm_qms_manager")
        self.manager_group = manager_group
        self.reviewer = self.env["res.users"].create(
            {
                "name": "Independent Transition Reviewer",
                "login": "iso.transition.reviewer@example.invalid",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "groups_id": [Command.set(manager_group.ids)],
            }
        )
        self.organization = self.env["pm.qms.organization"].create(
            {
                "name": "Transition Review Test Organization",
                "code": "TRR-ORG",
                "company_id": self.env.company.id,
            }
        )
        self.project = self.env["pm.qms.implementation.project"].create(
            {
                "name": "ISO 9001 transition test project",
                "company_id": self.env.company.id,
                "organization_id": self.organization.id,
                "project_manager_id": self.env.user.id,
                "date_start": fields.Date.today(),
                "target_date": fields.Date.today() + timedelta(days=90),
                "implementation_type": "migration",
            }
        )
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

    def _assessment_with_actions(self):
        assessment = self.env["pm.qms.iso9001.gap.assessment"].create(
            {
                "name": "Transition review source assessment",
                "scenario_id": self.scenario.id,
                "source_profile_id": self.source_profile.id,
            }
        )
        assessment.action_start()
        assessment.line_ids.write({"status": "conforming"})
        deadline = fields.Date.today() + timedelta(days=30)
        for line, status in zip(assessment.line_ids[:2], ("partial", "gap")):
            line.write(
                {
                    "status": status,
                    "gap_description": f"Controlled {status} source finding.",
                    "action_plan": f"Complete the controlled {status} action.",
                    "responsible_id": self.env.user.id,
                    "target_date": deadline,
                }
            )
        assessment.action_complete()
        assessment.action_generate_transition_plan()
        assessment.transition_action_ids.write(
            {"implementation_project_id": self.project.id}
        )
        return assessment

    def _complete_actions(self, assessment):
        for action in assessment.transition_action_ids:
            if action.state == "draft":
                action.action_start()
            action.write(
                {
                    "completion_summary": "Controlled transition action completed.",
                    "verification_evidence": "Independent evidence reference reviewed.",
                }
            )
            action.action_submit_verification()
            action.with_user(self.reviewer).action_complete()

    def _review_values(self, decision="continue_actions"):
        return {
            "reviewer_id": self.reviewer.id,
            "decision": decision,
            "review_basis": "The controlled gap assessment and transition actions were reviewed.",
            "residual_risk_summary": "Open actions remain controlled under assigned owners.",
            "decision_notes": "Continue controlled execution before internal review.",
        }

    def test_review_preparation_is_controlled_and_idempotent(self):
        assessment = self._assessment_with_actions()

        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            assessment
        )
        same_review = assessment.action_prepare_readiness_review()
        self.assertEqual(same_review["res_id"], review.id)
        self.assertTrue(review.code.startswith("ISO-TRR-"))
        self.assertEqual(review.company_id, assessment.company_id)
        self.assertEqual(review.implementation_project_id, self.project)
        self.assertEqual(review.source_edition_snapshot, "2015")
        self.assertEqual(review.target_edition_snapshot, "2026")

        with self.assertRaises(AccessError):
            self.env["pm.qms.iso9001.transition.review"].create(
                {
                    "name": "Forged review",
                    "code": "FORGED",
                    "assessment_id": assessment.id,
                    "company_id": self.env.company.id,
                    "implementation_project_id": self.project.id,
                    "reviewer_id": self.reviewer.id,
                    "review_basis": "forged",
                    "residual_risk_summary": "forged",
                    "decision_notes": "forged",
                    "source_edition_snapshot": "2015",
                    "target_edition_snapshot": "2026",
                }
            )

    def test_submit_requires_independent_reviewer_and_snapshots_actions(self):
        assessment = self._assessment_with_actions()
        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            assessment
        )
        with self.assertRaises(UserError):
            review.action_submit()

        review.write(self._review_values())
        review.action_submit()

        self.assertEqual(review.state, "submitted")
        self.assertEqual(review.total_action_count_snapshot, 2)
        self.assertEqual(review.completed_action_count_snapshot, 0)
        self.assertEqual(review.open_action_count_snapshot, 2)
        self.assertTrue(review.action_state_snapshot)
        review.with_user(self.reviewer).action_approve()
        self.assertEqual(review.state, "approved")
        self.assertEqual(review.approved_by_id, self.reviewer)
        with self.assertRaises(AccessError):
            review.write({"decision_notes": "Historical rewrite"})

    def test_internal_review_requires_all_actions_completed_and_fresh_snapshot(self):
        assessment = self._assessment_with_actions()
        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            assessment
        )
        values = self._review_values("internal_review")
        values.update(
            {
                "review_basis": "Transition evidence was evaluated.",
                "residual_risk_summary": "No uncontrolled residual risks are accepted.",
                "decision_notes": "Proceed only after every action is independently verified.",
            }
        )
        review.write(values)
        review.action_submit()
        with self.assertRaises(UserError):
            review.with_user(self.reviewer).action_approve()

        review.with_user(self.reviewer).write(
            {"return_reason": "Complete and verify every transition action."}
        )
        review.with_user(self.reviewer).action_return()
        self._complete_actions(assessment)
        review.action_submit()
        self.assertEqual(review.completed_action_count_snapshot, 2)
        self.assertEqual(review.open_action_count_snapshot, 0)
        review.with_user(self.reviewer).action_approve()
        self.assertEqual(review.state, "approved")

    def test_changed_action_state_after_submission_invalidates_snapshot(self):
        assessment = self._assessment_with_actions()
        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            assessment
        )
        review.write(self._review_values())
        review.action_submit()
        assessment.transition_action_ids[:1].action_start()

        with self.assertRaisesRegex(
            UserError, "status or relationships changed after submission"
        ):
            review.with_user(self.reviewer).action_approve()

    def test_reviewer_must_have_access_to_review_company(self):
        assessment = self._assessment_with_actions()
        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            assessment
        )
        foreign_company = self.env["res.company"].create(
            {"name": "Foreign Review Company"}
        )
        foreign_reviewer = self.env["res.users"].create(
            {
                "name": "Foreign Transition Reviewer",
                "login": "iso.foreign.reviewer@example.invalid",
                "company_id": foreign_company.id,
                "company_ids": [Command.set(foreign_company.ids)],
                "groups_id": [Command.set(self.manager_group.ids)],
            }
        )

        with self.assertRaises(ValidationError):
            review.write({"reviewer_id": foreign_reviewer.id})

    def test_action_project_drift_after_submission_invalidates_review(self):
        assessment = self._assessment_with_actions()
        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            assessment
        )
        review.write(self._review_values())
        review.action_submit()
        alternate_project = self.env["pm.qms.implementation.project"].create(
            {
                "name": "Alternate ISO 9001 transition project",
                "company_id": self.env.company.id,
                "organization_id": self.organization.id,
                "project_manager_id": self.env.user.id,
                "date_start": fields.Date.today(),
                "target_date": fields.Date.today() + timedelta(days=120),
                "implementation_type": "migration",
            }
        )
        assessment.transition_action_ids[:1].write(
            {"implementation_project_id": alternate_project.id}
        )

        with self.assertRaisesRegex(
            UserError, "status or relationships changed after submission"
        ):
            review.with_user(self.reviewer).action_approve()
