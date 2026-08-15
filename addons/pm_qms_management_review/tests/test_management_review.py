from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsManagementReview(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Management Review Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.qms_admin_group = cls.env.ref("pm_qms_core.group_pm_qms_administrator")

        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Management Review Organization", "code": "PM-MR-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Management Review Process",
                "code": "PM-MR-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Management Review Control",
                "code": "PM-QMS-MR-001",
                "objective": "Review operational QMS information using Perfect Match methodology.",
                "process_id": cls.process.id,
                "category": "governance",
            }
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Management review implementation",
                "code": "MR-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.customer = cls.env["res.partner"].create({"name": "Management Review Customer", "company_id": cls.company.id})
        cls.supplier = cls.env["res.partner"].create({"name": "Management Review Supplier", "company_id": cls.company.id})

        cls.same_company_other_org = cls.env["pm.qms.organization"].create(
            {"name": "Same Company Other Org", "code": "PM-MR-ORG-SAME", "company_id": cls.company.id}
        )
        cls.same_company_other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Same Company Other Process",
                "code": "PM-MR-PROC-SAME",
                "organization_id": cls.same_company_other_org.id,
                "company_id": cls.company.id,
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Company MR Organization", "code": "PM-MR-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Company MR Process",
                "code": "PM-MR-PROC2",
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

    def _review_values(self, **extra_values):
        values = {
            "name": "Quarterly Management Review",
            "organization_id": self.organization.id,
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "planned_date": "2026-04-15",
            "actual_date": "2026-04-15",
            "chair_id": self.env.user.id,
            "participant_ids": [(6, 0, [self.env.user.id])],
            "objective": "Review selected operational QMS inputs.",
            "conclusion": "Management reviewed the captured inputs and retained action follow-up separately.",
        }
        values.update(extra_values)
        return values

    def _create_review(self, manager, **extra_values):
        values = self._review_values(chair_id=manager.id, participant_ids=[(6, 0, [manager.id])], **extra_values)
        return self.env["pm.qms.management.review"].with_user(manager).create(values)

    def _create_kpi_with_measurement(self, manager, period_start="2026-01-01", period_end="2026-03-31", value=94.0):
        kpi = self.env["pm.qms.kpi"].with_user(manager).create(
            {
                "name": "On-Time Delivery",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "unit_of_measure": "%",
                "direction": "higher_is_better",
                "target_value": 95.0,
                "warning_value": 90.0,
                "frequency": "monthly",
                "start_date": "2026-01-01",
                "control_instance_ids": [(6, 0, [self.control_instance.id])],
            }
        )
        kpi.with_user(manager).action_activate()
        measurement = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            {
                "kpi_id": kpi.id,
                "measurement_date": period_end,
                "period_start": period_start,
                "period_end": period_end,
                "value": value,
            }
        )
        return kpi, measurement

    def _create_objective(self, manager, **extra_values):
        values = {
            "name": "Improve delivery performance",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "owner_id": manager.id,
            "description": "Internal objective for delivery performance.",
            "date_start": "2026-01-01",
            "target_date": "2026-12-31",
            "target_value": 95.0,
            "target_operator": "ge",
            "unit_of_measure": "%",
            "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
        }
        values.update(extra_values)
        return self.env["pm.qms.objective"].with_user(manager).create(values)

    def _create_completed_audit_with_open_finding(self, manager):
        audit = self.env["pm.qms.audit"].with_user(manager).create(
            {
                "name": "Management Review Internal Audit",
                "organization_id": self.organization.id,
                "planned_start": "2026-03-15",
                "planned_end": "2026-03-16",
                "audit_type": "process",
                "objective": "Evaluate selected internal implementation records.",
                "scope_summary": "Selected operational records.",
                "lead_auditor_id": manager.id,
                "auditor_ids": [(6, 0, [manager.id])],
            }
        )
        scope = self.env["pm.qms.audit.scope"].with_user(manager).create(
            {
                "audit_id": audit.id,
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "control_instance_ids": [(6, 0, [self.control_instance.id])],
            }
        )
        criterion = self.env["pm.qms.audit.criterion"].with_user(manager).create(
            {
                "audit_id": audit.id,
                "name": "Internal implementation criterion",
                "criterion_type": "perfect_match_control",
                "control_id": self.control.id,
                "control_instance_id": self.control_instance.id,
                "reference": "PM-QMS-MR-001",
            }
        )
        audit.with_user(manager).action_plan()
        audit.with_user(manager).action_record_independence()
        audit.with_user(manager).action_mark_ready()
        audit.with_user(manager).action_start()
        audit.with_user(manager).write({"actual_start": "2026-03-15"})
        audit.with_user(manager).action_start_reporting()
        audit.with_user(manager).write(
            {"actual_end": "2026-03-16", "conclusion": "Audit completed with one open follow-up item."}
        )
        audit.with_user(manager).action_complete()
        finding = self.env["pm.qms.audit.finding"].with_user(manager).create(
            {
                "name": "Open audit finding",
                "title": "Open audit finding",
                "audit_id": audit.id,
                "classification": "observation",
                "description": "Open finding reviewed by management.",
                "objective_evidence": "Internal observation text.",
                "criterion_id": criterion.id,
                "process_id": self.process.id,
                "control_instance_id": self.control_instance.id,
                "due_date": "2026-04-30",
            }
        )
        finding.with_user(manager).action_issue()
        finding.with_user(manager).action_require_action()
        self.assertEqual(scope.audit_id, audit)
        return audit, finding

    def _create_capa_in_effectiveness_review(self, manager):
        capa = self.env["pm.qms.capa"].with_user(manager).create(
            {
                "name": "Management Review CAPA",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "source_type": "management_decision",
                "problem_statement": "Follow-up action requires effectiveness confirmation.",
                "root_cause": "The follow-up check was not previously assigned.",
                "target_date": "2026-03-31",
                "effectiveness_review_date": "2026-04-30",
                "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
            }
        )
        action = self.env["pm.qms.capa.action"].with_user(manager).create(
            {"capa_id": capa.id, "name": "Complete management review follow-up check"}
        )
        capa.with_user(manager).action_start_analysis()
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        action.with_user(manager).action_start()
        action.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()
        self.assertEqual(capa.state, "effectiveness_review")
        return capa

    def _prepare_review_with_snapshot(self, manager, **extra_values):
        review = self._create_review(manager, **extra_values)
        review.with_user(manager).action_prepare()
        review.with_user(manager).action_generate_snapshot()
        return review

    def test_review_workflow_completion_keeps_open_actions(self):
        manager = self._create_test_user("pmqms.mr.workflow", self.qms_manager_group)
        self._create_kpi_with_measurement(manager)
        review = self._prepare_review_with_snapshot(manager)
        decision = self.env["pm.qms.management.review.decision"].with_user(manager).create(
            {
                "review_id": review.id,
                "name": "Continue monitoring selected performance",
                "description": "Management will keep the selected performance rhythm active.",
                "decision_type": "continue",
                "owner_id": manager.id,
            }
        )
        action = self.env["pm.qms.management.review.action"].with_user(manager).create(
            {
                "review_id": review.id,
                "name": "Follow up on open review action",
                "owner_id": manager.id,
                "target_date": "2026-08-30",
            }
        )
        review.with_user(manager).action_mark_ready()
        review.with_user(manager).action_start_review()
        review.with_user(manager).action_complete()

        self.assertRegex(review.code, r"^PM-MR-\d{5}$")
        self.assertEqual(review.state, "completed")
        self.assertEqual(action.status, "open")
        self.assertEqual(review.open_action_count, 1)
        self.assertEqual(decision.review_id, review)
        with self.assertRaises(AccessError):
            review.with_user(manager).write({"state": "draft"})
        with self.assertRaises(AccessError):
            review.input_ids.with_user(manager).write({"notes": "normal correction"})
        events = self.env["pm.qms.event"].search([("res_model", "=", "pm.qms.management.review"), ("res_id", "=", review.id)])
        self.assertGreaterEqual(len(events), 4)

    def test_kpi_snapshot_is_historical_after_live_changes(self):
        manager = self._create_test_user("pmqms.mr.kpi", self.qms_manager_group)
        kpi, measurement = self._create_kpi_with_measurement(manager, value=94.0)
        review = self._prepare_review_with_snapshot(manager)
        kpi_input = review.input_ids.filtered(lambda item: item.category == "kpi")
        self.assertEqual(len(kpi_input), 1)
        self.assertEqual(kpi_input.numeric_value, 94.0)
        self.assertEqual(kpi_input.target_snapshot, 95.0)
        self.assertEqual(kpi_input.status_snapshot, measurement.status)

        kpi.with_user(manager).write({"target_value": 97.0, "warning_value": 94.0})
        self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            {
                "kpi_id": kpi.id,
                "measurement_date": "2026-04-30",
                "period_start": "2026-04-01",
                "period_end": "2026-04-30",
                "value": 98.0,
            }
        )
        self.assertEqual(kpi.target_value, 97.0)
        self.assertEqual(kpi.latest_value, 98.0)
        self.assertEqual(kpi_input.numeric_value, 94.0)
        self.assertEqual(kpi_input.target_snapshot, 95.0)

    def test_objective_audit_and_capa_snapshots_are_historical(self):
        manager = self._create_test_user("pmqms.mr.historical", self.qms_manager_group)
        objective = self._create_objective(manager)
        audit, finding = self._create_completed_audit_with_open_finding(manager)
        capa = self._create_capa_in_effectiveness_review(manager)
        review = self._prepare_review_with_snapshot(manager)

        objective_input = review.input_ids.filtered(lambda item: item.category == "objectives")
        finding_input = review.input_ids.filtered(lambda item: item.category == "audit_findings")
        capa_input = review.input_ids.filtered(lambda item: item.category == "capa")
        self.assertEqual(objective_input.target_snapshot, 95.0)
        self.assertEqual(finding_input.status_snapshot, "action_required")
        self.assertEqual(capa_input.status_snapshot, "effectiveness_review")
        self.assertEqual(audit.state, "completed")

        objective.with_user(manager).write({"target_value": 99.0})
        finding.with_user(manager).write({"closure_notes": "Finding closed after the review snapshot."})
        finding.with_user(manager).action_close()
        capa.with_user(manager).write({"effectiveness_notes": "Effective after management review."})
        capa.with_user(manager).action_mark_effective()
        capa.with_user(manager).action_close()

        self.assertEqual(objective_input.target_snapshot, 95.0)
        self.assertEqual(finding_input.status_snapshot, "action_required")
        self.assertEqual(capa_input.status_snapshot, "effectiveness_review")

    def test_customer_supplier_risk_ncr_inputs_are_generated(self):
        manager = self._create_test_user("pmqms.mr.inputs", self.qms_manager_group)
        self.env["pm.qms.customer.performance"].with_user(manager).create(
            {
                "customer_id": self.customer.id,
                "organization_id": self.organization.id,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "customer_satisfaction_score": 74.0,
                "manual_complaint_count": 2,
                "return_count": 1,
                "delivery_performance": 91.0,
            }
        )
        self.env["pm.qms.customer.satisfaction"].with_user(manager).create(
            {
                "customer_id": self.customer.id,
                "organization_id": self.organization.id,
                "measurement_date": "2026-03-31",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "measurement_method": "survey",
                "score": 74.0,
                "score_scale_max": 100.0,
            }
        )
        self.env["pm.qms.supplier.performance"].with_user(manager).create(
            {
                "supplier_id": self.supplier.id,
                "organization_id": self.organization.id,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "quality_score": 70.0,
                "delivery_score": 82.0,
                "received_quantity": 100.0,
                "rejected_quantity": 4.0,
            }
        )
        self.env["pm.qms.supplier.evaluation"].with_user(manager).create(
            {
                "supplier_id": self.supplier.id,
                "organization_id": self.organization.id,
                "evaluation_date": "2026-03-31",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "quality_score": 70.0,
                "delivery_score": 82.0,
                "service_score": 85.0,
                "status": "monitor",
            }
        )
        risk = self.env["pm.qms.risk"].with_user(manager).create(
            {
                "name": "High delivery risk",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "risk_type": "risk",
                "category": "customer",
                "description": "Delivery performance may miss the internal target.",
                "likelihood": 4,
                "impact": 4,
                "residual_likelihood": 4,
                "residual_impact": 4,
            }
        )
        opportunity = self.env["pm.qms.risk"].with_user(manager).create(
            {
                "name": "Improve supplier communication",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "risk_type": "opportunity",
                "description": "Supplier scorecards may support better planning.",
                "benefit": "Improved supplier follow-up.",
            }
        )
        ncr = self.env["pm.qms.nonconformity"].with_user(manager).create(
            {
                "name": "Customer issue reviewed by management",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "source_type": "customer",
                "description": "Customer issue for management review snapshot.",
                "detected_date": "2026-03-15",
                "severity": "major",
                "target_date": "2026-03-31",
            }
        )
        ncr.with_user(manager).action_open()
        review = self._prepare_review_with_snapshot(manager)
        categories = set(review.input_ids.mapped("category"))
        self.assertIn("customer_performance", categories)
        self.assertIn("customer_satisfaction", categories)
        self.assertIn("supplier_performance", categories)
        self.assertIn("supplier_evaluation", categories)
        self.assertIn("risks", categories)
        self.assertIn("opportunities", categories)
        self.assertIn("ncr", categories)
        self.assertEqual(risk.residual_level, "critical")
        self.assertTrue(review.input_ids.filtered(lambda item: item.source_identifier == risk.code))
        self.assertTrue(review.input_ids.filtered(lambda item: item.source_identifier == opportunity.code))
        self.assertTrue(review.input_ids.filtered(lambda item: item.source_identifier == ncr.code))

    def test_previous_management_review_actions_are_captured(self):
        manager = self._create_test_user("pmqms.mr.previous", self.qms_manager_group)
        review_a = self._create_review(
            manager,
            name="Previous Management Review",
            period_start="2026-01-01",
            period_end="2026-03-31",
            planned_date="2026-04-15",
            actual_date="2026-04-15",
        )
        self.env["pm.qms.management.review.input"].with_user(manager).create(
            {
                "review_id": review_a.id,
                "category": "other",
                "title": "Manual input for prior review",
                "source_type": "manual",
            }
        )
        self.env["pm.qms.management.review.decision"].with_user(manager).create(
            {
                "review_id": review_a.id,
                "name": "Prior decision",
                "description": "A prior management decision.",
                "decision_type": "other",
            }
        )
        action = self.env["pm.qms.management.review.action"].with_user(manager).create(
            {
                "review_id": review_a.id,
                "name": "Prior open action",
                "owner_id": manager.id,
                "target_date": "2026-04-30",
            }
        )
        review_a.with_user(manager).action_prepare()
        review_a.with_user(manager).action_mark_ready()
        review_a.with_user(manager).action_start_review()
        review_a.with_user(manager).action_complete()

        review_b = self._prepare_review_with_snapshot(
            manager,
            name="Current Management Review",
            period_start="2026-04-01",
            period_end="2026-06-30",
            planned_date="2026-07-15",
            actual_date="2026-07-15",
        )
        previous_inputs = review_b.input_ids.filtered(lambda item: item.category == "previous_actions")
        self.assertEqual(len(previous_inputs), 1)
        self.assertEqual(previous_inputs.source_identifier, action.code)
        self.assertIn(previous_inputs.status_snapshot, ("open", "overdue"))
        self.assertEqual(action.status, "open")

    def test_management_review_action_owner_workflow_overdue_and_permissions(self):
        manager = self._create_test_user("pmqms.mr.action.manager", self.qms_manager_group)
        qms_user = self._create_test_user("pmqms.mr.action.owner", self.qms_user_group)
        other_user = self._create_test_user("pmqms.mr.action.other", self.qms_user_group)
        review = self._create_review(manager)
        action = self.env["pm.qms.management.review.action"].with_user(manager).create(
            {
                "review_id": review.id,
                "name": "Owner follow-up",
                "owner_id": qms_user.id,
                "target_date": "2026-01-31",
                "priority": "high",
            }
        )
        self.assertRegex(action.code, r"^PM-MRA-\d{5}$")
        self.assertTrue(action.is_overdue)
        self.assertGreater(action.days_overdue, 0)

        with self.assertRaises(AccessError):
            action.with_user(other_user).action_start()
        action.with_user(qms_user).action_start()
        action.with_user(qms_user).action_complete()
        self.assertEqual(action.status, "completed")
        with self.assertRaises(AccessError):
            action.with_user(qms_user).action_verify()
        action.with_user(manager).action_verify()
        self.assertEqual(action.status, "verified")
        self.assertEqual(action.verified_by_id, manager)

    def test_multicompany_and_snapshot_generation_isolation(self):
        manager = self._create_test_user("pmqms.mr.security.manager", self.qms_manager_group)
        other_user = self._create_test_user("pmqms.mr.security.other", self.qms_user_group, self.other_company)
        self._create_kpi_with_measurement(manager, value=96.0)
        same_org_kpi = self.env["pm.qms.kpi"].with_user(manager).create(
            {
                "name": "Same Company Other Org KPI",
                "organization_id": self.same_company_other_org.id,
                "process_id": self.same_company_other_process.id,
                "unit_of_measure": "%",
                "target_value": 90.0,
                "warning_value": 85.0,
                "frequency": "monthly",
                "start_date": "2026-01-01",
            }
        )
        self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            {
                "kpi_id": same_org_kpi.id,
                "measurement_date": "2026-03-31",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "value": 99.0,
            }
        )
        other_company_manager = self._create_test_user(
            "pmqms.mr.security.other.manager", self.qms_manager_group, self.other_company
        )
        other_kpi = self.env["pm.qms.kpi"].with_user(other_company_manager).create(
            {
                "name": "Other Company KPI",
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
                "unit_of_measure": "%",
                "target_value": 90.0,
                "warning_value": 85.0,
                "frequency": "monthly",
                "start_date": "2026-01-01",
            }
        )
        self.env["pm.qms.kpi.measurement"].with_user(other_company_manager).create(
            {
                "kpi_id": other_kpi.id,
                "measurement_date": "2026-03-31",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "value": 99.0,
            }
        )
        review = self._prepare_review_with_snapshot(manager)
        kpi_inputs = review.input_ids.filtered(lambda item: item.category == "kpi")
        self.assertEqual(len(kpi_inputs), 1)
        self.assertNotIn("Other Org", kpi_inputs.title)
        self.assertNotIn("Other Company", kpi_inputs.title)

        decision = self.env["pm.qms.management.review.decision"].with_user(manager).create(
            {
                "review_id": review.id,
                "name": "Security decision",
                "description": "Security boundary decision.",
                "decision_type": "other",
            }
        )
        action = self.env["pm.qms.management.review.action"].with_user(manager).create(
            {"review_id": review.id, "name": "Security action", "owner_id": manager.id}
        )
        self.assertFalse(self.env["pm.qms.management.review"].with_user(other_user).search([("id", "=", review.id)]))
        self.assertFalse(
            self.env["pm.qms.management.review.input"].with_user(other_user).search([("review_id", "=", review.id)])
        )
        self.assertFalse(
            self.env["pm.qms.management.review.decision"].with_user(other_user).search([("id", "=", decision.id)])
        )
        self.assertFalse(
            self.env["pm.qms.management.review.action"].with_user(other_user).search([("id", "=", action.id)])
        )

    def test_validation_and_snapshot_locking_policy(self):
        manager = self._create_test_user("pmqms.mr.validation", self.qms_manager_group)
        admin = self._create_test_user("pmqms.mr.admin", self.qms_admin_group)
        with self.assertRaises(ValidationError):
            self._create_review(manager, period_start="2026-03-31", period_end="2026-01-01")
        self._create_kpi_with_measurement(manager)
        review = self._prepare_review_with_snapshot(manager)
        self.assertTrue(review.snapshot_date)
        review.with_user(manager).action_mark_ready()
        with self.assertRaises(UserError):
            review.with_user(manager).action_generate_snapshot()
        with self.assertRaises(AccessError):
            review.input_ids.with_user(manager).unlink()
        review.input_ids.with_user(admin).write({"notes": "Privileged correction note."})
        self.assertEqual(review.input_ids[:1].notes, "Privileged correction note.")
