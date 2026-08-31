from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestM27Security(TransactionCase):
    """Focused DEV authorization checks for the M27 security boundary."""

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
        cls.process_a = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M27 Fictional Process A",
                "code": "M27-PA",
                "company_id": cls.company_a.id,
                "organization_id": cls.organization_a.id,
            }
        )
        cls.process_b = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M27 Fictional Process B",
                "code": "M27-PB",
                "company_id": cls.company_b.id,
                "organization_id": cls.organization_b.id,
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
        cls.base_user = cls.env.ref("base.group_user")
        cls.viewer_group = cls.env.ref("pm_qms_core.group_qms_viewer")
        cls.quality_manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")
        cls.quality_supervisor_group = cls.env.ref("pm_qms_core.group_qms_quality_supervisor")
        cls.qms_admin_group = cls.env.ref("pm_qms_core.group_pm_qms_administrator")
        cls.licensing_admin_group = cls.env.ref("pm_qms_license.group_pm_qms_license_admin")

        def user(login, company, groups, organization):
            return cls.env["res.users"].sudo().with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([company.id])],
                    "group_ids": [Command.set([cls.base_user.id, *(group.id for group in groups)])],
                    "qms_organization_ids": [Command.set([organization.id])],
                    "qms_scope_configured": True,
                }
            )

        cls.viewer_a = user("m27.viewer.a", cls.company_a, [cls.viewer_group], cls.organization_a)
        cls.viewer_b = user("m27.viewer.b", cls.company_b, [cls.viewer_group], cls.organization_b)
        cls.manager_a = user("m27.manager.a", cls.company_a, [cls.quality_manager_group], cls.organization_a)
        cls.supervisor_a = user("m27.supervisor.a", cls.company_a, [cls.quality_supervisor_group], cls.organization_a)
        cls.licensing_admin = user("m27.licensing.admin", cls.company_a, [cls.licensing_admin_group], cls.organization_a)

    def test_customer_roles_do_not_inherit_system_administration(self):
        for user in (self.viewer_a, self.manager_a, self.supervisor_a, self.licensing_admin):
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

    def test_licensing_admin_keeps_only_license_workflow_access(self):
        license_model = self.env["pm.qms.license"].with_user(self.licensing_admin)
        activation_model = self.env["pm.qms.activation.request"].with_user(self.licensing_admin)
        framework_model = self.env["pm.qms.framework.pack"].with_user(self.licensing_admin)
        self.assertTrue(license_model.check_access_rights("read", raise_exception=False))
        self.assertTrue(activation_model.check_access_rights("create", raise_exception=False))
        self.assertFalse(framework_model.check_access_rights("write", raise_exception=False))
        self.assertFalse(
            self.env["res.users"].with_user(self.licensing_admin).check_access_rights("write", raise_exception=False)
        )
