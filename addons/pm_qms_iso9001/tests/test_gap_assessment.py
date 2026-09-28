from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import PROFILE_CODE, post_init_hook
from odoo.addons.pm_qms_iso9001.models.gap_assessment import GAP_FOCUS_DEFINITIONS


@tagged("-at_install", "post_install")
class TestPmQmsIso9001GapAssessment(TransactionCase):
    def setUp(self):
        super().setUp()
        post_init_hook(self.env)
        manager_group = self.env.ref("pm_qms_core.group_pm_qms_manager")
        administrator_group = self.env.ref("pm_qms_core.group_pm_qms_administrator")
        self.manager = self.env["res.users"].create(
            {
                "name": "ISO 9001 Gap Assessment Test Manager",
                "login": "iso.gap.manager@example.invalid",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            manager_group.id,
                            administrator_group.id,
                        ]
                    )
                ],
            }
        )
        self.scenario = self.env["pm.qms.iso9001.transition.scenario"].with_user(self.manager).search(
            [
                ("code", "=", "ISO9001-2026-TRANSITION-2015"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        self.source_profile = self.env["pm.qms.mapping.profile"].with_user(self.manager).search(
            [
                ("code", "=", PROFILE_CODE),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    def _assessment(self):
        return self.env["pm.qms.iso9001.gap.assessment"].with_user(self.manager).create(
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
        self.assertEqual(assessment.completed_by_id, self.manager)
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
                "responsible_id": self.manager.id,
                "target_date": fields.Date.today(),
            }
        )
        assessment.action_complete()

        self.assertEqual(assessment.state, "completed")
        self.assertEqual(assessment.gap_area_count, 1)
        self.assertLess(assessment.readiness_percent, 100.0)

    def test_scenario_action_leaves_assessment_draft_for_project_selection(self):
        organization = self.env["pm.qms.organization"].with_user(self.manager).create(
            {
                "name": "Gap Assessment Project Organization",
                "code": "GAP-PROJECT-ORG",
                "company_id": self.env.company.id,
            }
        )
        project = self.env["pm.qms.implementation.project"].with_user(self.manager).create(
            {
                "name": "Gap Assessment Transition Project",
                "company_id": self.env.company.id,
                "organization_id": organization.id,
                "project_manager_id": self.manager.id,
                "date_start": fields.Date.today(),
                "target_date": fields.Date.today(),
                "implementation_type": "migration",
            }
        )
        before = len(self.scenario.assessment_ids)
        action = self.scenario.action_create_gap_assessment()
        assessment = self.env["pm.qms.iso9001.gap.assessment"].with_user(self.manager).browse(action["res_id"])

        self.assertEqual(len(self.scenario.assessment_ids), before + 1)
        self.assertEqual(assessment.state, "draft")
        self.assertFalse(assessment.line_ids)
        self.assertEqual(assessment.source_profile_id, self.source_profile)
        self.assertEqual(action["res_model"], "pm.qms.iso9001.gap.assessment")

        assessment.write({"implementation_project_id": project.id})
        assessment.action_start()
        self.assertEqual(assessment.state, "in_progress")
        with self.assertRaises(AccessError):
            assessment.write({"implementation_project_id": False})

    def test_cancelled_or_completed_assessments_cannot_be_restarted(self):
        assessment = self._assessment()
        assessment.action_cancel()

        with self.assertRaises(UserError):
            assessment.action_start()

    def test_area_initialization_cannot_be_called_directly(self):
        assessment = self._assessment()
        code, name, purpose = GAP_FOCUS_DEFINITIONS[0]
        with self.assertRaises(AccessError):
            self.env["pm.qms.iso9001.gap.assessment.line"].with_user(self.manager).with_context(
                pm_qms_gap_initialize=True
            ).create(
                {
                    "assessment_id": assessment.id,
                    "focus_code": code,
                    "focus_name_snapshot": name,
                    "purpose_snapshot": purpose,
                }
            )

    def test_assessment_identity_is_locked_after_start(self):
        assessment = self._assessment()
        assessment.action_start()

        with self.assertRaises(AccessError):
            assessment.write({"assessment_date": fields.Date.today()})

    def test_workflow_context_cannot_forge_completion(self):
        assessment = self._assessment()

        with self.assertRaises(AccessError):
            assessment.with_context(pm_qms_gap_workflow=True).write(
                {
                    "state": "completed",
                    "completed_by_id": self.manager.id,
                    "completed_date": fields.Datetime.now(),
                }
            )

        self.assertEqual(assessment.state, "draft")
        self.assertFalse(assessment.completed_by_id)
        self.assertFalse(assessment.completed_date)

    def test_not_applicable_area_requires_rationale(self):
        assessment = self._assessment()
        assessment.action_start()
        assessment.line_ids.write({"status": "conforming"})
        excluded_line = assessment.line_ids[:1]
        excluded_line.write({"status": "not_applicable"})

        with self.assertRaises(UserError):
            assessment.action_complete()

        excluded_line.write(
            {"disposition_rationale": "This area is outside the approved transition scope."}
        )
        assessment.action_complete()

        self.assertEqual(assessment.state, "completed")
        self.assertEqual(assessment.not_applicable_area_count, 1)

    def test_assessment_company_is_server_owned_and_scenario_company_is_frozen(self):
        other_company = self.env["res.company"].create(
            {"name": "Independent ISO Assessment Company"}
        )
        assessment = self.env["pm.qms.iso9001.gap.assessment"].with_user(self.manager).create(
            {
                "name": "Company snapshot assessment",
                "scenario_id": self.scenario.id,
                "source_profile_id": self.source_profile.id,
                "company_id": other_company.id,
            }
        )

        self.assertEqual(assessment.company_id, self.scenario.company_id)
        with self.assertRaises(AccessError):
            self.scenario.write({"company_id": other_company.id})
        self.assertEqual(assessment.company_id, self.env.company)

    def test_retired_or_archived_scenario_cannot_start_assessment(self):
        self.scenario.write({"state": "retired", "active": False})

        with self.assertRaises(ValidationError):
            self.scenario.action_create_gap_assessment()
