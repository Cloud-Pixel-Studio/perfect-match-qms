import base64

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsAudit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Audit Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Audit Organization", "code": "PM-AUD-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Audit Process",
                "code": "PM-AUD-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Audit Control",
                "code": "PM-QMS-AUD-001",
                "objective": "Define internal audit traceability using Perfect Match wording.",
                "process_id": cls.process.id,
            }
        )
        cls.requirement = cls.env["pm.qms.evidence.requirement"].create(
            {"name": "Audit requirement", "control_id": cls.control.id, "evidence_type": "record"}
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Audit implementation",
                "code": "AUD-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.document = cls.env["pm.qms.document"].create(
            {
                "name": "Audit Procedure",
                "code": "PM-AUD-DOC-001",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "document_type": "procedure",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
            }
        )
        cls.implementation_evidence = cls.env["pm.qms.evidence"].create(
            {
                "name": "Audit implementation evidence",
                "control_instance_id": cls.control_instance.id,
                "evidence_requirement_id": cls.requirement.id,
                "document_ids": [(6, 0, [cls.document.id])],
            }
        )
        cls.external_mapping = cls.env["pm.qms.external.mapping"].create(
            {
                "control_id": cls.control.id,
                "standard_name": "Example Standard",
                "edition": "2026",
                "reference": "X.X",
                "note": "Reference metadata only.",
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Audit Organization", "code": "PM-AUD-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Audit Process",
                "code": "PM-AUD-PROC2",
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

    def _program_values(self, **extra_values):
        values = {
            "name": "Internal Audit Program",
            "organization_id": self.organization.id,
            "date_start": "2026-08-01",
            "date_end": "2026-12-31",
            "objective": "Plan internal audits for selected Perfect Match processes.",
        }
        values.update(extra_values)
        return values

    def _audit_values(self, **extra_values):
        values = {
            "name": "Document control audit",
            "organization_id": self.organization.id,
            "planned_start": "2026-01-01",
            "planned_end": "2026-01-02",
            "audit_type": "process",
            "objective": "Evaluate the internal document control implementation.",
            "scope_summary": "Selected controlled documents and implementation records.",
        }
        values.update(extra_values)
        return values

    def _create_ready_audit(self, manager):
        program = self.env["pm.qms.audit.program"].with_user(manager).create(
            self._program_values(owner_id=manager.id)
        )
        audit = self.env["pm.qms.audit"].with_user(manager).create(
            self._audit_values(
                program_id=program.id,
                lead_auditor_id=manager.id,
                auditor_ids=[(6, 0, [manager.id])],
            )
        )
        self.env["pm.qms.audit.scope"].with_user(manager).create(
            {
                "audit_id": audit.id,
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "control_instance_ids": [(6, 0, [self.control_instance.id])],
                "description": "Document control implementation scope.",
            }
        )
        criterion = self.env["pm.qms.audit.criterion"].with_user(manager).create(
            {
                "audit_id": audit.id,
                "name": "Perfect Match control reference",
                "criterion_type": "perfect_match_control",
                "control_id": self.control.id,
                "control_instance_id": self.control_instance.id,
                "external_mapping_id": self.external_mapping.id,
                "reference": "PM-QMS-AUD-001",
            }
        )
        self.env["pm.qms.audit.plan.line"].with_user(manager).create(
            {
                "audit_id": audit.id,
                "planned_datetime": "2026-08-20 13:00:00",
                "duration": 1.5,
                "process_id": self.process.id,
                "activity": "Opening meeting and document walkthrough",
                "auditor_id": manager.id,
            }
        )
        evidence = self.env["pm.qms.audit.evidence"].with_user(manager).create(
            {
                "name": "Procedure sample",
                "audit_id": audit.id,
                "criterion_id": criterion.id,
                "source": "document_review",
                "description": "A controlled procedure was sampled against the internal register.",
                "document_id": self.document.id,
                "control_instance_id": self.control_instance.id,
            }
        )
        audit.with_user(manager).action_plan()
        audit.with_user(manager).action_record_independence()
        audit.with_user(manager).action_mark_ready()
        return audit, criterion, evidence

    def _finding_values(self, audit, criterion, evidence, **extra_values):
        values = {
            "name": "Audit finding",
            "title": "Audit finding title",
            "audit_id": audit.id,
            "classification": "observation",
            "description": "A useful observation from the audit.",
            "objective_evidence": "Original Perfect Match audit evidence wording.",
            "criterion_id": criterion.id,
            "process_id": self.process.id,
            "control_instance_id": self.control_instance.id,
            "audit_evidence_ids": [(6, 0, [evidence.id])],
            "due_date": "2026-01-01",
            "follow_up_date": "2026-01-15",
        }
        values.update(extra_values)
        return values

    def test_audit_program_audit_workflow_independence_and_history(self):
        manager = self._create_test_user("pmqms.audit.manager", self.qms_manager_group)
        program = self.env["pm.qms.audit.program"].with_user(manager).create(
            self._program_values(owner_id=manager.id)
        )
        program.with_user(manager).action_approve()
        program.with_user(manager).action_activate()
        self.assertRegex(program.code, r"^PM-AUDPROG-\d{5}$")
        self.assertEqual(program.state, "active")

        audit = self.env["pm.qms.audit"].with_user(manager).create(
            self._audit_values(program_id=program.id, lead_auditor_id=manager.id)
        )
        self.env["pm.qms.audit.scope"].with_user(manager).create(
            {
                "audit_id": audit.id,
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "control_instance_ids": [(6, 0, [self.control_instance.id])],
            }
        )
        self.env["pm.qms.audit.criterion"].with_user(manager).create(
            {
                "audit_id": audit.id,
                "name": "Internal control criterion",
                "criterion_type": "perfect_match_control",
                "control_id": self.control.id,
                "control_instance_id": self.control_instance.id,
                "reference": "PM-QMS-AUD-001",
            }
        )
        audit.with_user(manager).action_plan()
        with self.assertRaises(UserError):
            audit.with_user(manager).action_mark_ready()

        audit.with_user(manager).action_record_independence()
        self.assertTrue(audit.independence_confirmed)
        self.assertEqual(audit.independence_reviewed_by_id, manager)
        audit.with_user(manager).action_mark_ready()
        with self.assertRaises(UserError):
            audit.with_user(manager).action_complete()
        audit.with_user(manager).action_start()
        audit.with_user(manager).action_start_reporting()
        audit.with_user(manager).write({"conclusion": "Audit report data is complete; actions remain tracked separately."})
        audit.with_user(manager).action_complete()

        self.assertRegex(audit.code, r"^PM-AUD-\d{5}$")
        self.assertEqual(audit.state, "completed")
        events = self.env["pm.qms.event"].search([("res_model", "=", "pm.qms.audit"), ("res_id", "=", audit.id)])
        self.assertGreaterEqual(len(events), 5)

    def test_independence_override_requires_notes(self):
        manager = self._create_test_user("pmqms.audit.independence", self.qms_manager_group)
        audit = self.env["pm.qms.audit"].with_user(manager).create(
            self._audit_values(lead_auditor_id=manager.id)
        )
        self.env["pm.qms.audit.scope"].with_user(manager).create(
            {"audit_id": audit.id, "organization_id": self.organization.id, "process_id": self.process.id}
        )
        self.env["pm.qms.audit.criterion"].with_user(manager).create(
            {"audit_id": audit.id, "name": "Procedure criterion", "criterion_type": "company_procedure", "reference": "PM-PROC"}
        )

        with self.assertRaises(UserError):
            audit.with_user(manager).action_record_independence_override()
        audit.with_user(manager).write({"independence_notes": "Small team override reviewed and documented."})
        audit.with_user(manager).action_record_independence_override()
        audit.with_user(manager).action_plan()
        audit.with_user(manager).action_mark_ready()
        self.assertFalse(audit.independence_required)
        self.assertFalse(audit.independence_confirmed)

    def test_finding_classifications_and_ncr_gate(self):
        manager = self._create_test_user("pmqms.audit.findings", self.qms_manager_group)
        audit, criterion, evidence = self._create_ready_audit(manager)

        for classification in ("conformity", "observation", "opportunity_for_improvement"):
            finding = self.env["pm.qms.audit.finding"].with_user(manager).create(
                self._finding_values(
                    audit,
                    criterion,
                    evidence,
                    title=f"{classification} finding",
                    classification=classification,
                )
            )
            finding.with_user(manager).action_issue()
            with self.assertRaises(UserError):
                finding.with_user(manager).action_create_ncr()
            finding.with_user(manager).action_accept()
            finding.with_user(manager).write({"closure_notes": "Closed without formal NCR."})
            finding.with_user(manager).action_close()
            self.assertEqual(finding.state, "closed")

        with self.assertRaises(ValidationError):
            self.env["pm.qms.audit.finding"].with_user(manager).create(
                self._finding_values(
                    audit,
                    criterion,
                    evidence,
                    title="Invalid severity",
                    classification="observation",
                    severity="major",
                )
            )

        nonconformity = self.env["pm.qms.audit.finding"].with_user(manager).create(
            self._finding_values(
                audit,
                criterion,
                evidence,
                title="Internal nonconformity finding",
                classification="nonconformity",
                severity="major",
            )
        )
        with self.assertRaises(UserError):
            nonconformity.with_user(manager).action_create_ncr()
        nonconformity.with_user(manager).action_issue()
        action = nonconformity.with_user(manager).action_create_ncr()
        ncr = self.env["pm.qms.nonconformity"].browse(action["res_id"])
        self.assertEqual(nonconformity.state, "action_required")
        self.assertEqual(ncr.source_type, "audit")
        self.assertEqual(ncr.source_audit_id, audit)
        self.assertEqual(ncr.source_audit_finding_id, nonconformity)
        self.assertEqual(ncr.source_audit_evidence_ids, evidence)
        with self.assertRaises(UserError):
            nonconformity.with_user(manager).action_create_ncr()

    def test_audit_to_ncr_to_capa_preserves_independent_lifecycles(self):
        manager = self._create_test_user("pmqms.audit.integration", self.qms_manager_group)
        original_control_name = self.control.name
        original_control_state = self.control.state
        audit, criterion, evidence = self._create_ready_audit(manager)
        finding = self.env["pm.qms.audit.finding"].with_user(manager).create(
            self._finding_values(
                audit,
                criterion,
                evidence,
                title="Superseded instruction at workstation",
                classification="nonconformity",
                severity="minor",
            )
        )

        finding.with_user(manager).action_issue()
        ncr = self.env["pm.qms.nonconformity"].browse(finding.with_user(manager).action_create_ncr()["res_id"])
        ncr.with_user(manager).action_open()
        capa = self.env["pm.qms.capa"].browse(ncr.with_user(manager).action_create_capa()["res_id"])
        capa_action = self.env["pm.qms.capa.action"].with_user(manager).create(
            {"capa_id": capa.id, "name": "Replace superseded workstation instruction"}
        )
        capa.with_user(manager).write({"root_cause": "The local instruction check was not assigned."})
        capa.with_user(manager).action_start_analysis()
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        capa_action.with_user(manager).action_start()

        audit.with_user(manager).action_start()
        audit.with_user(manager).action_start_reporting()
        audit.with_user(manager).write({"conclusion": "Audit report is complete; corrective actions remain open."})
        audit.with_user(manager).action_complete()

        self.assertEqual(audit.state, "completed")
        self.assertEqual(finding.state, "action_required")
        self.assertEqual(ncr.state, "open")
        self.assertEqual(capa.state, "implementation")
        self.assertEqual(capa.source_ncr_id, ncr)
        self.assertEqual(self.control.name, original_control_name)
        self.assertEqual(self.control.state, original_control_state)
        self.assertNotIn("audit_ids", self.control._fields)

    def test_audit_security_multicompany_constraints_and_attachment_isolation(self):
        manager = self._create_test_user("pmqms.audit.security.manager", self.qms_manager_group)
        other_user = self._create_test_user("pmqms.audit.security.other", self.qms_user_group, self.other_company)
        qms_user = self._create_test_user("pmqms.audit.security.user", self.qms_user_group)
        audit, criterion, evidence = self._create_ready_audit(manager)
        finding = self.env["pm.qms.audit.finding"].with_user(manager).create(
            self._finding_values(audit, criterion, evidence, title="Protected finding")
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "audit-evidence.txt",
                "datas": base64.b64encode(b"protected audit evidence"),
                "res_model": "pm.qms.audit.evidence",
                "res_id": evidence.id,
            }
        )
        evidence.with_user(manager).write({"attachment_ids": [(4, attachment.id)]})

        self.assertFalse(self.env["pm.qms.audit"].with_user(other_user).search([("id", "=", audit.id)]))
        self.assertFalse(self.env["pm.qms.audit.program"].with_user(other_user).search([("id", "=", audit.program_id.id)]))
        self.assertFalse(self.env["pm.qms.audit.scope"].with_user(other_user).search([("audit_id", "=", audit.id)]))
        self.assertFalse(self.env["pm.qms.audit.criterion"].with_user(other_user).search([("audit_id", "=", audit.id)]))
        self.assertFalse(self.env["pm.qms.audit.evidence"].with_user(other_user).search([("id", "=", evidence.id)]))
        self.assertFalse(self.env["pm.qms.audit.finding"].with_user(other_user).search([("id", "=", finding.id)]))
        with self.assertRaises(AccessError):
            attachment.with_user(other_user).read(["name"])

        with self.assertRaises(AccessError):
            self.env["pm.qms.audit"].with_user(qms_user).create(self._audit_values(name="Unauthorized audit"))
        with self.assertRaises(AccessError):
            finding.with_user(qms_user).action_issue()

        other_control = self.env["pm.qms.control"].create(
            {
                "name": "Other Audit Control",
                "code": "PM-QMS-AUD-OTHER",
                "objective": "Other company only.",
                "process_id": self.other_process.id,
            }
        )
        other_instance = self.env["pm.qms.control.instance"].create(
            {
                "name": "Other audit implementation",
                "code": "OTHER-AUD-PM-QMS-001",
                "control_id": other_control.id,
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.audit.scope"].create(
                {
                    "audit_id": audit.id,
                    "organization_id": self.organization.id,
                    "process_id": self.process.id,
                    "control_instance_ids": [(6, 0, [other_instance.id])],
                }
            )

    def test_overdue_and_operational_relationship_metrics(self):
        manager = self._create_test_user("pmqms.audit.metrics", self.qms_manager_group)
        audit, criterion, evidence = self._create_ready_audit(manager)
        finding = self.env["pm.qms.audit.finding"].with_user(manager).create(
            self._finding_values(
                audit,
                criterion,
                evidence,
                title="Overdue audit finding",
                classification="nonconformity",
                severity="critical",
            )
        )

        self.assertTrue(audit.is_overdue)
        self.assertTrue(finding.is_overdue)
        self.assertTrue(finding.follow_up_is_overdue)
        self.assertEqual(self.control_instance.audit_finding_count, 1)
        self.assertEqual(self.control_instance.open_audit_finding_count, 1)
        self.assertIn(audit, self.control_instance.audit_ids)
        self.assertEqual(self.process.audit_finding_count, 1)
        self.assertIn(audit, self.process.audit_ids)
