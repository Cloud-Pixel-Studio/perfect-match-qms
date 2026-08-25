from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tools.convert import convert_file
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPmQmsActionCenter(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.quality_manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")
        cls.viewer_group = cls.env.ref("pm_qms_core.group_qms_viewer")
        cls.quality_manager = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Action Center Quality Manager",
                "login": "action-center-quality-manager",
                "email": "action-center-quality-manager@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, cls.quality_manager_group.id])],
            }
        )
        cls.viewer = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Action Center Viewer",
                "login": "action-center-viewer",
                "email": "action-center-viewer@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, cls.viewer_group.id])],
            }
        )
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

    def test_menu_matches_viewer_permissions(self):
        action_center = self.env.ref("pm_qms_action_center.menu_pm_qms_action_center")
        action_lines = self.env["pm.qms.action.center.line"]

        manager_menus = self.env["ir.ui.menu"].with_user(self.quality_manager).load_menus(False)
        viewer_menus = self.env["ir.ui.menu"].with_user(self.viewer).load_menus(False)
        self.assertIn(action_center.id, manager_menus)
        self.assertNotIn(action_center.id, viewer_menus)

        manager_action = action_lines.with_user(self.quality_manager).action_open_center()
        self.assertEqual(manager_action["res_model"], "pm.qms.action.center.line")
        with self.assertRaises(AccessError):
            action_lines.with_user(self.viewer).create(
                {
                    "source_key": "pm.qms.nonconformity:1:ncr_closure",
                    "source_model": "pm.qms.nonconformity",
                    "source_id": 1,
                    "action_kind": "ncr_closure",
                    "title": "Viewer must not create action lines",
                }
            )

    def test_menu_upgrade_replaces_residual_viewer_group(self):
        action_center = self.env.ref("pm_qms_action_center.menu_pm_qms_action_center")
        action_center.write(
            {"group_ids": [Command.set([self.qms_user_group.id, self.viewer_group.id])]}
        )

        convert_file(
            self.env,
            "pm_qms_action_center",
            "views/menu_views.xml",
            {},
            mode="update",
            kind="data",
        )
        action_center.invalidate_recordset(["group_ids"])

        self.assertEqual(action_center.group_ids, self.env.ref("pm_qms_core.group_pm_qms_user"))
        self.assertNotIn(self.viewer_group, action_center.group_ids)

    def test_effective_menu_visibility_matches_customer_roles(self):
        action_center = self.env.ref("pm_qms_action_center.menu_pm_qms_action_center")
        manager_menus = self.env["ir.ui.menu"].with_user(self.quality_manager).load_menus(False)
        viewer_menus = self.env["ir.ui.menu"].with_user(self.viewer).load_menus(False)

        self.assertIn(action_center.id, manager_menus)
        self.assertNotIn(action_center.id, viewer_menus)
        self.assertFalse(self.env["pm.qms.action.center.line"].with_user(self.viewer).check_access_rights("create", raise_exception=False))
