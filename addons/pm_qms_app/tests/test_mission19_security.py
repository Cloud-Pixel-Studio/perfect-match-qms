from odoo import Command
from odoo.tests.common import TransactionCase


class TestMission19Security(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.organization = cls.env["pm.qms.organization"].sudo().create(
            {"name": "Mission 19 Org", "code": "M19-ORG", "company_id": cls.company.id}
        )
        cls.site_a = cls.env["pm.qms.site"].sudo().create(
            {
                "name": "Mission 19 Site A",
                "code": "M19-A",
                "organization_id": cls.organization.id,
                "site_type": "manufacturing",
            }
        )
        cls.site_b = cls.env["pm.qms.site"].sudo().create(
            {
                "name": "Mission 19 Site B",
                "code": "M19-B",
                "organization_id": cls.organization.id,
                "site_type": "inspection",
            }
        )
        cls.process_a = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "Mission 19 Process A",
                "code": "M19-P-A",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
                "site_ids": [Command.set([cls.site_a.id])],
            }
        )
        cls.process_b = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "Mission 19 Process B",
                "code": "M19-P-B",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
                "site_ids": [Command.set([cls.site_b.id])],
            }
        )
        cls.risk_a = cls.env["pm.qms.risk"].sudo().create(
            {
                "name": "Mission 19 Risk A",
                "code": "M19-R-A",
                "organization_id": cls.organization.id,
                "process_id": cls.process_a.id,
                "description": "Security scope test record A",
            }
        )
        cls.risk_b = cls.env["pm.qms.risk"].sudo().create(
            {
                "name": "Mission 19 Risk B",
                "code": "M19-R-B",
                "organization_id": cls.organization.id,
                "process_id": cls.process_b.id,
                "description": "Security scope test record B",
            }
        )
        cls.viewer = cls.env["res.users"].sudo().create(
            {
                "name": "Mission 19 Viewer",
                "login": "mission19.viewer",
                "email": "mission19.viewer@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.set([cls.env.ref("pm_qms_core.group_qms_viewer").id])],
                "qms_organization_ids": [Command.set([cls.organization.id])],
                "qms_site_ids": [Command.set([cls.site_a.id])],
                "qms_process_ids": [Command.set([cls.process_a.id])],
            }
        )

    def test_empty_organization_scope_fails_closed(self):
        viewer_env = self.env["pm.qms.organization"].with_user(self.viewer)
        self.viewer.sudo().write({"qms_organization_ids": [Command.clear()]})
        self.assertFalse(viewer_env.search([]))

    def test_selected_process_scope_filters_operational_records(self):
        risks = self.env["pm.qms.risk"].with_user(self.viewer).search([])
        self.assertEqual(risks, self.risk_a)

    def test_viewer_is_read_only_for_risk_records(self):
        risk_model = self.env["pm.qms.risk"].with_user(self.viewer)
        self.assertTrue(risk_model.check_access_rights("read", raise_exception=False))
        self.assertFalse(risk_model.check_access_rights("write", raise_exception=False))

    def test_qms_role_is_not_odoo_system_administrator(self):
        self.assertTrue(self.viewer.has_group("pm_qms_core.group_qms_viewer"))
        self.assertFalse(self.viewer.has_group("base.group_system"))
