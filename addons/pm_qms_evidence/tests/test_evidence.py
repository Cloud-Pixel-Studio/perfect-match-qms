from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsEvidence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Evidence Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.organization = cls.env["pm.qms.organization"].create(
            {
                "name": "Evidence Organization",
                "code": "PM-EVD-ORG",
                "company_id": cls.company.id,
            }
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Evidence Process",
                "code": "PM-EVD-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Evidence Review Control",
                "code": "PM-QMS-EVD-001",
                "objective": "Define evidence review using Perfect Match methodology.",
                "process_id": cls.process.id,
            }
        )
        cls.requirement = cls.env["pm.qms.evidence.requirement"].create(
            {
                "name": "Approved controlled record",
                "control_id": cls.control.id,
                "evidence_type": "document",
                "mandatory": True,
            }
        )
        cls.optional_requirement = cls.env["pm.qms.evidence.requirement"].create(
            {
                "name": "Optional supporting note",
                "control_id": cls.control.id,
                "evidence_type": "record",
                "mandatory": False,
            }
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Evidence implementation",
                "code": "EVD-PM-QMS-EVD-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.document = cls.env["pm.qms.document"].create(
            {
                "name": "Evidence Procedure",
                "code": "PM-EVD-DOC-001",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "document_type": "procedure",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {
                "name": "Evidence Other Organization",
                "code": "PM-EVD-ORG2",
                "company_id": cls.other_company.id,
            }
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Evidence Other Process",
                "code": "PM-EVD-PROC2",
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

    def _evidence_values(self, **extra_values):
        values = {
            "name": "Approved revision evidence",
            "control_instance_id": self.control_instance.id,
            "evidence_requirement_id": self.requirement.id,
            "document_ids": [(6, 0, [self.document.id])],
            "description": "Client implementation evidence record.",
        }
        values.update(extra_values)
        return values

    def test_evidence_submission_review_and_acceptance(self):
        qms_user = self._create_test_user("pmqms.evidence.user", self.qms_user_group)
        manager = self._create_test_user("pmqms.evidence.manager", self.qms_manager_group)
        evidence = self.env["pm.qms.evidence"].with_user(qms_user).create(self._evidence_values())

        self.assertEqual(evidence.state, "draft")
        evidence.with_user(qms_user).action_submit()
        self.assertEqual(evidence.state, "submitted")

        with self.assertRaises(AccessError):
            evidence.with_user(qms_user).action_accept()

        evidence.with_user(manager).action_review()
        self.assertEqual(evidence.state, "under_review")
        evidence.with_user(manager).action_accept()
        self.assertEqual(evidence.state, "accepted")
        self.assertEqual(evidence.reviewer_id, manager)
        self.assertTrue(evidence.reviewed_on)
        events = self.env["pm.qms.event"].search(
            [("res_model", "=", "pm.qms.evidence"), ("res_id", "=", evidence.id)]
        )
        self.assertIn("accepted", events.mapped("new_state"))

    def test_rejected_evidence_retains_review_history_and_allows_replacement(self):
        manager = self._create_test_user("pmqms.evidence.manager2", self.qms_manager_group)
        rejected = self.env["pm.qms.evidence"].create(self._evidence_values(name="Rejected evidence"))
        rejected.action_submit()
        rejected.with_user(manager).action_review()
        rejected.with_user(manager).write({"review_notes": "Evidence does not show current authorization."})
        rejected.with_user(manager).action_reject()

        replacement = self.env["pm.qms.evidence"].create(self._evidence_values(name="Replacement evidence"))
        replacement.action_submit()
        replacement.with_user(manager).action_accept()

        self.assertEqual(rejected.state, "rejected")
        self.assertEqual(rejected.reviewer_id, manager)
        self.assertTrue(rejected.reviewed_on)
        self.assertIn("current authorization", rejected.review_notes)
        self.assertEqual(replacement.state, "accepted")

    def test_evidence_completion_counts_required_accepted_and_missing(self):
        manager = self._create_test_user("pmqms.evidence.manager3", self.qms_manager_group)
        self.assertEqual(self.control_instance.required_evidence_count, 1)
        self.assertEqual(self.control_instance.accepted_evidence_count, 0)
        self.assertEqual(self.control_instance.missing_evidence_count, 1)

        evidence = self.env["pm.qms.evidence"].create(self._evidence_values(name="Completion evidence"))
        evidence.action_submit()
        evidence.with_user(manager).action_accept()

        self.control_instance.invalidate_recordset(
            ["required_evidence_count", "accepted_evidence_count", "missing_evidence_count"]
        )
        self.assertEqual(self.control_instance.required_evidence_count, 1)
        self.assertEqual(self.control_instance.accepted_evidence_count, 1)
        self.assertEqual(self.control_instance.missing_evidence_count, 0)

    def test_requirement_must_match_control_instance_control(self):
        other_control = self.env["pm.qms.control"].create(
            {
                "name": "Other Evidence Control",
                "code": "PM-QMS-EVD-OTHER",
                "objective": "Separate original Perfect Match control.",
                "process_id": self.process.id,
            }
        )
        other_requirement = self.env["pm.qms.evidence.requirement"].create(
            {
                "name": "Other requirement",
                "control_id": other_control.id,
                "evidence_type": "record",
            }
        )

        with self.assertRaises(ValidationError):
            self.env["pm.qms.evidence"].create(
                self._evidence_values(
                    name="Mismatched requirement evidence",
                    evidence_requirement_id=other_requirement.id,
                )
            )

    def test_evidence_document_must_match_organization(self):
        other_document = self.env["pm.qms.document"].create(
            {
                "name": "Other Evidence Document",
                "code": "PM-EVD-DOC-OTHER",
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
                "document_type": "procedure",
            }
        )

        with self.assertRaises(ValidationError):
            self.env["pm.qms.evidence"].create(
                self._evidence_values(
                    name="Wrong organization evidence",
                    document_ids=[(6, 0, [other_document.id])],
                )
            )

    def test_evidence_multicompany_isolation(self):
        other_user = self._create_test_user("pmqms.evidence.other", self.qms_user_group, self.other_company)
        evidence = self.env["pm.qms.evidence"].create(self._evidence_values(name="Company one evidence"))

        self.assertFalse(self.env["pm.qms.evidence"].with_user(other_user).search([("id", "=", evidence.id)]))

    def test_m25_8_requirement_identity_and_reviewer_context(self):
        self.requirement.write({
            "definition_key": "PM-QMS-EVID-PM-QMP-TEST-001",
            "description": "A current controlled source.",
            "acceptance_criteria": "Owner is identified.\nDate is present.",
        })
        evidence = self.env["pm.qms.evidence"].create(self._evidence_values())
        self.assertEqual(evidence.requirement_description, "A current controlled source.")
        self.assertEqual(evidence.requirement_acceptance_criteria, "Owner is identified.\nDate is present.")
        with self.assertRaises(ValidationError):
            self.requirement.write({"definition_key": "PM-QMS-EVID-OTHER"})

    def test_m25_8_archived_evidence_is_excluded_from_live_completion(self):
        manager = self._create_test_user("pmqms.evidence.archive_manager", self.qms_manager_group)
        evidence = self.env["pm.qms.evidence"].create(self._evidence_values())
        evidence.action_submit()
        evidence.with_user(manager).action_accept()
        evidence.with_context(pm_qms_evidence_workflow=True).write({"active": False})
        self.control_instance.invalidate_recordset([
            "required_evidence_count", "accepted_evidence_count", "missing_evidence_count"
        ])
        self.assertEqual(self.control_instance.required_evidence_count, 1)
        self.assertEqual(self.control_instance.accepted_evidence_count, 0)
        self.assertEqual(self.control_instance.missing_evidence_count, 1)
