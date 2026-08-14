import base64

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsRisk(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Risk Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Risk Organization", "code": "PM-RISK-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Risk Process",
                "code": "PM-RISK-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Risk Response Control",
                "code": "PM-QMS-RISK-001",
                "objective": "Define internal risk response ownership.",
                "process_id": cls.process.id,
            }
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Risk implementation",
                "code": "RISK-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.document = cls.env["pm.qms.document"].create(
            {
                "name": "Risk Response Procedure",
                "code": "PM-RISK-DOC-001",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "document_type": "procedure",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Risk Organization", "code": "PM-RISK-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Risk Process",
                "code": "PM-RISK-PROC2",
                "organization_id": cls.other_organization.id,
                "company_id": cls.other_company.id,
            }
        )

    @classmethod
    def _create_test_user(cls, login, group, company=None):
        company = company or cls.company
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": company.id,
                "company_ids": [(6, 0, [company.id])],
                "group_ids": [(6, 0, [cls.base_user_group.id, group.id])],
            }
        )

    def _risk_values(self, **extra_values):
        values = {
            "name": "Delayed document approval",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "description": "Approval delay may leave obsolete work instructions in use.",
            "cause": "Review ownership is unclear.",
            "potential_effect": "Teams may use obsolete information.",
            "likelihood": 3,
            "impact": 4,
            "residual_likelihood": 2,
            "residual_impact": 2,
            "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
            "related_document_ids": [(6, 0, [self.document.id])],
        }
        values.update(extra_values)
        return values

    def test_risk_creation_scoring_residual_and_workflow_history(self):
        manager = self._create_test_user("pmqms.risk.manager", self.qms_manager_group)
        risk = self.env["pm.qms.risk"].with_user(manager).create(self._risk_values())

        self.assertRegex(risk.code, r"^PM-RISK-\d{5}$")
        self.assertEqual(risk.initial_score, 12)
        self.assertEqual(risk.initial_level, "high")
        self.assertEqual(risk.residual_score, 4)
        self.assertEqual(risk.residual_level, "low")
        self.assertEqual(risk.related_control_instance_ids, self.control_instance)

        risk.with_user(manager).action_assess()
        risk.with_user(manager).action_require_action()
        risk.with_user(manager).action_start_monitoring()
        risk.with_user(manager).write({"closure_notes": "Risk response is operating as planned."})
        risk.with_user(manager).action_close()

        events = self.env["pm.qms.event"].search([("res_model", "=", "pm.qms.risk"), ("res_id", "=", risk.id)])
        self.assertGreaterEqual(len(events), 4)
        self.assertEqual(risk.state, "closed")
        self.assertEqual(risk.closed_by_id, manager)

    def test_opportunity_uses_same_model_and_overdue_logic(self):
        opportunity = self.env["pm.qms.risk"].create(
            self._risk_values(
                name="Shorter approval cycle",
                risk_type="opportunity",
                benefit="Faster document release.",
                opportunity_action="Define a standard review lane.",
                target_date="2026-01-01",
            )
        )

        self.assertEqual(opportunity.risk_type, "opportunity")
        self.assertTrue(opportunity.is_overdue)
        self.assertGreater(opportunity.days_overdue, 0)

    def test_risk_company_and_organization_isolation(self):
        other_user = self._create_test_user("pmqms.risk.other", self.qms_user_group, self.other_company)
        risk = self.env["pm.qms.risk"].create(self._risk_values(name="Company one risk"))

        self.assertFalse(self.env["pm.qms.risk"].with_user(other_user).search([("id", "=", risk.id)]))

        other_document = self.env["pm.qms.document"].create(
            {
                "name": "Other Risk Document",
                "code": "PM-RISK-DOC-OTHER",
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
                "document_type": "procedure",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.risk"].create(
                self._risk_values(name="Cross organization risk", related_document_ids=[(6, 0, [other_document.id])])
            )

    def test_user_cannot_close_or_directly_change_status(self):
        qms_user = self._create_test_user("pmqms.risk.user", self.qms_user_group)
        risk = self.env["pm.qms.risk"].with_user(qms_user).create(self._risk_values(name="User reported risk"))

        with self.assertRaises(AccessError):
            risk.with_user(qms_user).action_close()
        with self.assertRaises(AccessError):
            risk.with_user(qms_user).write({"state": "closed"})

    def test_closure_requires_notes_and_attachment_access_is_protected(self):
        manager = self._create_test_user("pmqms.risk.manager2", self.qms_manager_group)
        other_user = self._create_test_user("pmqms.risk.other2", self.qms_user_group, self.other_company)
        risk = self.env["pm.qms.risk"].with_user(manager).create(self._risk_values(name="Attachment risk"))
        attachment = self.env["ir.attachment"].create(
            {
                "name": "risk-note.txt",
                "datas": base64.b64encode(b"protected risk note"),
                "res_model": "pm.qms.risk",
                "res_id": risk.id,
            }
        )
        risk.write({"attachment_ids": [(4, attachment.id)]})

        with self.assertRaises(UserError):
            risk.with_user(manager).action_close()
        with self.assertRaises(AccessError):
            attachment.with_user(other_user).read(["name"])
