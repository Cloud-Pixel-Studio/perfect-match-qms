from pathlib import Path

from odoo import Command, fields
from odoo.exceptions import AccessError
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
        cls.quality_manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")
        cls.user = cls._create_user("app_shell_user", cls.qms_user_group, cls.company)
        cls.manager = cls._create_user("app_shell_manager", cls.qms_manager_group, cls.company)
        cls.quality_manager = cls._create_user(
            "app_shell_quality_manager", cls.quality_manager_group, cls.company
        )
        cls.viewer = cls._create_user(
            "app_shell_viewer", cls.env.ref("pm_qms_core.group_qms_viewer"), cls.company
        )
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
            "Implementation",
            "Quality Operations",
            "Assurance",
            "Performance",
            "Configuration",
        }
        self.assertTrue(expected.issubset(child_names))
        for xmlid, name in (
            ("pm_qms_action_center.menu_pm_qms_action_center", "Action Center"),
            ("pm_qms_iso9001.menu_pm_qms_standards", "Standards"),
        ):
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu.active:
                self.assertIn(name, child_names)
        self.assertNotIn("Implementations", child_names)
        self.assertNotIn("Risk & Improvement", child_names)
        self.assertNotIn("People & Competency", child_names)

        implementation = self.env.ref("pm_qms_core.menu_pm_qms_implementation")
        self.assertIn("Activities", set(implementation.child_id.filtered("active").mapped("name")))
        self.assertIn("Controls", set(implementation.child_id.filtered("active").mapped("name")))
        self.assertIn("Readiness", set(implementation.child_id.filtered("active").mapped("name")))
        self.assertIn("Evidence", set(implementation.child_id.filtered("active").mapped("name")))

        quality_operations = self.env.ref("pm_qms_app.menu_pm_qms_quality_operations")
        self.assertEqual(self.env.ref("pm_qms_risk.menu_pm_qms_risk_improvement").parent_id, quality_operations)
        customer_quality = self.env.ref("pm_qms_customer_quality.menu_pm_qms_customer_quality", raise_if_not_found=False)
        if customer_quality:
            self.assertEqual(customer_quality.parent_id, quality_operations)
        self.assertEqual(self.env.ref("pm_qms_calibration.menu_pm_qms_calibration").parent_id, quality_operations)

        assurance = self.env.ref("pm_qms_app.menu_pm_qms_assurance")
        self.assertEqual(self.env.ref("pm_qms_documents.menu_pm_qms_documents").parent_id, assurance)
        self.assertEqual(self.env.ref("pm_qms_audit.menu_pm_qms_audit").parent_id, assurance)
        self.assertEqual(self.env.ref("pm_qms_people.menu_pm_qms_people").parent_id, assurance)

        performance = self.env.ref("pm_qms_kpi.menu_pm_qms_performance")
        self.assertEqual(self.env.ref("pm_qms_management_review.menu_pm_qms_management_review").parent_id, performance)
        cost_quality = self.env.ref("pm_qms_cost_quality.menu_pm_qms_cost_quality", raise_if_not_found=False)
        if cost_quality:
            self.assertEqual(cost_quality.parent_id, performance)

        configuration = self.env.ref("pm_qms_core.menu_pm_qms_configuration")
        self.assertEqual(self.env.ref("pm_qms_core.menu_pm_qms_organizations").parent_id, configuration)
        self.assertEqual(self.env.ref("pm_qms_core.menu_pm_qms_processes").parent_id, configuration)
        self.assertEqual(self.env.ref("pm_qms_license.menu_pm_qms_license").parent_id, configuration)
        self.assertEqual(
            self.env.ref("pm_qms_license.menu_pm_qms_activation_requests").parent_id,
            self.env.ref("pm_qms_license.menu_pm_qms_license"),
        )

    def test_menu_permissions_keep_framework_out_of_user_navigation(self):
        framework = self.env.ref("pm_qms_core.menu_pm_qms_framework")
        administrator_group = self.env.ref("pm_qms_core.group_pm_qms_administrator")
        configuration = self.env.ref("pm_qms_core.menu_pm_qms_configuration")
        self.assertIn(administrator_group, framework.group_ids)
        self.assertNotIn(self.qms_manager_group, framework.group_ids)
        self.assertNotIn(self.qms_user_group, framework.group_ids)
        self.assertEqual(framework.parent_id, configuration)
        visible_menus = self.env["ir.ui.menu"].with_user(self.user).load_menus(False)
        self.assertNotIn(framework.id, visible_menus)

    def test_platform_roots_are_reserved_for_technical_administrators(self):
        technical_group = self.env.ref("base.group_system")
        for xmlid in (
            "base.menu_management",
            "base.menu_apps",
            "base.menu_module_tree",
            "base.menu_tests",
            "project.menu_main_pm",
            "mail.menu_root_discuss",
        ):
            menu = self.env.ref(xmlid)
            self.assertEqual(menu.group_ids, technical_group, xmlid)
            visible_menus = self.env["ir.ui.menu"].with_user(self.manager).load_menus(False)
            self.assertNotIn(menu.id, visible_menus, xmlid)
        apps_action = self.env.ref("base.open_module_tree")
        self.assertEqual(apps_action.group_ids, technical_group)

    def test_customer_roles_cannot_browse_modules_by_direct_route(self):
        modules = self.env["ir.module.module"]
        self.assertEqual(modules.with_user(self.manager).search_count([]), 0)
        self.assertEqual(modules.with_user(self.viewer).search_count([]), 0)
        self.assertGreater(modules.with_user(self.env.user).search_count([]), 0)

    def test_users_access_action_is_restricted_server_side(self):
        action = self.env.ref("pm_qms_app.action_pm_qms_users_access")
        with self.assertRaises(AccessError):
            action.with_user(self.manager).read()
        self.assertTrue(action.with_user(self.quality_manager).read())
        self.assertTrue(action.with_user(self.env.user).read())

    def test_viewer_can_open_read_only_dashboard_transient(self):
        dashboard = self.env["pm.qms.dashboard"].with_user(self.viewer).create(
            {"organization_id": self.organization.id}
        )
        self.assertTrue(dashboard)
        with self.assertRaises(AccessError):
            dashboard.with_user(self.viewer).write({"organization_id": self.organization.id})

    def test_optional_platform_roots_are_restricted_when_installed(self):
        menu = self.env.ref("project_todo.menu_todo_todos", raise_if_not_found=False)
        if not menu:
            self.skipTest("Optional project_todo module is not installed in this bundle")
        technical_group = self.env.ref("base.group_system")
        self.assertEqual(menu.group_ids, technical_group)
        visible_menus = self.env["ir.ui.menu"].with_user(self.manager).load_menus(False)
        self.assertNotIn(menu.id, visible_menus)

    def test_quality_manager_role_is_not_system_administrator(self):
        self.assertTrue(self.quality_manager.has_group("pm_qms_core.group_qms_quality_manager"))
        self.assertFalse(self.quality_manager.has_group("base.group_system"))

    def test_customer_messaging_shell_contract_preserves_qms_mail(self):
        static_root = Path(__file__).parents[1] / "static" / "src"
        helper = (static_root / "js" / "customer_shell.js").read_text(encoding="utf-8")
        messaging = (static_root / "js" / "messaging_shell.js").read_text(encoding="utf-8")
        template = (static_root / "xml" / "messaging_shell.xml").read_text(encoding="utf-8")

        for group in (
            "pm_qms_core.group_pm_qms_user",
            "pm_qms_core.group_qms_viewer",
            "base.group_system",
        ):
            self.assertIn(group, helper)
        self.assertIn('new Set(["chat", "channel"])', messaging)
        self.assertIn('"notification"', messaging)
        self.assertIn("onWillStart", messaging)
        self.assertIn("await resolveQmsCustomerShell()", messaging)
        self.assertIn("mail.MessagingMenu.content", template)
        self.assertIn("!isQmsCustomerShell", template)
        self.assertIn("mail.DiscussSearch", template)
        self.assertIn("mail.DiscussSearch.newMeeting", template)
        self.assertIn("onClickNewMessage", template)
        self.assertIn("Promise.all", helper)
        self.assertIn("async function isQmsCustomerShell", helper)

        user_menu = (static_root / "js" / "user_menu.js").read_text(encoding="utf-8")
        self.assertIn("@web/webclient/user_menu/user_menu", user_menu)
        self.assertIn("ImStatusDropdown", user_menu)
        self.assertIn("onWillStart", user_menu)
        self.assertIn("element.id !== \"account\"", user_menu)

        self.assertTrue(self.quality_manager.has_group("pm_qms_core.group_pm_qms_user"))
        self.assertTrue(self.viewer.has_group("pm_qms_core.group_qms_viewer"))
        for customer in (self.quality_manager, self.manager, self.viewer):
            self.assertFalse(customer.has_group("base.group_system"))
            self.assertTrue(customer.with_user(customer).has_group("base.group_user"))
        self.assertTrue(self.env.user.has_group("base.group_system"))

        activity = self.control.activity_schedule(
            "mail.mail_activity_data_todo",
            summary="Customer shell mail activity regression",
        )
        self.assertTrue(activity)
        self.assertEqual(activity.res_model, self.control._name)
        self.control.message_subscribe(partner_ids=[self.manager.partner_id.id])
        self.assertTrue(self.control.with_user(self.manager).message_follower_ids)
        activity.action_done()
        self.assertFalse(activity.active)
        self.assertTrue(activity.date_done)

    def test_product_identity_templates_are_loaded(self):
        layout = self.env.ref("pm_qms_app.pm_qms_web_layout_branding")
        login = self.env.ref("pm_qms_app.pm_qms_login_branding")
        self.assertIn("Perfect Match QMS", layout.arch)
        self.assertIn("Perfect Match QMS", login.arch)
        self.assertNotIn("pm_qms_login_logo", login.arch)
        self.assertNotIn("Your logo", login.arch)

    def test_product_shell_asset_bundles_compile_without_css_fallback(self):
        for bundle_name in ("web.assets_frontend", "web.assets_backend"):
            with self.subTest(bundle=bundle_name):
                bundle = self.env["ir.qweb"]._get_asset_bundle(
                    bundle_name,
                    css=True,
                    js=False,
                )
                attachment = bundle.css()
                self.assertFalse(
                    bundle.css_errors,
                    f"{bundle_name} reported CSS errors: {bundle.css_errors}",
                )
                self.assertTrue(attachment.raw)
                self.assertNotIn(
                    b"A css error occured, using an old style to render this page",
                    attachment.raw,
                )

    def test_customer_shell_groups_are_visible_without_changing_authority(self):
        manager_menus = self.env["ir.ui.menu"].with_user(self.manager).load_menus(False)
        viewer_menus = self.env["ir.ui.menu"].with_user(self.viewer).load_menus(False)
        for xmlid in (
            "pm_qms_app.menu_pm_qms_quality_operations",
            "pm_qms_app.menu_pm_qms_assurance",
        ):
            menu = self.env.ref(xmlid)
            self.assertIn(menu.id, manager_menus)
            self.assertIn(menu.id, viewer_menus)

        framework = self.env.ref("pm_qms_core.menu_pm_qms_framework")
        self.assertNotIn(framework.id, manager_menus)
        self.assertNotIn(framework.id, viewer_menus)

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

    def test_mission13_major_product_actions_are_reachable(self):
        expected_actions = {
            "pm_qms_app.action_pm_qms_dashboard": "pm.qms.dashboard",
            "pm_qms_implementation.action_pm_qms_implementation_project": "pm.qms.implementation.project",
            "pm_qms_implementation.action_pm_qms_implementation_control": "pm.qms.implementation.control",
            "pm_qms_implementation.action_pm_qms_implementation_activities": "project.task",
            "pm_qms_evidence.action_pm_qms_evidence": "pm.qms.evidence",
            "pm_qms_implementation.action_pm_qms_readiness_assessment": "pm.qms.readiness.assessment",
            "pm_qms_documents.action_pm_qms_document": "pm.qms.document",
            "pm_qms_documents.action_pm_qms_document_revision": "pm.qms.document.revision",
            "pm_qms_risk.action_pm_qms_risk": "pm.qms.risk",
            "pm_qms_ncr.action_pm_qms_nonconformity": "pm.qms.nonconformity",
            "pm_qms_capa.action_pm_qms_capa": "pm.qms.capa",
            "pm_qms_audit.action_pm_qms_audit": "pm.qms.audit",
            "pm_qms_audit.action_pm_qms_audit_finding": "pm.qms.audit.finding",
            "pm_qms_kpi.action_pm_qms_objective": "pm.qms.objective",
            "pm_qms_kpi.action_pm_qms_kpi": "pm.qms.kpi",
            "pm_qms_kpi.action_pm_qms_customer_performance": "pm.qms.customer.performance",
            "pm_qms_kpi.action_pm_qms_supplier_performance": "pm.qms.supplier.performance",
            "pm_qms_management_review.action_pm_qms_management_review": "pm.qms.management.review",
            "pm_qms_core.action_pm_qms_organization": "pm.qms.organization",
            "pm_qms_core.action_pm_qms_process": "pm.qms.process",
            "pm_qms_core.action_pm_qms_control": "pm.qms.control",
            "pm_qms_core.action_pm_qms_evidence_requirement": "pm.qms.evidence.requirement",
            "pm_qms_implementation.action_pm_qms_framework_pack": "pm.qms.framework.pack",
            "pm_qms_pack_quality.action_pm_qms_external_mapping_quality": "pm.qms.external.mapping",
        }
        for xmlid, model_name in expected_actions.items():
            action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
            self.assertEqual(action["res_model"], model_name, xmlid)
            self.assertTrue(action.get("view_mode"), xmlid)

    def test_mission13_dashboard_navigation_reaches_operational_surface(self):
        dashboard = self.env["pm.qms.dashboard"].with_user(self.user).create(
            {"organization_id": self.organization.id, "implementation_project_id": self.project.id}
        )
        self.assertTrue(dashboard.next_action_1_name or dashboard.total_controls)
        operational_actions = {
            dashboard.action_view_risks: "pm.qms.risk",
            dashboard.action_view_nonconformities: "pm.qms.nonconformity",
            dashboard.action_view_capa: "pm.qms.capa",
            dashboard.action_view_audit_findings: "pm.qms.audit.finding",
            dashboard.action_view_objectives: "pm.qms.objective",
            dashboard.action_view_kpis: "pm.qms.kpi",
            dashboard.action_view_management_reviews: "pm.qms.management.review",
        }
        for method, model_name in operational_actions.items():
            action = method()
            self.assertEqual(action["res_model"], model_name)
            self.assertIn(("organization_id", "=", self.organization.id), action.get("domain", []))

    def test_mission13_implementation_control_visual_actions(self):
        gap_action = self.project.action_view_gaps()
        self.assertEqual(gap_action["res_model"], "pm.qms.implementation.control")
        self.assertIn(("implementation_project_id", "=", self.project.id), gap_action["domain"])
        self.assertIn(("readiness_state", "in", ("gap", "partial")), gap_action["domain"])

        evidence_action = self.line.action_open_evidence()
        self.assertEqual(evidence_action["res_model"], "pm.qms.evidence")
        self.assertIn(("control_instance_id", "=", self.line.control_instance_id.id), evidence_action["domain"])
