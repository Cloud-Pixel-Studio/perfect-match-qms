from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPmQmsCostQuality(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.env.user.write({"group_ids": [(4, cls.env.ref("pm_qms_core.group_pm_qms_manager").id)]})
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Cost Quality Org", "code": "PM-CQ-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {"name": "Cost Quality Process", "code": "PM-CQ-PROC", "organization_id": cls.organization.id, "company_id": cls.company.id}
        )
        Type = cls.env["pm.qms.cost.type"]
        cls.prevention = Type.create({"name": "Prevention", "category": "prevention", "company_id": cls.company.id})
        cls.appraisal = Type.create({"name": "Appraisal", "category": "appraisal", "company_id": cls.company.id})
        cls.internal_failure = Type.create({"name": "Internal", "category": "internal_failure", "company_id": cls.company.id})
        cls.external_failure = Type.create({"name": "External", "category": "external_failure", "company_id": cls.company.id})
        cls.ncr = cls.env["pm.qms.nonconformity"].create(
            {
                "name": "Cost source NCR",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "source_type": "internal",
                "severity": "major",
                "description": "Cost source issue.",
                "detected_date": fields.Date.today(),
                "target_date": fields.Date.today(),
            }
        )

    def _event(self):
        return self.env["pm.qms.cost.event"].create(
            {
                "name": "Cost event",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "source_model": "pm.qms.nonconformity",
                "source_id": self.ncr.id,
                "line_ids": [
                    (0, 0, {"cost_type_id": self.prevention.id, "description": "Prevent", "amount": 100.0, "is_estimated": True}),
                    (0, 0, {"cost_type_id": self.appraisal.id, "description": "Check", "amount": 50.0}),
                    (0, 0, {"cost_type_id": self.internal_failure.id, "description": "Rework", "amount": 25.0}),
                    (0, 0, {"cost_type_id": self.external_failure.id, "description": "Customer", "amount": 10.0, "recovery_amount": 3.0}),
                ],
            }
        )

    def test_copq_excludes_prevention_and_appraisal(self):
        event = self._event()
        self.assertEqual(event.quality_cost_total, 185.0)
        self.assertEqual(event.copq_amount, 35.0)
        self.assertEqual(event.net_quality_cost, 182.0)

    def test_confirmed_event_is_immutable_and_corrections_are_draft(self):
        event = self._event()
        event.action_confirm()
        with self.assertRaises(AccessError):
            event.write({"event_date": fields.Date.today()})
        with self.assertRaises(AccessError):
            event.line_ids[0].write({"amount": 1.0})
        action = event.action_create_correction()
        correction = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(correction.state, "draft")
        self.assertFalse(correction.line_ids)


    def test_dashboard_reports_official_quality_costs(self):
        event = self._event()
        event.action_confirm()
        self.assertTrue(event.line_ids.filtered("is_estimated"))
        dashboard = self.env["pm.qms.dashboard"].create({"organization_id": self.organization.id})
        self.assertEqual(dashboard.quality_cost_event_count, 1)
        self.assertEqual(dashboard.dashboard_quality_cost_total, 185.0)
        self.assertEqual(dashboard.dashboard_copq_amount, 35.0)
        action = dashboard.action_view_cost_quality()
        self.assertEqual(action["res_model"], "pm.qms.cost.event")

    def test_source_alignment_is_enforced(self):
        other_company = self.env["res.company"].create({"name": "Other CQ Company"})
        other_org = self.env["pm.qms.organization"].create({"name": "Other CQ Org", "code": "PM-CQ-OTHER", "company_id": other_company.id})
        with self.assertRaises(ValidationError):
            self.env["pm.qms.cost.event"].create(
                {"name": "Bad source", "organization_id": other_org.id, "source_model": "pm.qms.nonconformity", "source_id": self.ncr.id}
            )

    def test_confirm_requires_lines(self):
        event = self.env["pm.qms.cost.event"].create({"name": "Empty", "organization_id": self.organization.id})
        with self.assertRaises(UserError):
            event.action_confirm()

    def test_cost_quality_is_not_exposed_to_qms_viewers(self):
        base_user = self.env.ref("base.group_user")
        quality_manager = self.env.ref("pm_qms_core.group_qms_quality_manager")
        management_user = self.env.ref("pm_qms_core.group_qms_management_user")
        viewer = self.env.ref("pm_qms_core.group_qms_viewer")
        users = {
            "manager": self.env["res.users"].with_context(no_reset_password=True).create(
                {"name": "Cost Quality Manager", "login": "cost-quality-manager", "group_ids": [Command.set([base_user.id, quality_manager.id])]}
            ),
            "management": self.env["res.users"].with_context(no_reset_password=True).create(
                {"name": "Cost Quality Management", "login": "cost-quality-management", "group_ids": [Command.set([base_user.id, management_user.id])]}
            ),
            "viewer": self.env["res.users"].with_context(no_reset_password=True).create(
                {"name": "Cost Quality Viewer", "login": "cost-quality-viewer", "group_ids": [Command.set([base_user.id, viewer.id])]}
            ),
        }
        cost_event = self.env.ref("pm_qms_cost_quality.menu_pm_qms_cost_quality")
        self.assertIn(quality_manager, cost_event.group_ids)
        self.assertIn(management_user, cost_event.group_ids)
        self.assertNotIn(viewer, cost_event.group_ids)
        for user in (users["manager"], users["management"]):
            self.env["pm.qms.cost.event"].with_user(user).check_access_rights("read", raise_exception=True)
        with self.assertRaises(AccessError):
            self.env["pm.qms.cost.event"].with_user(users["viewer"]).check_access_rights("read", raise_exception=True)
