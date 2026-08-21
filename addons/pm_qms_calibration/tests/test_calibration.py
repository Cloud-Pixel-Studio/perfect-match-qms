from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsCalibration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Calibration Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.qms_admin_group = cls.env.ref("pm_qms_core.group_pm_qms_administrator")

        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Calibration Organization", "code": "PM-CAL-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Calibration Process",
                "code": "PM-CAL-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Calibration Control",
                "code": "PM-QMS-CAL-001",
                "objective": "Control monitoring and measuring resources.",
                "process_id": cls.process.id,
            }
        )
        cls.requirement = cls.env["pm.qms.evidence.requirement"].create(
            {"name": "Calibration certificate", "control_id": cls.control.id, "evidence_type": "record"}
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Calibration control implementation",
                "code": "CAL-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.equipment_type = cls.env["pm.qms.equipment.type"].create(
            {"name": "Test Gage", "code": "PM-CAL-TYPE", "company_id": cls.company.id}
        )
        cls.provider = cls.env["pm.qms.calibration.provider"].create(
            {"name": "Calibration Provider", "code": "PM-CAL-PROV", "company_id": cls.company.id}
        )
        cls.person = cls.env["pm.qms.person"].create(
            {"name": "Calibration Owner", "code": "PM-CAL-PER-001", "organization_id": cls.organization.id}
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Calibration Other Org", "code": "PM-CAL-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_type = cls.env["pm.qms.equipment.type"].create(
            {"name": "Other Gage", "code": "PM-CAL-TYPE2", "company_id": cls.other_company.id}
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

    def _equipment_values(self, **extra_values):
        values = {
            "name": "Digital Caliper",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "type_id": self.equipment_type.id,
            "responsible_person_id": self.person.id,
            "calibration_strategy": "external",
            "default_provider_id": self.provider.id,
            "frequency_interval": 12,
            "frequency_unit": "months",
            "due_soon_days": 45,
            "acceptance_criteria": "Use the approved internal acceptance criteria for this resource.",
        }
        values.update(extra_values)
        return values

    def test_equipment_master_sequence_due_status_and_alignment(self):
        equipment = self.env["pm.qms.equipment"].create(self._equipment_values())
        self.assertRegex(equipment.code, r"^PM-EQ-\d{5}$")
        self.assertEqual(equipment.calibration_status, "no_history")

        with self.assertRaises(ValidationError):
            self.env["pm.qms.equipment"].create(self._equipment_values(code=equipment.code))

        with self.assertRaises(ValidationError):
            self.env["pm.qms.equipment"].create(self._equipment_values(type_id=self.other_type.id))

    def test_accepted_event_drives_schedule_and_return_to_service(self):
        manager = self._create_test_user("pmqms.cal.manager", self.qms_manager_group)
        equipment = self.env["pm.qms.equipment"].create(self._equipment_values(code="PM-CAL-GAGE-001"))
        event = self.env["pm.qms.calibration.event"].create(
            {
                "equipment_id": equipment.id,
                "calibration_date": "2026-08-01",
                "provider_id": self.provider.id,
                "result": "pass",
            }
        )

        event.with_user(manager).action_accept()

        self.assertEqual(event.state, "accepted")
        self.assertEqual(event.next_due_date.isoformat(), "2027-08-01")
        self.assertEqual(equipment.last_event_id, event)
        self.assertEqual(equipment.lifecycle_state, "in_service")

    def test_out_of_tolerance_creates_impact_assessment_and_quarantine(self):
        manager = self._create_test_user("pmqms.cal.manager2", self.qms_manager_group)
        equipment = self.env["pm.qms.equipment"].create(self._equipment_values(code="PM-CAL-GAGE-002"))
        self.env["pm.qms.calibration.event"].with_user(manager).create(
            {
                "equipment_id": equipment.id,
                "calibration_date": "2026-01-15",
                "next_due_date": "2027-01-15",
                "result": "pass",
            }
        ).action_accept()
        oot_event = self.env["pm.qms.calibration.event"].create(
            {
                "equipment_id": equipment.id,
                "calibration_date": "2026-08-15",
                "provider_id": self.provider.id,
                "result": "out_of_tolerance",
                "as_found_condition": "As-found result exceeded internal acceptance criteria.",
            }
        )

        oot_event.with_user(manager).action_accept()
        oot_event.with_user(manager).action_accept()

        self.assertEqual(equipment.lifecycle_state, "quarantined")
        self.assertEqual(len(equipment.impact_assessment_ids), 1)
        assessment = equipment.impact_assessment_ids
        self.assertEqual(assessment.event_id, oot_event)
        self.assertEqual(assessment.exposure_start.isoformat(), "2026-01-15")
        self.assertEqual(assessment.used_during_exposure, "unknown")
        with self.assertRaises(UserError):
            equipment.with_user(manager).action_return_to_service()

    def test_impact_assessment_ncr_capa_links_and_closure_controls(self):
        manager = self._create_test_user("pmqms.cal.manager3", self.qms_manager_group)
        equipment = self.env["pm.qms.equipment"].create(self._equipment_values(code="PM-CAL-GAGE-003"))
        event = self.env["pm.qms.calibration.event"].create(
            {
                "equipment_id": equipment.id,
                "calibration_date": "2026-08-15",
                "result": "fail",
                "as_found_condition": "Failed verification check.",
            }
        )
        event.with_user(manager).action_accept()
        assessment = event.impact_assessment_id.with_user(manager)
        assessment.write(
            {
                "used_during_exposure": "yes",
                "impact_conclusion": "potential_impact",
                "evaluation_summary": "Potentially affected records must be reviewed.",
                "containment_action": "Hold equipment and review recent checks.",
                "disposition": "Keep equipment quarantined until a passing verification is accepted.",
            }
        )

        assessment.action_start_review()
        assessment.action_set_disposition()
        action = assessment.action_create_ncr()
        ncr = self.env["pm.qms.nonconformity"].browse(action["res_id"])
        self.assertEqual(ncr.calibration_impact_assessment_id, assessment)
        self.assertEqual(ncr.equipment_id, equipment)

        capa_action = assessment.action_link_capa_from_ncr()
        capa = self.env["pm.qms.capa"].browse(capa_action["res_id"])
        self.assertEqual(capa.calibration_event_id, event)
        self.assertEqual(capa.equipment_id, equipment)

        assessment.action_close()
        self.assertEqual(assessment.state, "closed")

    def test_reminder_idempotency_dashboard_and_management_review_snapshot(self):
        manager = self._create_test_user("pmqms.cal.manager4", self.qms_manager_group)
        equipment = self.env["pm.qms.equipment"].create(self._equipment_values(code="PM-CAL-GAGE-004"))
        event = self.env["pm.qms.calibration.event"].create(
            {
                "equipment_id": equipment.id,
                "calibration_date": "2026-07-01",
                "next_due_date": "2026-08-01",
                "result": "pass",
            }
        )
        event.with_user(manager).action_accept()
        equipment.action_schedule_due_activities()
        equipment.action_schedule_due_activities()
        activities = self.env["mail.activity"].search(
            [("res_model", "=", "pm.qms.equipment"), ("res_id", "=", equipment.id), ("summary", "=", "Calibration due")]
        )
        self.assertEqual(len(activities), 1)

        dashboard = self.env["pm.qms.dashboard"].create({"organization_id": self.organization.id})
        self.assertGreaterEqual(dashboard.calibration_overdue, 1)

        review = self.env["pm.qms.management.review"].with_user(manager).create(
            {
                "name": "Calibration Management Review",
                "organization_id": self.organization.id,
                "period_start": "2026-07-01",
                "period_end": "2026-08-31",
                "planned_date": "2026-09-15",
                "actual_date": "2026-09-15",
                "chair_id": manager.id,
                "participant_ids": [(6, 0, [manager.id])],
                "objective": "Review calibration status.",
                "conclusion": "Calibration resources were reviewed.",
            }
        )
        review.action_generate_snapshot()
        calibration_input = review.input_ids.filtered(lambda item: item.source_identifier == "PM-QMS-CALIBRATION")
        self.assertEqual(len(calibration_input), 1)
        self.assertEqual(calibration_input.category, "resources")

    def test_readonly_user_cannot_accept_calibration_event(self):
        user = self._create_test_user("pmqms.cal.user", self.qms_user_group)
        equipment = self.env["pm.qms.equipment"].sudo().create(self._equipment_values(code="PM-CAL-GAGE-005"))
        event = self.env["pm.qms.calibration.event"].sudo().create(
            {"equipment_id": equipment.id, "calibration_date": "2026-08-01", "result": "pass"}
        )
        with self.assertRaises(AccessError):
            event.with_user(user).action_accept()
