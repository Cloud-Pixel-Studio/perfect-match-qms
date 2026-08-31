import base64

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestM27Security(TransactionCase):
    """Runtime authorization evidence for the M27 security boundary."""

    OPERATIONS = ("read", "create", "write", "unlink")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "M27 Fictional Company B"})
        cls.organization_a = cls.env["pm.qms.organization"].sudo().create(
            {"name": "M27 Fictional Organization A", "code": "M27-A", "company_id": cls.company_a.id}
        )
        cls.organization_b = cls.env["pm.qms.organization"].sudo().create(
            {"name": "M27 Fictional Organization B", "code": "M27-B", "company_id": cls.company_b.id}
        )
        cls.site_a1 = cls.env["pm.qms.site"].sudo().create(
            {"name": "M27 Fictional Site A1", "code": "M27-SA1", "organization_id": cls.organization_a.id, "site_type": "manufacturing"}
        )
        cls.site_a2 = cls.env["pm.qms.site"].sudo().create(
            {"name": "M27 Fictional Site A2", "code": "M27-SA2", "organization_id": cls.organization_a.id, "site_type": "office"}
        )
        cls.site_b1 = cls.env["pm.qms.site"].sudo().create(
            {"name": "M27 Fictional Site B1", "code": "M27-SB1", "organization_id": cls.organization_b.id, "site_type": "warehouse"}
        )
        cls.process_a = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M27 Fictional Process A",
                "code": "M27-PA",
                "company_id": cls.company_a.id,
                "organization_id": cls.organization_a.id,
                "site_ids": [Command.set([cls.site_a1.id, cls.site_a2.id])],
            }
        )
        cls.process_b = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M27 Fictional Process B",
                "code": "M27-PB",
                "company_id": cls.company_b.id,
                "organization_id": cls.organization_b.id,
                "site_ids": [Command.set([cls.site_b1.id])],
            }
        )
        cls.risk_a = cls.env["pm.qms.risk"].sudo().create(
            {
                "name": "M27 Fictional Risk A",
                "code": "M27-RA",
                "description": "M27 fictional risk fixture A",
                "company_id": cls.company_a.id,
                "organization_id": cls.organization_a.id,
                "process_id": cls.process_a.id,
            }
        )
        cls.risk_b = cls.env["pm.qms.risk"].sudo().create(
            {
                "name": "M27 Fictional Risk B",
                "code": "M27-RB",
                "description": "M27 fictional risk fixture B",
                "company_id": cls.company_b.id,
                "organization_id": cls.organization_b.id,
                "process_id": cls.process_b.id,
            }
        )
        cls.control_a = cls.env["pm.qms.control"].sudo().create(
            {
                "name": "M27 Fictional Control A",
                "objective": "Maintain a fictional controlled QMS record.",
                "process_id": cls.process_a.id,
                "state": "active",
            }
        )
        cls.requirement_a = cls.env["pm.qms.evidence.requirement"].sudo().create(
            {"name": "M27 Fictional Evidence Requirement", "control_id": cls.control_a.id, "evidence_type": "record", "mandatory": True}
        )
        cls.instance_a = cls.env["pm.qms.control.instance"].sudo().create(
            {
                "name": "M27 Fictional Control Instance",
                "control_id": cls.control_a.id,
                "organization_id": cls.organization_a.id,
                "process_id": cls.process_a.id,
            }
        )
        cls.document_a = cls.env["pm.qms.document"].sudo().create(
            {
                "name": "M27 Fictional Controlled Document",
                "code": "M27-DOC-A",
                "organization_id": cls.organization_a.id,
                "process_id": cls.process_a.id,
                "related_control_ids": [Command.set([cls.control_a.id])],
                "related_control_instance_ids": [Command.set([cls.instance_a.id])],
            }
        )
        cls.evidence_a = cls.env["pm.qms.evidence"].sudo().create(
            {
                "name": "M27 Fictional Evidence",
                "control_instance_id": cls.instance_a.id,
                "evidence_requirement_id": cls.requirement_a.id,
                "document_ids": [Command.set([cls.document_a.id])],
            }
        )
        cls.attachment_a = cls.env["ir.attachment"].sudo().create(
            {
                "name": "m27-fictional-evidence.txt",
                "type": "binary",
                "datas": base64.b64encode(b"M27 fictional evidence").decode(),
                "res_model": "pm.qms.risk",
                "res_id": cls.risk_a.id,
                "mimetype": "text/plain",
            }
        )
        cls.risk_a.sudo().message_post(body="M27 fictional scope message.", subtype_xmlid="mail.mt_note")
        cls.risk_a.sudo().activity_schedule(
            "mail.mail_activity_data_todo",
            summary="M27 fictional activity",
            date_deadline=fields.Date.today(),
            user_id=cls.env.user.id,
        )

        cls.base_user = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.viewer_group = cls.env.ref("pm_qms_core.group_qms_viewer")
        cls.quality_manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")
        cls.quality_supervisor_group = cls.env.ref("pm_qms_core.group_qms_quality_supervisor")
        cls.qms_admin_group = cls.env.ref("pm_qms_core.group_pm_qms_administrator")
        cls.licensing_admin_group = cls.env.ref("pm_qms_license.group_pm_qms_license_admin")
        cls.technical_group = cls.env.ref("base.group_system")
        cls.portal_group = cls.env.ref("base.group_portal", raise_if_not_found=False)

        def user(login, company, groups, organization=None, *, portal=False):
            group_ids = [*(group.id for group in groups)]
            if portal and cls.portal_group:
                group_ids.append(cls.portal_group.id)
            else:
                group_ids.insert(0, cls.base_user.id)
            return cls.env["res.users"].sudo().with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([company.id])],
                    "group_ids": [Command.set(sorted(set(group_ids)))],
                    "qms_organization_ids": [Command.set([organization.id])] if organization else [Command.clear()],
                    "qms_all_processes": bool(organization),
                    "qms_scope_configured": bool(organization),
                }
            )

        cls.viewer_a = user("m27.viewer.a", cls.company_a, [cls.viewer_group], cls.organization_a)
        cls.viewer_b = user("m27.viewer.b", cls.company_b, [cls.viewer_group], cls.organization_b)
        cls.qms_user_a = user("m27.qms.user", cls.company_a, [cls.qms_user_group], cls.organization_a)
        cls.manager_a = user("m27.manager.a", cls.company_a, [cls.quality_manager_group], cls.organization_a)
        cls.supervisor_a = user("m27.supervisor.a", cls.company_a, [cls.quality_supervisor_group], cls.organization_a)
        cls.qms_admin_a = user("m27.qms.admin", cls.company_a, [cls.qms_admin_group], cls.organization_a)
        cls.licensing_admin = user("m27.licensing.admin", cls.company_a, [cls.licensing_admin_group], cls.organization_a)
        cls.technical_admin = user("m27.technical.admin", cls.company_a, [cls.technical_group], cls.organization_a)
        cls.portal_user = user("m27.portal", cls.company_a, [], None, portal=True) if cls.portal_group else None
        cls.public_user = cls.env.ref("base.public_user")

    def test_customer_roles_do_not_inherit_system_administration(self):
        for user in (self.qms_user_a, self.viewer_a, self.manager_a, self.supervisor_a, self.licensing_admin):
            with self.subTest(user=user.login):
                self.assertFalse(user.has_group("base.group_system"))
        self.assertFalse(self.licensing_admin.has_group("pm_qms_core.group_pm_qms_administrator"))

    def test_qms_business_records_are_isolated_by_company_and_organization(self):
        risks = self.env["pm.qms.risk"].with_user(self.manager_a).search([])
        self.assertEqual(risks, self.risk_a)
        with self.assertRaises(AccessError):
            self.risk_b.with_user(self.manager_a).read(["name"])

    def test_viewer_cannot_mutate_business_records_or_cross_scope_records(self):
        risk = self.env["pm.qms.risk"].with_user(self.viewer_a)
        self.assertEqual(risk.search([]), self.risk_a)
        self.assertFalse(risk.check_access_rights("create", raise_exception=False))
        self.assertFalse(risk.check_access_rights("write", raise_exception=False))
        self.assertFalse(risk.check_access_rights("unlink", raise_exception=False))
        with self.assertRaises(AccessError):
            self.risk_a.with_user(self.viewer_a).write({"name": "M27 unauthorized mutation"})
        with self.assertRaises(AccessError):
            self.risk_b.with_user(self.viewer_a).read(["name"])

    def test_viewer_dashboard_access_is_transient_and_non_mutating(self):
        dashboard = self.env["pm.qms.dashboard"].with_user(self.viewer_a).create(
            {"organization_id": self.organization_a.id}
        )
        self.assertTrue(dashboard)
        self.assertTrue(self.env["pm.qms.dashboard"]._transient)
        with self.assertRaises(AccessError):
            dashboard.with_user(self.viewer_a).write({"organization_id": self.organization_a.id})

    def test_viewer_dashboard_is_owner_and_scope_isolated(self):
        dashboard_a = self.env["pm.qms.dashboard"].with_user(self.viewer_a).create(
            {"organization_id": self.organization_a.id}
        )
        dashboard_b = self.env["pm.qms.dashboard"].with_user(self.viewer_b).create(
            {"organization_id": self.organization_b.id}
        )
        self.assertFalse(self.env["pm.qms.dashboard"].with_user(self.viewer_b).search([("id", "=", dashboard_a.id)]))
        with self.assertRaises(AccessError):
            dashboard_a.with_user(self.viewer_b).write({"organization_id": self.organization_b.id})
        with self.assertRaises(AccessError):
            dashboard_a.with_user(self.viewer_b).unlink()
        with self.assertRaises((AccessError, ValidationError)):
            self.env["pm.qms.dashboard"].with_user(self.viewer_a).create({"organization_id": self.organization_b.id})
        self.assertTrue(dashboard_b)
        self.assertEqual(self.env["pm.qms.risk"].sudo().search_count([]), 2)

    def test_public_and_portal_have_no_qms_model_or_side_channel_access(self):
        users = [("public", self.public_user)]
        if self.portal_user:
            users.append(("portal", self.portal_user))
        model_names = sorted(
            name
            for name, model in self.env.registry.models.items()
            if name.startswith("pm.qms.") and not model._abstract
        )
        self.assertGreaterEqual(len(model_names), 80)
        for label, user in users:
            for model_name in model_names:
                model = self.env[model_name].with_user(user)
                with self.subTest(user=label, model=model_name):
                    for operation in self.OPERATIONS:
                        self.assertFalse(model.check_access_rights(operation, raise_exception=False))
            self.assertFalse(self.env["pm.qms.risk"].with_user(user).search([("id", "=", self.risk_a.id)]))
            self.assertFalse(self.env["pm.qms.risk"].with_user(user).name_search("M27 Fictional"))
            self.assertEqual(self.env["pm.qms.risk"].with_user(user).read_group([], ["id"], []), [])
            with self.assertRaises(AccessError):
                self.attachment_a.with_user(user).read(["name", "datas"])
            with self.assertRaises(AccessError):
                self.risk_a.with_user(user).message_post(body="M27 unauthorized message")

    def test_native_actions_and_customer_admin_surfaces_are_restricted(self):
        dashboard_action = self.env.ref("pm_qms_app.action_pm_qms_dashboard")
        framework_action = self.env.ref("pm_qms_implementation.action_pm_qms_framework_pack")
        apps_action = self.env.ref("base.open_module_tree")
        for user in (self.qms_user_a, self.viewer_a, self.manager_a, self.supervisor_a):
            with self.subTest(user=user.login):
                with self.assertRaises(AccessError):
                    apps_action.with_user(user).read()
        with self.assertRaises(AccessError):
            framework_action.with_user(self.licensing_admin).read()
        self.assertTrue(dashboard_action.with_user(self.viewer_a).read())
        self.assertTrue(framework_action.with_user(self.qms_admin_a).read())

    def test_scoped_documents_evidence_mail_activity_and_attachment_surface(self):
        self.assertEqual(self.risk_a.with_user(self.viewer_a).search([("id", "=", self.risk_a.id)]), self.risk_a)
        self.assertFalse(self.risk_b.with_user(self.viewer_a).exists())
        with self.assertRaises(AccessError):
            self.attachment_a.with_user(self.viewer_b).read(["name", "datas"])
        with self.assertRaises(AccessError):
            self.risk_a.with_user(self.viewer_a).message_post(body="M27 viewer mutation")
        activities = self.env["mail.activity"].with_user(self.viewer_a).search(
            [("res_model", "=", "pm.qms.risk"), ("res_id", "=", self.risk_a.id)]
        )
        self.assertEqual(len(activities), 1)
        self.assertTrue(self.document_a.with_user(self.viewer_a).read(["name"]))
        self.assertTrue(self.evidence_a.with_user(self.viewer_a).read(["name"]))

    def test_licensing_admin_keeps_only_license_workflow_access(self):
        license_model = self.env["pm.qms.license"].with_user(self.licensing_admin)
        activation_model = self.env["pm.qms.activation.request"].with_user(self.licensing_admin)
        framework_model = self.env["pm.qms.framework.pack"].with_user(self.licensing_admin)
        self.assertTrue(license_model.check_access_rights("read", raise_exception=False))
        self.assertTrue(activation_model.check_access_rights("create", raise_exception=False))
        self.assertFalse(framework_model.check_access_rights("write", raise_exception=False))
        self.assertFalse(self.env["res.users"].with_user(self.licensing_admin).check_access_rights("write", raise_exception=False))
        self.assertFalse(self.env["pm.qms.risk"].with_user(self.licensing_admin).check_access_rights("read", raise_exception=False))
        self.assertFalse(self.env["pm.qms.framework.pack"].with_user(self.licensing_admin).search([]))
        self.assertFalse(self.env["pm.qms.risk"].with_user(self.licensing_admin).search([("id", "=", self.risk_a.id)]))

    def test_approved_persona_fixture_and_cross_scope_identity(self):
        self.assertTrue(self.qms_user_a.has_group("pm_qms_core.group_pm_qms_user"))
        self.assertTrue(self.qms_admin_a.has_group("pm_qms_core.group_pm_qms_administrator"))
        self.assertTrue(self.technical_admin.has_group("base.group_system"))
        self.assertEqual(self.viewer_b.qms_organization_ids, self.organization_b)
        self.assertNotEqual(self.viewer_a.company_id, self.viewer_b.company_id)
