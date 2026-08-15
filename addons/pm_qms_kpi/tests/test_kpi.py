from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsKpi(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Performance Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")

        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Performance Organization", "code": "PM-PERF-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Performance Process",
                "code": "PM-PERF-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Performance Control",
                "code": "PM-QMS-PERF-TST",
                "objective": "Define internal Perfect Match performance tracking.",
                "process_id": cls.process.id,
                "category": "performance",
            }
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Performance implementation",
                "code": "PERF-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.customer = cls.env["res.partner"].create({"name": "Performance Customer", "company_id": cls.company.id})
        cls.supplier = cls.env["res.partner"].create({"name": "Performance Supplier", "company_id": cls.company.id})

        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Performance Organization", "code": "PM-PERF-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Performance Process",
                "code": "PM-PERF-PROC2",
                "organization_id": cls.other_organization.id,
                "company_id": cls.other_company.id,
            }
        )
        cls.other_control = cls.env["pm.qms.control"].create(
            {
                "name": "Other Performance Control",
                "code": "PM-QMS-PERF-OTHER",
                "objective": "Other company performance control.",
                "process_id": cls.other_process.id,
                "category": "performance",
            }
        )
        cls.other_control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Other performance implementation",
                "code": "OTHER-PERF-PM-QMS-001",
                "control_id": cls.other_control.id,
                "organization_id": cls.other_organization.id,
                "process_id": cls.other_process.id,
            }
        )
        cls.other_customer = cls.env["res.partner"].create(
            {"name": "Other Performance Customer", "company_id": cls.other_company.id}
        )
        cls.other_supplier = cls.env["res.partner"].create(
            {"name": "Other Performance Supplier", "company_id": cls.other_company.id}
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

    def _objective_values(self, **extra_values):
        values = {
            "name": "Improve delivery performance",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "date_start": "2026-01-01",
            "target_date": "2026-12-31",
            "baseline_value": 93.5,
            "baseline_date": "2026-01-31",
            "target_value": 95.0,
            "target_operator": "ge",
            "unit_of_measure": "%",
            "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
        }
        values.update(extra_values)
        return values

    def _kpi_values(self, **extra_values):
        values = {
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
        values.update(extra_values)
        return values

    def _measurement_values(self, kpi, period_start, period_end, value, **extra_values):
        values = {
            "kpi_id": kpi.id,
            "measurement_date": period_end,
            "period_start": period_start,
            "period_end": period_end,
            "value": value,
        }
        values.update(extra_values)
        return values

    def test_objective_workflow_relationships_and_history(self):
        manager = self._create_test_user("pmqms.performance.objective", self.qms_manager_group)
        objective = self.env["pm.qms.objective"].with_user(manager).create(
            self._objective_values(owner_id=manager.id)
        )
        self.assertRegex(objective.code, r"^PM-OBJ-\d{5}$")
        self.assertEqual(objective.status, "draft")
        objective.with_user(manager).action_activate()
        objective.with_user(manager).action_mark_achieved()
        objective.with_user(manager).action_close()
        self.assertEqual(objective.status, "closed")
        self.assertIn(objective, self.control_instance.objective_ids)
        self.assertEqual(self.process.objective_count, 1)
        events = self.env["pm.qms.event"].search([("res_model", "=", "pm.qms.objective"), ("res_id", "=", objective.id)])
        self.assertGreaterEqual(len(events), 3)

        with self.assertRaises(AccessError):
            objective.with_user(manager).write({"status": "active"})
        with self.assertRaises(UserError):
            objective.with_user(manager).unlink()

    def test_kpi_measurement_snapshots_status_schedule_and_trend(self):
        manager = self._create_test_user("pmqms.performance.kpi", self.qms_manager_group)
        objective = self.env["pm.qms.objective"].with_user(manager).create(
            self._objective_values(owner_id=manager.id, auto_evaluation=True)
        )
        kpi = self.env["pm.qms.kpi"].with_user(manager).create(
            self._kpi_values(owner_id=manager.id, objective_ids=[(6, 0, [objective.id])])
        )
        kpi.with_user(manager).action_activate()
        jan = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-01-01", "2026-01-31", 92.0)
        )
        self.assertEqual(jan.status, "warning")
        self.assertEqual(jan.target_value_snapshot, 95.0)
        self.assertEqual(kpi.next_measurement_date.strftime("%Y-%m-%d"), "2026-02-28")

        feb = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-02-01", "2026-02-28", 96.0)
        )
        self.assertEqual(feb.status, "on_target")
        self.assertEqual(kpi.latest_value, 96.0)
        self.assertEqual(kpi.latest_status, "on_target")
        self.assertEqual(kpi.previous_value, 92.0)
        self.assertEqual(kpi.trend_direction, "improving")

        kpi.with_user(manager).write({"target_value": 97.0, "warning_value": 94.0})
        self.assertEqual(jan.target_value_snapshot, 95.0)
        self.assertEqual(feb.target_value_snapshot, 95.0)
        mar = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-03-01", "2026-03-31", 96.0)
        )
        self.assertEqual(mar.target_value_snapshot, 97.0)
        self.assertEqual(mar.status, "warning")
        self.assertEqual(kpi.latest_status, "warning")
        self.assertEqual(kpi.trend_direction, "declining")
        self.assertIn(kpi, objective.kpi_ids)
        self.assertIn(kpi, self.control_instance.kpi_ids)

        objective.with_user(manager).action_activate()
        objective.with_user(manager).action_evaluate_from_kpis()
        self.assertEqual(objective.status, "active")

    def test_kpi_lower_is_better_warning_off_target_and_validation(self):
        manager = self._create_test_user("pmqms.performance.lower", self.qms_manager_group)
        kpi = self.env["pm.qms.kpi"].with_user(manager).create(
            self._kpi_values(
                name="Customer Rejection Rate",
                direction="lower_is_better",
                target_value=3.0,
                warning_value=5.0,
                unit_of_measure="%",
            )
        )
        on_target = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-01-01", "2026-01-31", 2.5)
        )
        warning = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-02-01", "2026-02-28", 4.5)
        )
        off_target = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-03-01", "2026-03-31", 6.0)
        )
        self.assertEqual(on_target.status, "on_target")
        self.assertEqual(warning.status, "warning")
        self.assertEqual(off_target.status, "off_target")

        with self.assertRaises(ValidationError):
            self.env["pm.qms.kpi.measurement"].with_user(manager).create(
                self._measurement_values(kpi, "2026-04-30", "2026-04-01", 2.0)
            )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.kpi.measurement"].with_user(manager).create(
                self._measurement_values(kpi, "2026-03-01", "2026-03-31", 7.0)
            )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.kpi"].with_user(manager).create(
                self._kpi_values(name="Invalid lower KPI", direction="lower_is_better", target_value=3, warning_value=2)
            )

    def test_kpi_overdue_logic_and_user_measurement_entry(self):
        manager = self._create_test_user("pmqms.performance.overdue.manager", self.qms_manager_group)
        qms_user = self._create_test_user("pmqms.performance.measure.user", self.qms_user_group)
        kpi = self.env["pm.qms.kpi"].with_user(manager).create(self._kpi_values(start_date="2026-01-01"))
        kpi.with_user(manager).action_activate()
        self.assertTrue(kpi.measurement_overdue)
        self.assertGreater(kpi.days_overdue, 0)

        measurement = self.env["pm.qms.kpi.measurement"].with_user(qms_user).create(
            self._measurement_values(kpi, "2026-01-01", "2026-01-31", 96.0)
        )
        self.assertEqual(measurement.recorded_by_id, qms_user)
        with self.assertRaises(AccessError):
            measurement.with_user(qms_user).action_verify()
        measurement.with_user(manager).action_verify()
        self.assertEqual(measurement.verified_by_id, manager)

    def test_customer_performance_satisfaction_and_ncr_metrics(self):
        manager = self._create_test_user("pmqms.performance.customer", self.qms_manager_group)
        ncr = self.env["pm.qms.nonconformity"].with_user(manager).create(
            {
                "name": "Customer rejection",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "source_type": "customer",
                "description": "Customer-related NCR for performance metrics.",
                "detected_date": "2026-03-15",
            }
        )
        ncr.with_user(manager).action_open()
        performance = self.env["pm.qms.customer.performance"].with_user(manager).create(
            {
                "customer_id": self.customer.id,
                "organization_id": self.organization.id,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "customer_satisfaction_score": 88.0,
                "manual_complaint_count": 1,
                "return_count": 2,
                "rejection_count": 1,
                "delivery_performance": 96.0,
                "survey_response_count": 10,
            }
        )
        self.assertEqual(performance.ncr_count, 1)
        self.assertEqual(performance.open_complaint_count, 1)
        self.assertEqual(performance.complaint_count, 2)

        satisfaction = self.env["pm.qms.customer.satisfaction"].with_user(manager).create(
            {
                "customer_id": self.customer.id,
                "organization_id": self.organization.id,
                "measurement_date": "2026-03-31",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "measurement_method": "survey",
                "score": 44.0,
                "score_scale_max": 50.0,
                "response_count": 10,
                "owner_id": manager.id,
            }
        )
        self.assertEqual(satisfaction.score_percent, 88.0)
        self.assertIn(satisfaction, self.customer.qms_customer_satisfaction_ids)
        with self.assertRaises(ValidationError):
            self.env["pm.qms.customer.satisfaction"].with_user(manager).create(
                {
                    "customer_id": self.customer.id,
                    "organization_id": self.organization.id,
                    "measurement_date": "2026-04-30",
                    "period_start": "2026-04-01",
                    "period_end": "2026-04-30",
                    "measurement_method": "survey",
                    "score": 60.0,
                    "score_scale_max": 50.0,
                }
            )

    def test_supplier_performance_evaluation_scoring_and_ncr_metrics(self):
        manager = self._create_test_user("pmqms.performance.supplier", self.qms_manager_group)
        self.env["pm.qms.nonconformity"].with_user(manager).create(
            {
                "name": "Supplier rejection",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "source_type": "supplier",
                "description": "Supplier-related NCR for performance metrics.",
                "detected_date": "2026-03-15",
            }
        )
        performance = self.env["pm.qms.supplier.performance"].with_user(manager).create(
            {
                "supplier_id": self.supplier.id,
                "organization_id": self.organization.id,
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "quality_score": 90.0,
                "delivery_score": 80.0,
                "received_quantity": 100.0,
                "rejected_quantity": 5.0,
                "late_delivery_count": 2,
                "total_delivery_count": 20,
            }
        )
        self.assertEqual(performance.overall_score, 85.0)
        self.assertEqual(performance.supplier_ncr_count, 1)

        evaluation = self.env["pm.qms.supplier.evaluation"].with_user(manager).create(
            {
                "supplier_id": self.supplier.id,
                "organization_id": self.organization.id,
                "evaluation_date": "2026-03-31",
                "period_start": "2026-01-01",
                "period_end": "2026-03-31",
                "quality_score": 90.0,
                "delivery_score": 80.0,
                "service_score": 100.0,
                "compliance_score": 0.0,
                "status": "conditional",
            }
        )
        self.assertEqual(evaluation.overall_score, 88.0)
        evaluation.with_user(manager).action_complete()
        self.assertEqual(evaluation.state, "completed")
        events = self.env["pm.qms.event"].search(
            [("res_model", "=", "pm.qms.supplier.evaluation"), ("res_id", "=", evaluation.id)]
        )
        self.assertTrue(events)

        with self.assertRaises(ValidationError):
            self.env["pm.qms.supplier.evaluation"].with_user(manager).create(
                {
                    "supplier_id": self.supplier.id,
                    "organization_id": self.organization.id,
                    "evaluation_date": "2026-04-30",
                    "period_start": "2026-04-01",
                    "period_end": "2026-04-30",
                    "quality_score": 90.0,
                    "delivery_score": 80.0,
                    "service_score": 100.0,
                    "quality_weight": 0.0,
                    "delivery_weight": 0.0,
                    "service_weight": 0.0,
                    "compliance_weight": 0.0,
                }
            )

    def test_multicompany_isolation_and_indirect_relationship_constraints(self):
        manager = self._create_test_user("pmqms.performance.security.manager", self.qms_manager_group)
        other_user = self._create_test_user("pmqms.performance.security.other", self.qms_user_group, self.other_company)
        objective = self.env["pm.qms.objective"].with_user(manager).create(self._objective_values(owner_id=manager.id))
        kpi = self.env["pm.qms.kpi"].with_user(manager).create(self._kpi_values(owner_id=manager.id))
        measurement = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-01-01", "2026-01-31", 96.0)
        )
        customer_performance = self.env["pm.qms.customer.performance"].with_user(manager).create(
            {
                "customer_id": self.customer.id,
                "organization_id": self.organization.id,
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            }
        )
        satisfaction = self.env["pm.qms.customer.satisfaction"].with_user(manager).create(
            {
                "customer_id": self.customer.id,
                "organization_id": self.organization.id,
                "measurement_date": "2026-01-31",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
                "measurement_method": "scorecard",
                "score": 90.0,
                "score_scale_max": 100.0,
            }
        )
        supplier_performance = self.env["pm.qms.supplier.performance"].with_user(manager).create(
            {
                "supplier_id": self.supplier.id,
                "organization_id": self.organization.id,
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            }
        )
        supplier_evaluation = self.env["pm.qms.supplier.evaluation"].with_user(manager).create(
            {
                "supplier_id": self.supplier.id,
                "organization_id": self.organization.id,
                "evaluation_date": "2026-01-31",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
                "quality_score": 90.0,
                "delivery_score": 90.0,
                "service_score": 90.0,
            }
        )

        self.assertFalse(self.env["pm.qms.objective"].with_user(other_user).search([("id", "=", objective.id)]))
        self.assertFalse(self.env["pm.qms.kpi"].with_user(other_user).search([("id", "=", kpi.id)]))
        self.assertFalse(self.env["pm.qms.kpi.measurement"].with_user(other_user).search([("id", "=", measurement.id)]))
        self.assertFalse(
            self.env["pm.qms.customer.performance"].with_user(other_user).search([("id", "=", customer_performance.id)])
        )
        self.assertFalse(
            self.env["pm.qms.customer.satisfaction"].with_user(other_user).search([("id", "=", satisfaction.id)])
        )
        self.assertFalse(
            self.env["pm.qms.supplier.performance"].with_user(other_user).search([("id", "=", supplier_performance.id)])
        )
        self.assertFalse(
            self.env["pm.qms.supplier.evaluation"].with_user(other_user).search([("id", "=", supplier_evaluation.id)])
        )

        try:
            self.env["pm.qms.objective"].with_user(manager).create(
                self._objective_values(
                    name="Invalid cross-company objective",
                    related_control_instance_ids=[(6, 0, [self.other_control_instance.id])],
                )
            )
        except (AccessError, ValidationError):
            pass
        else:
            self.fail("Cross-company control instance relationship should be blocked.")
        with self.assertRaises(ValidationError):
            self.env["pm.qms.customer.performance"].with_user(manager).create(
                {
                    "customer_id": self.other_customer.id,
                    "organization_id": self.organization.id,
                    "period_start": "2026-02-01",
                    "period_end": "2026-02-28",
                }
            )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.supplier.performance"].with_user(manager).create(
                {
                    "supplier_id": self.other_supplier.id,
                    "organization_id": self.organization.id,
                    "period_start": "2026-02-01",
                    "period_end": "2026-02-28",
                }
            )

    def test_cross_module_objective_kpi_off_target_to_risk_without_auto_ncr(self):
        manager = self._create_test_user("pmqms.performance.integration", self.qms_manager_group)
        initial_ncr_count = self.env["pm.qms.nonconformity"].search_count([])
        objective = self.env["pm.qms.objective"].with_user(manager).create(
            self._objective_values(owner_id=manager.id, auto_evaluation=True)
        )
        risk = self.env["pm.qms.risk"].with_user(manager).create(
            {
                "name": "Persistent delivery underperformance",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "risk_type": "risk",
                "category": "customer",
                "description": "Delivery performance may miss the internal objective.",
                "likelihood": 3,
                "impact": 3,
                "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
            }
        )
        objective.with_user(manager).write({"related_risk_ids": [(6, 0, [risk.id])]})
        kpi = self.env["pm.qms.kpi"].with_user(manager).create(
            self._kpi_values(owner_id=manager.id, objective_ids=[(6, 0, [objective.id])])
        )
        kpi.with_user(manager).action_activate()
        measurement = self.env["pm.qms.kpi.measurement"].with_user(manager).create(
            self._measurement_values(kpi, "2026-01-01", "2026-01-31", 82.0)
        )
        self.assertEqual(measurement.status, "off_target")
        objective.with_user(manager).action_activate()
        objective.with_user(manager).action_evaluate_from_kpis()
        self.assertEqual(objective.status, "not_achieved")
        self.assertIn(risk, objective.related_risk_ids)
        self.assertEqual(self.env["pm.qms.nonconformity"].search_count([]), initial_ncr_count)
