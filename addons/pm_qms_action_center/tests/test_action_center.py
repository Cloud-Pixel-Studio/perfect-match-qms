from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPmQmsActionCenter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Action Center Org", "code": "PM-AC-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Action Center Process",
                "code": "PM-AC-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.ncr = cls.env["pm.qms.nonconformity"].create(
            {
                "name": "Action center NCR",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "source_type": "internal",
                "severity": "major",
                "description": "Open issue for action center testing.",
                "detected_date": fields.Date.today(),
                "owner_id": cls.env.user.id,
                "target_date": fields.Date.today(),
            }
        )

    def test_collects_source_records_without_authoritative_action_model(self):
        model = self.env["pm.qms.action.center.line"]
        values = model._collect_action_values(self.organization)
        keys = {item["source_key"] for item in values}
        self.assertIn(f"pm.qms.nonconformity:{self.ncr.id}:ncr_closure", keys)
        self.assertNotIn("pm.qms.action", self.env)

    def test_refresh_is_idempotent_for_current_user(self):
        model = self.env["pm.qms.action.center.line"]
        first = model._refresh_for_current_user()
        second = model._refresh_for_current_user()
        self.assertEqual(first, second)
        self.assertEqual(
            model.search_count([("source_key", "=", f"pm.qms.nonconformity:{self.ncr.id}:ncr_closure")]),
            1,
        )

    def test_open_source_uses_allowlisted_source_identity(self):
        self.env["pm.qms.action.center.line"]._refresh_for_current_user()
        line = self.env["pm.qms.action.center.line"].search(
            [("source_key", "=", f"pm.qms.nonconformity:{self.ncr.id}:ncr_closure")], limit=1
        )
        action = line.action_open_source()
        self.assertEqual(action["res_model"], "pm.qms.nonconformity")
        self.assertEqual(action["res_id"], self.ncr.id)

    def test_rejects_unregistered_open_request(self):
        line = self.env["pm.qms.action.center.line"].create(
            {
                "source_key": "res.partner:1:any",
                "source_model": "res.partner",
                "source_id": 1,
                "action_kind": "any",
                "title": "Unsafe",
            }
        )
        with self.assertRaises(UserError):
            line.action_open_source()

    def test_dashboard_surfaces_unified_action_counts(self):
        dashboard = self.env["pm.qms.dashboard"].create({"organization_id": self.organization.id})
        self.assertGreaterEqual(dashboard.unified_action_count, 1)
        self.assertGreaterEqual(dashboard.my_action_count, 1)
        action = dashboard.action_view_unified_actions()
        self.assertEqual(action["res_model"], "pm.qms.action.center.line")
