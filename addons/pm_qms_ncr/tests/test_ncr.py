from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsNcr(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "NCR Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "NCR Organization", "code": "PM-NCR-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "NCR Process",
                "code": "PM-NCR-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "NCR Control",
                "code": "PM-QMS-NCR-001",
                "objective": "Define nonconformity intake and response.",
                "process_id": cls.process.id,
            }
        )
        cls.requirement = cls.env["pm.qms.evidence.requirement"].create(
            {"name": "NCR evidence requirement", "control_id": cls.control.id, "evidence_type": "record"}
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "NCR implementation",
                "code": "NCR-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.document = cls.env["pm.qms.document"].create(
            {
                "name": "NCR Procedure",
                "code": "PM-NCR-DOC-001",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "document_type": "procedure",
            }
        )
        cls.evidence = cls.env["pm.qms.evidence"].create(
            {
                "name": "NCR evidence",
                "control_instance_id": cls.control_instance.id,
                "evidence_requirement_id": cls.requirement.id,
            }
        )
        cls.risk = cls.env["pm.qms.risk"].create(
            {
                "name": "Related NCR Risk",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "description": "A process issue could repeat.",
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other NCR Organization", "code": "PM-NCR-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other NCR Process",
                "code": "PM-NCR-PROC2",
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

    def _ncr_values(self, **extra_values):
        values = {
            "name": "Superseded instruction found",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "source_type": "document",
            "severity": "major",
            "description": "A superseded work instruction was found at a demo workstation.",
            "containment_required": True,
            "containment_action": "Remove the superseded copy.",
            "target_date": "2026-01-01",
            "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
            "related_document_ids": [(6, 0, [self.document.id])],
            "related_evidence_ids": [(6, 0, [self.evidence.id])],
            "related_risk_ids": [(6, 0, [self.risk.id])],
        }
        values.update(extra_values)
        return values

    def test_ncr_creation_sequence_containment_workflow_and_history(self):
        reporter = self._create_test_user("pmqms.ncr.reporter", self.qms_user_group)
        manager = self._create_test_user("pmqms.ncr.manager", self.qms_manager_group)
        ncr = self.env["pm.qms.nonconformity"].with_user(reporter).create(self._ncr_values())

        self.assertRegex(ncr.code, r"^PM-NCR-\d{5}$")
        self.assertTrue(ncr.is_overdue)
        ncr.with_user(reporter).action_open()
        self.assertEqual(ncr.opened_by_id, reporter)

        ncr.with_user(manager).action_start_containment()
        with self.assertRaises(UserError):
            ncr.with_user(manager).action_start_investigation()

        ncr.with_user(manager).write({"containment_completed": True, "containment_date": "2026-08-14"})
        ncr.with_user(manager).action_start_investigation()
        ncr.with_user(manager).write({"root_cause_summary": "Distribution verification was not confirmed."})
        ncr.with_user(manager).action_require_action()
        ncr.with_user(manager).action_start_verification()
        ncr.with_user(manager).write({"closure_notes": "Corrective action created and verification completed."})
        ncr.with_user(manager).action_close()

        self.assertEqual(ncr.state, "closed")
        self.assertEqual(ncr.closed_by_id, manager)
        events = self.env["pm.qms.event"].search([("res_model", "=", "pm.qms.nonconformity"), ("res_id", "=", ncr.id)])
        self.assertGreaterEqual(len(events), 6)

    def test_ncr_security_closure_requirements_and_relationship_validation(self):
        reporter = self._create_test_user("pmqms.ncr.reporter2", self.qms_user_group)
        ncr = self.env["pm.qms.nonconformity"].with_user(reporter).create(
            self._ncr_values(name="Reporter NCR", containment_required=False)
        )
        ncr.with_user(reporter).action_open()

        with self.assertRaises(AccessError):
            ncr.with_user(reporter).action_close()
        with self.assertRaises(AccessError):
            ncr.with_user(reporter).write({"state": "closed"})

        other_risk = self.env["pm.qms.risk"].create(
            {
                "name": "Other company risk",
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
                "description": "Other company only.",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.nonconformity"].create(
                self._ncr_values(name="Cross company NCR", related_risk_ids=[(6, 0, [other_risk.id])])
            )

    def test_ncr_company_isolation(self):
        other_user = self._create_test_user("pmqms.ncr.other", self.qms_user_group, self.other_company)
        ncr = self.env["pm.qms.nonconformity"].create(self._ncr_values(name="Company one NCR"))

        self.assertFalse(self.env["pm.qms.nonconformity"].with_user(other_user).search([("id", "=", ncr.id)]))
