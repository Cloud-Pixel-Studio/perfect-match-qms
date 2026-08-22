from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsCustomerSupplierQuality(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Customer Quality Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")

        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Customer Supplier Quality Organization", "code": "PM-CQ-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Customer Supplier Quality Process",
                "code": "PM-CQ-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.customer = cls.env["res.partner"].create({"name": "Fictional Customer", "company_id": cls.company.id})
        cls.supplier = cls.env["res.partner"].create({"name": "Fictional Supplier", "company_id": cls.company.id})

        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Customer Quality Organization", "code": "PM-CQ-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Customer Quality Process",
                "code": "PM-CQ-PROC2",
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

    def _complaint_values(self, **extra_values):
        values = {
            "name": "Customer reported dimensional escape",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "customer_id": self.customer.id,
            "received_date": "2026-01-05",
            "response_due_date": "2026-01-10",
            "description": "Customer reported a contained dimensional escape in a shipped lot.",
            "customer_reference": "CUST-REF-001",
            "product_reference": "PM-PART-001",
            "lot_serial_reference": "LOT-001",
            "severity": "high",
            "priority": "urgent",
            "containment_required": True,
            "containment_action": "Quarantine suspect lot and notify the customer contact.",
        }
        values.update(extra_values)
        return values

    def _supplier_issue_values(self, **extra_values):
        values = {
            "name": "Supplier certificate discrepancy",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "supplier_id": self.supplier.id,
            "issue_date": "2026-01-07",
            "description": "Supplier certificate did not match the incoming inspection record.",
            "supplier_reference": "SUP-REF-001",
            "product_reference": "PM-MAT-001",
            "severity": "high",
            "containment_required": True,
            "containment_action": "Hold affected incoming material pending supplier response.",
            "scar_required": True,
        }
        values.update(extra_values)
        return values

    def test_customer_complaint_links_existing_ncr_capa_and_8d(self):
        manager = self._create_test_user("pmqms.cq.manager", self.qms_manager_group)
        complaint = self.env["pm.qms.customer.complaint"].with_user(manager).create(self._complaint_values())

        self.assertRegex(complaint.code, r"^CC-\d{4}-\d{4}$")
        self.assertTrue(complaint.is_response_overdue)
        complaint.with_user(manager).action_under_review()
        complaint.with_user(manager).action_start_containment()
        complaint.with_user(manager).action_complete_containment()

        first_ncr_action = complaint.with_user(manager).action_create_ncr()
        first_ncr = self.env["pm.qms.nonconformity"].browse(first_ncr_action["res_id"])
        second_ncr_action = complaint.with_user(manager).action_create_ncr()
        second_ncr = self.env["pm.qms.nonconformity"].browse(second_ncr_action["res_id"])
        self.assertEqual(first_ncr, second_ncr)
        self.assertEqual(first_ncr.source_type, "customer")
        self.assertEqual(first_ncr.customer_complaint_id, complaint)

        eight_d_action = complaint.with_user(manager).action_create_eight_d()
        eight_d = self.env["pm.qms.eight.d"].browse(eight_d_action["res_id"])
        self.assertEqual(eight_d.source_type, "complaint")
        self.assertEqual(eight_d.complaint_id, complaint)
        self.assertEqual(eight_d.ncr_id, first_ncr)

        rca_action = eight_d.with_user(manager).action_create_root_cause()
        rca = self.env["pm.qms.root.cause.analysis"].browse(rca_action["res_id"])
        self.env["pm.qms.root.cause.line"].with_user(manager).create(
            {"analysis_id": rca.id, "sequence": 1, "question": "Why was it shipped?", "answer": "Final check missed the condition."}
        )
        rca.with_user(manager).write({"root_cause": "The final check was not linked to the current inspection characteristic."})
        rca.with_user(manager).action_submit_review()
        rca.with_user(manager).action_approve()

        eight_d.with_user(manager).write(
            {
                "d4_root_cause": rca.root_cause,
                "d5_corrective_action": "Update the final inspection instruction and verify first-pass compliance.",
            }
        )
        capa_action = eight_d.with_user(manager).action_create_capa()
        capa = self.env["pm.qms.capa"].browse(capa_action["res_id"])
        self.assertEqual(capa.source_type, "customer_issue")
        self.assertEqual(capa.eight_d_id, eight_d)
        self.assertEqual(complaint.capa_id, capa)

    def test_customer_quality_alert_workflow_and_closure_controls(self):
        manager = self._create_test_user("pmqms.cq.alert.manager", self.qms_manager_group)
        complaint = self.env["pm.qms.customer.complaint"].with_user(manager).create(self._complaint_values(name="Customer alert source"))
        alert_action = complaint.with_user(manager).action_create_quality_alert()
        alert = self.env["pm.qms.quality.alert"].browse(alert_action["res_id"])

        self.assertRegex(alert.code, r"^QA-\d{4}-\d{4}$")
        self.assertEqual(alert.complaint_id, complaint)
        alert.with_user(manager).action_publish()
        alert.with_user(manager).action_close()
        self.assertEqual(alert.state, "closed")

    def test_supplier_issue_scar_response_history_and_optional_capa(self):
        manager = self._create_test_user("pmqms.cq.supplier.manager", self.qms_manager_group)
        issue = self.env["pm.qms.supplier.issue"].with_user(manager).create(self._supplier_issue_values())

        self.assertRegex(issue.code, r"^SI-\d{4}-\d{4}$")
        ncr_action = issue.with_user(manager).action_create_ncr()
        ncr = self.env["pm.qms.nonconformity"].browse(ncr_action["res_id"])
        self.assertEqual(ncr.supplier_issue_id, issue)
        self.assertEqual(issue.with_user(manager).action_create_ncr()["res_id"], ncr.id)

        scar_action = issue.with_user(manager).action_create_scar()
        scar = self.env["pm.qms.scar"].browse(scar_action["res_id"])
        self.assertRegex(scar.code, r"^SCAR-\d{4}-\d{4}$")
        self.assertEqual(scar.supplier_issue_id, issue)
        self.assertFalse(scar.capa_id, "SCAR creation must not auto-create CAPA records.")
        self.assertEqual(issue.with_user(manager).action_create_scar()["res_id"], scar.id)

        scar.with_user(manager).action_issue()
        scar.with_user(manager).write(
            {
                "supplier_containment": "Supplier segregated affected material.",
                "supplier_root_cause": "Certificate review step was bypassed.",
                "supplier_corrective_action": "Supplier added release verification before shipment.",
            }
        )
        scar.with_user(manager).action_record_response()
        self.assertEqual(len(scar.response_line_ids), 1)
        scar.with_user(manager).write({"internal_review_notes": "Response needs stronger prevention evidence."})
        scar.with_user(manager).action_return_for_revision()
        scar.with_user(manager).write({"supplier_corrective_action": "Supplier added release verification and monthly layered review."})
        scar.with_user(manager).action_record_response()
        self.assertEqual(scar.response_line_ids.mapped("revision"), [1, 2])
        scar.with_user(manager).write({"internal_review_notes": "Revised response is acceptable."})
        scar.with_user(manager).action_accept_response()
        scar.with_user(manager).action_start_effectiveness()
        scar.with_user(manager).write({"effectiveness_notes": "No repeat discrepancy in the verification sample."})
        scar.with_user(manager).action_mark_effective()
        scar.with_user(manager).action_close()
        self.assertEqual(scar.state, "closed")
        self.assertEqual(issue.state, "verification")

        capa_action = scar.with_user(manager).action_create_capa()
        capa = self.env["pm.qms.capa"].browse(capa_action["res_id"])
        self.assertEqual(capa.source_type, "supplier_issue")
        self.assertEqual(capa.scar_id, scar)
        self.assertEqual(issue.capa_id, capa)

    def test_dashboard_and_management_review_include_customer_supplier_quality(self):
        manager = self._create_test_user("pmqms.cq.dashboard.manager", self.qms_manager_group)
        self.env["pm.qms.customer.complaint"].with_user(manager).create(self._complaint_values(name="Open complaint for dashboard"))
        issue = self.env["pm.qms.supplier.issue"].with_user(manager).create(self._supplier_issue_values(name="Open supplier issue for dashboard"))
        issue.with_user(manager).action_create_scar()

        dashboard = self.env["pm.qms.dashboard"].with_user(manager).create({})
        dashboard._compute_dashboard()
        self.assertGreaterEqual(dashboard.open_customer_complaints, 1)
        self.assertGreaterEqual(dashboard.overdue_customer_responses, 1)
        self.assertGreaterEqual(dashboard.open_supplier_issues, 1)
        self.assertGreaterEqual(dashboard.open_scar, 1)

        review = self.env["pm.qms.management.review"].with_user(manager).create(
            {
                "name": "Customer Supplier Quality Review",
                "organization_id": self.organization.id,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "planned_date": "2026-04-15",
                "chair_id": manager.id,
                "participant_ids": [(6, 0, [manager.id])],
                "objective": "Review customer and supplier quality signals.",
            }
        )
        review.with_user(manager).action_generate_snapshot()
        input_names = review.input_ids.mapped("title")
        self.assertIn("Customer quality and 8D status", input_names)
        self.assertIn("Supplier quality and SCAR status", input_names)

    def test_company_isolation_and_alignment_rules(self):
        qms_user = self._create_test_user("pmqms.cq.user", self.qms_user_group)
        other_user = self._create_test_user("pmqms.cq.other", self.qms_user_group, self.other_company)
        complaint = self.env["pm.qms.customer.complaint"].with_user(qms_user).create(self._complaint_values(name="Company isolated complaint"))

        with self.assertRaises(AccessError):
            complaint.with_user(qms_user).write({"state": "closed"})
        self.assertFalse(self.env["pm.qms.customer.complaint"].with_user(other_user).search([("id", "=", complaint.id)]))

        other_customer = self.env["res.partner"].create({"name": "Other Company Customer", "company_id": self.other_company.id})
        with self.assertRaises(ValidationError):
            self.env["pm.qms.customer.complaint"].create(
                self._complaint_values(name="Misaligned customer", customer_id=other_customer.id)
            )

        with self.assertRaises(ValidationError):
            self.env["pm.qms.supplier.issue"].create(
                self._supplier_issue_values(name="Misaligned process", process_id=self.other_process.id)
            )

    def test_workflow_actions_guard_required_closure_data(self):
        manager = self._create_test_user("pmqms.cq.guards.manager", self.qms_manager_group)
        complaint = self.env["pm.qms.customer.complaint"].with_user(manager).create(
            self._complaint_values(name="Complaint closure guard", containment_action=False)
        )

        complaint.with_user(manager).action_start_containment()
        with self.assertRaises(UserError):
            complaint.with_user(manager).action_complete_containment()
        complaint.with_user(manager).write({"containment_action": "Contain the affected sample."})
        complaint.with_user(manager).action_complete_containment()
        with self.assertRaises(UserError):
            complaint.with_user(manager).action_close()
        complaint.with_user(manager).write({"closure_notes": "Customer accepted the corrected response."})
        complaint.with_user(manager).action_close()
        self.assertEqual(complaint.state, "closed")
