from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval


@tagged("-at_install", "post_install")
class TestPmQmsAppShell(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Dashboard Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.qms_admin_group = cls.env.ref("pm_qms_core.group_pm_qms_administrator")
        cls.user = cls._create_user("app_shell_user", cls.qms_user_group, cls.company)
        cls.manager = cls._create_user("app_shell_manager", cls.qms_manager_group, cls.company)
        cls.other_user = cls._create_user("app_shell_other", cls.qms_user_group, cls.other_company)

        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Dashboard Organization", "code": "PM-APP-ORG", "company_id": cls.company.id}
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Dashboard Organization", "code": "PM-APP-ORG2", "company_id": cls.other_company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Dashboard Process",
                "code": "PM-APP-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Dashboard Process",
                "code": "PM-APP-PROC2",
                "organization_id": cls.other_organization.id,
                "company_id": cls.other_company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Dashboard Control",
                "code": "PM-QMS-APP-001",
                "objective": "Provide a proprietary dashboard validation control.",
                "process_id": cls.process.id,
                "category": "process",
            }
        )
        cls.control.action_activate()
        cls.activity = cls.env["pm.qms.activity"].create(
            {
                "control_id": cls.control.id,
                "name": "Complete dashboard validation activity",
                "description": "Validate that QMS activities remain backed by project.task.",
            }
        )
        cls.requirement = cls.env["pm.qms.evidence.requirement"].create(
            {"control_id": cls.control.id, "name": "Dashboard evidence", "evidence_type": "record", "mandatory": True}
        )
        cls.pack = cls.env["pm.qms.framework.pack"].create(
            {
                "name": "Dashboard Pack",
                "code": "PM-APP-PACK",
                "version": "1.0",
                "company_id": cls.company.id,
                "pack_type": "core",
                "description": "Fictional Perfect Match pack for dashboard tests.",
            }
        )
        cls.env["pm.qms.framework.pack.control"].create(
            {"pack_id": cls.pack.id, "control_id": cls.control.id, "sequence": 10, "required": True}
        )
        cls.pack.action_activate()
        cls.project = cls.env["pm.qms.implementation.project"].with_user(cls.manager).generate_from_wizard(
            {
                "name": "Dashboard Implementation",
                "company_id": cls.company.id,
                "organization_id": cls.organization.id,
                "project_manager_id": cls.manager.id,
                "date_start": fields.Date.today(),
                "target_date": fields.Date.today(),
                "implementation_type": "new_implementation",
                "pack_ids": cls.pack.ids,
                "create_odoo_project": True,
            }
        )
        cls.line = cls.project.implementation_control_ids[:1]
        cls.evidence = cls.env["pm.qms.evidence"].create(
            {
                "name": "Accepted dashboard evidence",
                "control_instance_id": cls.line.control_instance_id.id,
                "evidence_requirement_id": cls.requirement.id,
            }
        )
        cls.evidence.with_user(cls.manager).action_submit()
        cls.evidence.with_user(cls.manager).action_review()
        cls.evidence.with_user(cls.manager).action_accept()
        cls.line.control_instance_id.action_mark_implemented()
        cls.project.generated_task_ids.with_user(cls.manager).write({"state": "1_done"})

        cls.env["pm.qms.risk"].create(
            {
                "name": "Other company risk",
                "organization_id": cls.other_organization.id,
                "process_id": cls.other_process.id,
                "description": "Other company record must not appear in dashboard counts.",
                "likelihood": 5,
                "impact": 5,
                "residual_likelihood": 5,
                "residual_impact": 5,
            }
        )

    @classmethod
    def _create_user(cls, login, group, company):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": company.id,
                "company_ids": [Command.set([company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, group.id])],
            }
        )

    def test_product_app_shell_owns_single_root_menu_and_application_tile(self):
        root = self.env.ref("pm_qms_core.menu_pm_qms_root")
        self.assertEqual(root.name, "Perfect Match QMS")
        self.assertEqual(root.action, self.env.ref("pm_qms_app.action_pm_qms_dashboard"))
        self.assertEqual(root.web_icon, "pm_qms_app,static/description/icon.svg")
        roots = self.env["ir.ui.menu"].search([("parent_id", "=", False), ("name", "=", "Perfect Match QMS")])
        self.assertEqual(len(roots), 1)
        self.assertFalse(self.env["ir.module.module"].search([("name", "=", "pm_qms_core")], limit=1).application)
        self.assertTrue(self.env["ir.module.module"].search([("name", "=", "pm_qms_app")], limit=1).application)

    def test_expected_navigation_hierarchy_is_installed(self):
        root = self.env.ref("pm_qms_core.menu_pm_qms_root")
        child_names = set(root.child_id.filtered("active").mapped("name"))
        expected = {
            "Dashboard",
            "Implementations",
            "Documents",
            "Evidence",
            "Risk & Improvement",
            "Audit",
            "Performance",
            "Management Review",
            "Framework",
            "Configuration",
        }
        self.assertTrue(expected.issubset(child_names))
        implementation = self.env.ref("pm_qms_core.menu_pm_qms_implementation")
        self.assertIn("Activities", set(implementation.child_id.filtered("active").mapped("name")))
        self.assertIn("Controls", set(implementation.child_id.filtered("active").mapped("name")))

    def test_menu_permissions_keep_framework_out_of_user_navigation(self):
        framework = self.env.ref("pm_qms_core.menu_pm_qms_framework")
        self.assertIn(self.qms_manager_group, framework.group_ids)
        self.assertNotIn(self.qms_user_group, framework.group_ids)
        visible_menus = self.env["ir.ui.menu"].with_user(self.user).load_menus(False)
        self.assertNotIn(framework.id, visible_menus)

    def test_dashboard_uses_live_readiness_and_security_scoped_counts(self):
        dashboard = self.env["pm.qms.dashboard"].with_user(self.user).create(
            {"organization_id": self.organization.id, "implementation_project_id": self.project.id}
        )
        self.assertEqual(dashboard.total_controls, self.project.total_controls)
        self.assertEqual(dashboard.total_activities, self.project.total_generated_tasks)
        self.assertEqual(dashboard.accepted_evidence, self.project.accepted_evidence)
        self.assertAlmostEqual(dashboard.readiness_percent, self.project.readiness_percent, places=2)
        self.assertEqual(dashboard.open_risks, 0)
        other_dashboard = self.env["pm.qms.dashboard"].with_user(self.other_user).create(
            {"organization_id": self.other_organization.id}
        )
        self.assertEqual(other_dashboard.open_risks, 1)

    def test_implementation_activity_navigation_uses_project_task(self):
        action = self.project.action_view_activities()
        self.assertEqual(action["id"], self.env.ref("pm_qms_implementation.action_pm_qms_implementation_activities").id)
        self.assertEqual(action["res_model"], "project.task")
        self.assertIn("kanban", action["view_mode"])
        self.assertIn("list", action["view_mode"])
        self.assertIn("form", action["view_mode"])
        self.assertIn(("pm_implementation_project_id", "=", self.project.id), action["domain"])
        self.assertIn(("pm_generated", "=", True), action["domain"])
        self.assertEqual(action["context"]["default_pm_implementation_project_id"], self.project.id)
        self.assertEqual(action["context"]["default_project_id"], self.project.odoo_project_id.id)
        self.assertTrue(self.project.generated_task_ids)
        self.assertEqual(self.project.generated_task_ids._name, "project.task")

    def test_qms_activity_action_filters_out_generic_project_tasks(self):
        odoo_project = self.env["project.project"].create(
            {"name": "Generic Non-QMS Project", "company_id": self.company.id}
        )
        generic_task = self.env["project.task"].create(
            {"name": "Generic task outside QMS", "project_id": odoo_project.id}
        )

        action = self.env["ir.actions.actions"]._for_xml_id(
            "pm_qms_implementation.action_pm_qms_implementation_activities"
        )
        domain = safe_eval(action["domain"]) if isinstance(action["domain"], str) else action["domain"]
        activity_ids = self.env["project.task"].search(domain).ids

        self.assertEqual(action["res_model"], "project.task")
        self.assertNotIn(generic_task.id, activity_ids)
        self.assertTrue(set(self.project.generated_task_ids.ids).issubset(set(activity_ids)))
        self.assertFalse(self.env["ir.model"].search([("model", "=", "pm.qms.task")]))
        self.assertEqual(action["search_view_id"][0], self.env.ref("pm_qms_implementation.view_pm_qms_project_task_search").id)
        self.assertEqual([mode for _, mode in action["views"]], ["kanban", "list", "form"])

    def test_historical_readiness_snapshot_remains_immutable(self):
        action = self.project.with_user(self.manager).action_run_readiness_assessment()
        assessment = self.env["pm.qms.readiness.assessment"].browse(action["domain"][0][2])
        self.assertEqual(assessment.state, "completed")
        with self.assertRaises(Exception):
            assessment.with_user(self.manager).write({"notes": "Do not mutate completed snapshots."})
