from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsCapa(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "CAPA Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "CAPA Organization", "code": "PM-CAPA-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "CAPA Process",
                "code": "PM-CAPA-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "CAPA Control",
                "code": "PM-QMS-CAPA-001",
                "objective": "Define corrective action verification.",
                "process_id": cls.process.id,
            }
        )
        cls.requirement = cls.env["pm.qms.evidence.requirement"].create(
            {"name": "CAPA evidence requirement", "control_id": cls.control.id, "evidence_type": "record"}
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "CAPA implementation",
                "code": "CAPA-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.document = cls.env["pm.qms.document"].create(
            {
                "name": "CAPA Procedure",
                "code": "PM-CAPA-DOC-001",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "document_type": "procedure",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
            }
        )
        cls.evidence = cls.env["pm.qms.evidence"].create(
            {
                "name": "CAPA evidence",
                "control_instance_id": cls.control_instance.id,
                "evidence_requirement_id": cls.requirement.id,
                "document_ids": [(6, 0, [cls.document.id])],
            }
        )
        cls.risk = cls.env["pm.qms.risk"].create(
            {
                "name": "CAPA source risk",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "description": "Risk requiring action.",
                "mitigation_plan": "Create a corrective action plan.",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
                "related_document_ids": [(6, 0, [cls.document.id])],
            }
        )
        cls.ncr = cls.env["pm.qms.nonconformity"].create(
            {
                "name": "CAPA source NCR",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "source_type": "document",
                "severity": "major",
                "description": "A superseded instruction was found.",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
                "related_document_ids": [(6, 0, [cls.document.id])],
                "related_evidence_ids": [(6, 0, [cls.evidence.id])],
                "related_risk_ids": [(6, 0, [cls.risk.id])],
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other CAPA Organization", "code": "PM-CAPA-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other CAPA Process",
                "code": "PM-CAPA-PROC2",
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

    def _capa_values(self, **extra_values):
        values = {
            "name": "Distribution verification CAPA",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "source_type": "other",
            "problem_statement": "Distribution verification needs a clear owner.",
            "root_cause_method": "5why",
            "root_cause": "The recurring owner was not assigned.",
            "action_plan": "Assign owner and verify completion.",
            "target_date": "2026-01-01",
            "effectiveness_review_date": "2026-01-15",
            "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
            "related_document_ids": [(6, 0, [self.document.id])],
        }
        values.update(extra_values)
        return values

    def test_capa_creation_5why_multiple_actions_effectiveness_and_history(self):
        manager = self._create_test_user("pmqms.capa.manager", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values())
        self.env["pm.qms.capa.why"].with_user(manager).create(
            {"capa_id": capa.id, "sequence": 1, "question": "Why did this happen?", "answer": "Ownership was unclear."}
        )
        action_1 = self.env["pm.qms.capa.action"].with_user(manager).create(
            {"capa_id": capa.id, "name": "Assign owner", "target_date": "2026-01-01"}
        )
        action_2 = self.env["pm.qms.capa.action"].with_user(manager).create(
            {"capa_id": capa.id, "name": "Verify distribution points", "target_date": "2026-01-01"}
        )

        self.assertRegex(capa.code, r"^PM-CAPA-\d{5}$")
        self.assertEqual(len(capa.why_ids), 1)
        self.assertEqual(capa.action_count, 2)
        self.assertTrue(action_1.is_overdue)

        capa.with_user(manager).action_start_analysis()
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        action_1.with_user(manager).action_start()
        action_1.with_user(manager).action_complete()
        action_2.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()

        capa.with_user(manager).write({"effectiveness_notes": "The follow-up check shows the action worked."})
        capa.with_user(manager).action_mark_effective()
        capa.with_user(manager).action_close()

        self.assertEqual(capa.state, "closed")
        self.assertEqual(capa.effectiveness_result, "effective")
        events = self.env["pm.qms.event"].search([("res_model", "=", "pm.qms.capa"), ("res_id", "=", capa.id)])
        self.assertGreaterEqual(len(events), 6)

    def test_ineffective_capa_can_reopen_without_destroying_result(self):
        manager = self._create_test_user("pmqms.capa.manager2", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values(name="Ineffective CAPA"))
        action = self.env["pm.qms.capa.action"].with_user(manager).create({"capa_id": capa.id, "name": "Initial action"})

        capa.with_user(manager).action_start_analysis()
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        action.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()
        capa.with_user(manager).write({"effectiveness_notes": "The issue repeated during verification."})
        capa.with_user(manager).action_mark_ineffective()

        self.assertEqual(capa.effectiveness_result, "ineffective")
        capa.with_user(manager).action_reopen_actions()
        self.assertEqual(capa.state, "action_planned")
        self.assertEqual(capa.effectiveness_result, "ineffective")

    def test_ncr_and_risk_create_structured_capa(self):
        capa_from_ncr_action = self.ncr.action_create_capa()
        capa_from_ncr = self.env["pm.qms.capa"].browse(capa_from_ncr_action["res_id"])
        self.assertEqual(capa_from_ncr.source_ncr_id, self.ncr)
        self.assertEqual(capa_from_ncr.source_type, "ncr")
        self.assertEqual(capa_from_ncr.related_control_instance_ids, self.control_instance)

        capa_from_risk_action = self.risk.action_create_capa()
        capa_from_risk = self.env["pm.qms.capa"].browse(capa_from_risk_action["res_id"])
        self.assertEqual(capa_from_risk.source_risk_id, self.risk)
        self.assertEqual(capa_from_risk.source_type, "risk")
        self.assertEqual(capa_from_risk.action_plan, self.risk.mitigation_plan)

    def test_capa_security_company_isolation_and_closure_controls(self):
        qms_user = self._create_test_user("pmqms.capa.user", self.qms_user_group)
        other_user = self._create_test_user("pmqms.capa.other", self.qms_user_group, self.other_company)
        capa = self.env["pm.qms.capa"].with_user(qms_user).create(self._capa_values(name="User CAPA"))

        with self.assertRaises(AccessError):
            capa.with_user(qms_user).action_close()
        with self.assertRaises(AccessError):
            capa.with_user(qms_user).write({"state": "closed"})
        self.assertFalse(self.env["pm.qms.capa"].with_user(other_user).search([("id", "=", capa.id)]))

        other_control = self.env["pm.qms.control"].create(
            {
                "name": "Other CAPA Control",
                "code": "PM-QMS-CAPA-OTHER",
                "objective": "Other company only.",
                "process_id": self.other_process.id,
            }
        )
        other_instance = self.env["pm.qms.control.instance"].create(
            {
                "name": "Other CAPA implementation",
                "code": "OTHER-CAPA-PM-QMS-001",
                "control_id": other_control.id,
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.capa"].create(
                self._capa_values(name="Cross company CAPA", related_control_instance_ids=[(6, 0, [other_instance.id])])
            )

    def test_integration_chain_preserves_framework_control(self):
        manager = self._create_test_user("pmqms.capa.integration", self.qms_manager_group)
        original_control_state = self.control.state
        original_control_name = self.control.name

        self.evidence.with_user(manager).action_submit()
        self.evidence.with_user(manager).action_review()
        self.evidence.with_user(manager).action_accept()
        self.ncr.action_open()
        self.ncr.with_user(manager).action_start_investigation()
        self.ncr.with_user(manager).action_require_action()
        capa = self.env["pm.qms.capa"].browse(self.ncr.action_create_capa()["res_id"])
        action = self.env["pm.qms.capa.action"].with_user(manager).create({"capa_id": capa.id, "name": "Verify after next review"})
        capa.with_user(manager).write({"root_cause": "The controlled distribution check was not assigned."})
        capa.with_user(manager).action_start_analysis()
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        action.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()
        capa.with_user(manager).write({"effectiveness_notes": "Next review showed current instructions in use."})
        capa.with_user(manager).action_mark_effective()
        capa.with_user(manager).action_close()

        self.assertEqual(capa.source_ncr_id, self.ncr)
        self.assertEqual(capa.related_control_instance_ids, self.control_instance)
        self.assertEqual(self.control.state, original_control_state)
        self.assertEqual(self.control.name, original_control_name)
        self.assertNotIn("risk_ids", self.control._fields)
        self.assertNotIn("nonconformity_ids", self.control._fields)
        self.assertNotIn("capa_ids", self.control._fields)
