from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestPmQmsCore(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.other_company = cls.env["res.company"].create({"name": "Other QMS Company"})
        cls.organization = cls.env["pm.qms.organization"].create(
            {
                "name": "Perfect Match Test Organization",
                "code": "PM-ORG-TST",
                "description": "Original Perfect Match test organization.",
                "company_id": cls.company.id,
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {
                "name": "Other QMS Organization",
                "code": "PM-ORG-OTHER",
                "company_id": cls.other_company.id,
            }
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Supplier Management",
                "code": "PM-PROC-SUP",
                "description": "Perfect Match proprietary process definition.",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Document Management",
                "code": "PM-PROC-OTHER",
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

    def _control_values(self, **extra_values):
        values = {
            "name": "Supplier Qualification and Monitoring",
            "objective": "Define supplier qualification using Perfect Match methodology.",
            "description": "Reusable proprietary implementation control.",
            "process_id": self.process.id,
        }
        values.update(extra_values)
        return values

    def test_process_creation_and_code(self):
        process = self.env["pm.qms.process"].create(
            {
                "name": "Document Control",
                "code": "PM-PROC-DOC",
                "organization_id": self.organization.id,
                "company_id": self.company.id,
                "process_type": "support",
                "inputs": "Draft controlled documents.",
                "outputs": "Approved controlled documents.",
            }
        )

        self.assertEqual(process.code, "PM-PROC-DOC")
        self.assertEqual(process.organization_id, self.organization)
        self.assertEqual(process.sequence, 10)

    def test_control_sequence_manual_code_and_state_flow(self):
        sequenced_control = self.env["pm.qms.control"].create(self._control_values())
        manual_control = self.env["pm.qms.control"].create(
            self._control_values(name="Manual Code Control", code="PM-QMS-SUP-001")
        )

        self.assertRegex(sequenced_control.code, r"^PM-QMS-\d{5}$")
        self.assertEqual(manual_control.code, "PM-QMS-SUP-001")
        self.assertEqual(sequenced_control.state, "draft")

        sequenced_control.action_activate()
        self.assertEqual(sequenced_control.state, "active")

        sequenced_control.action_retire()
        self.assertEqual(sequenced_control.state, "retired")

    def test_control_code_is_unique_per_company(self):
        self.env["pm.qms.control"].create(
            self._control_values(name="Unique Control A", code="PM-QMS-UNQ-001")
        )

        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["pm.qms.control"].create(
                    self._control_values(name="Unique Control B", code="PM-QMS-UNQ-001")
                )

    def test_activity_and_evidence_requirements(self):
        control = self.env["pm.qms.control"].create(
            self._control_values(name="Process Evidence Planning")
        )
        activity = self.env["pm.qms.activity"].create(
            {
                "control_id": control.id,
                "name": "Review current process ownership",
                "responsible_role": "Process owner",
                "expected_output": "Owner confirmed for the implementation activity.",
            }
        )
        evidence = self.env["pm.qms.evidence.requirement"].create(
            {
                "control_id": control.id,
                "name": "Approved process owner record",
                "evidence_type": "record",
                "mandatory": True,
            }
        )

        self.assertEqual(activity.control_id, control)
        self.assertEqual(activity.company_id, control.company_id)
        self.assertEqual(evidence.control_id, control)
        self.assertEqual(evidence.company_id, control.company_id)
        self.assertTrue(evidence.mandatory)

    def test_external_mapping_is_reference_only(self):
        control = self.env["pm.qms.control"].create(
            self._control_values(name="External Reference Separation")
        )
        mapping = self.env["pm.qms.external.mapping"].create(
            {
                "control_id": control.id,
                "standard_name": "Example Standard",
                "edition": "2026",
                "reference": "X.X",
                "note": "Reference metadata only.",
            }
        )

        self.assertEqual(mapping.control_id, control)
        self.assertIn("standard_name", mapping._fields)
        self.assertIn("reference", mapping._fields)
        self.assertNotIn("standard_text", mapping._fields)
        self.assertNotIn("requirement_text", mapping._fields)
        self.assertNotIn("standard_text", control._fields)

    def test_control_definition_and_instances_are_separate(self):
        control = self.env["pm.qms.control"].create(
            self._control_values(name="Controlled Document Authorization", code="PM-QMS-DOC-001")
        )
        second_organization = self.env["pm.qms.organization"].create(
            {
                "name": "Second Same-Company Organization",
                "code": "PM-ORG-TST2",
                "company_id": self.company.id,
            }
        )
        second_process = self.env["pm.qms.process"].create(
            {
                "name": "Second Document Management",
                "code": "PM-PROC-DOC2",
                "organization_id": second_organization.id,
                "company_id": self.company.id,
            }
        )

        first_instance = self.env["pm.qms.control.instance"].create(
            {
                "name": "Primary organization implementation",
                "code": "ORG1-PM-QMS-DOC-001",
                "control_id": control.id,
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "implementation_status": "implemented",
            }
        )
        second_instance = self.env["pm.qms.control.instance"].create(
            {
                "name": "Second organization implementation",
                "code": "ORG2-PM-QMS-DOC-001",
                "control_id": control.id,
                "organization_id": second_organization.id,
                "process_id": second_process.id,
                "implementation_status": "in_progress",
            }
        )

        self.assertEqual(control.state, "draft")
        self.assertEqual(first_instance.implementation_status, "implemented")
        self.assertEqual(second_instance.implementation_status, "in_progress")
        self.assertEqual(len(control.control_instance_ids), 2)

    def test_control_instance_company_boundaries(self):
        control = self.env["pm.qms.control"].create(
            self._control_values(name="Company Bound Control", code="PM-QMS-BOUND-001")
        )

        with self.assertRaises(ValidationError):
            self.env["pm.qms.control.instance"].create(
                {
                    "name": "Cross-company instance should fail",
                    "code": "OTHER-PM-QMS-BOUND-001",
                    "control_id": control.id,
                    "organization_id": self.other_organization.id,
                    "process_id": self.other_process.id,
                }
            )

    def test_control_instance_record_rules_isolate_companies(self):
        control = self.env["pm.qms.control"].create(
            self._control_values(name="Visible Only To Company", code="PM-QMS-VIS-001")
        )
        instance = self.env["pm.qms.control.instance"].create(
            {
                "name": "Visible implementation",
                "code": "ORG1-PM-QMS-VIS-001",
                "control_id": control.id,
                "organization_id": self.organization.id,
                "process_id": self.process.id,
            }
        )
        other_user = self._create_test_user("pmqms.other.reader", self.qms_user_group, self.other_company)

        visible = self.env["pm.qms.control.instance"].with_user(other_user).search([("id", "=", instance.id)])
        self.assertFalse(visible)

    def test_basic_security_access(self):
        qms_user = self._create_test_user("pmqms.reader", self.qms_user_group)
        qms_manager = self._create_test_user("pmqms.manager", self.qms_manager_group)

        self.process.with_user(qms_user).read(["name", "code"])
        with self.assertRaises(AccessError):
            self.env["pm.qms.process"].with_user(qms_user).create(
                {
                    "name": "Reader Should Not Create",
                    "code": "PM-PROC-NOPE",
                    "company_id": self.company.id,
                }
            )

        manager_process = self.env["pm.qms.process"].with_user(qms_manager).create(
            {
                "name": "Manager Created Process",
                "code": "PM-PROC-MGR",
                "company_id": self.company.id,
            }
        )
        self.assertEqual(manager_process.code, "PM-PROC-MGR")

        control = self.env["pm.qms.control"].create(
            self._control_values(name="Security Control", code="PM-QMS-SEC-001")
        )
        self.env["pm.qms.control.instance"].with_user(qms_manager).create(
            {
                "name": "Manager instance",
                "code": "SEC-PM-QMS-001",
                "control_id": control.id,
                "organization_id": self.organization.id,
                "process_id": self.process.id,
            }
        )
        with self.assertRaises(AccessError):
            self.env["pm.qms.control.instance"].with_user(qms_user).create(
                {
                    "name": "Reader should not create instance",
                    "code": "NOPE-PM-QMS-001",
                    "control_id": control.id,
                    "organization_id": self.organization.id,
                    "process_id": self.process.id,
                }
            )
