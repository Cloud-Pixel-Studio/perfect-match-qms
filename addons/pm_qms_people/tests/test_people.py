from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsPeople(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.other_company = cls.env["res.company"].create({"name": "People Other Company"})
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "People Test Organization", "code": "PM-PEOPLE-ORG", "company_id": cls.company.id}
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "People Other Organization", "code": "PM-PEOPLE-OTHER", "company_id": cls.other_company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "People Process",
                "code": "PM-PEOPLE-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.manager = cls._create_test_user("pm_people_manager", cls.qms_manager_group)
        cls.user = cls._create_test_user("pm_people_user", cls.qms_user_group)
        cls.other_user = cls._create_test_user("pm_people_other_user", cls.qms_user_group)

    @classmethod
    def _create_test_user(cls, login, group, company=None):
        company = company or cls.company
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": company.id,
                "company_ids": [Command.set([company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, group.id])],
            }
        )

    def _person(self, name="Person A", user=False, organization=False):
        return self.env["pm.qms.person"].create(
            {
                "name": name,
                "organization_id": (organization or self.organization).id,
                "user_id": user.id if user else False,
            }
        )

    def _role(self, code="PM-ROLE-001", name="Inspector"):
        return self.env["pm.qms.role"].create(
            {
                "name": name,
                "code": code,
                "company_id": self.company.id,
                "organization_id": self.organization.id,
            }
        )

    def _competency(self, code="PM-COMP-001", name="Inspection Method"):
        return self.env["pm.qms.competency"].create(
            {"name": name, "code": code, "category": "Demo", "company_id": self.company.id}
        )

    def test_person_identity_and_role_assignment(self):
        person_without_login = self._person("QMS Person Without Login")
        person_with_login = self._person("QMS Person With Login", user=self.user)
        role = self._role()
        assignment = self.env["pm.qms.person.role.assignment"].create(
            {"person_id": person_with_login.id, "role_id": role.id}
        )

        self.assertFalse(person_without_login.user_id)
        self.assertEqual(person_with_login.user_id, self.user)
        self.assertIn(role, person_with_login.active_role_ids)
        self.assertEqual(assignment.company_id, self.company)

    def test_company_alignment_is_enforced(self):
        other_role = self.env["pm.qms.role"].create(
            {"name": "Other Role", "code": "PM-OTHER-ROLE", "company_id": self.other_company.id}
        )
        person = self._person()

        with self.assertRaises(ValidationError):
            self.env["pm.qms.person.role.assignment"].create({"person_id": person.id, "role_id": other_role.id})

    def test_competency_matrix_derives_gaps_and_history(self):
        person = self._person(user=self.user)
        role = self._role()
        competency = self._competency()
        requirement = self.env["pm.qms.role.competency.requirement"].create(
            {"role_id": role.id, "competency_id": competency.id, "valid_months": 12}
        )
        self.env["pm.qms.person.role.assignment"].create({"person_id": person.id, "role_id": role.id})
        line = self.env["pm.qms.competency.matrix.line"].search(
            [("person_id", "=", person.id), ("requirement_id", "=", requirement.id)]
        )

        self.assertEqual(line.status, "not_assessed")

        old_date = fields.Date.context_today(self.env.user) - timedelta(days=400)
        valid_date = fields.Date.context_today(self.env.user) + timedelta(days=120)
        old_assessment = self.env["pm.qms.competency.assessment"].create(
            {
                "person_id": person.id,
                "competency_id": competency.id,
                "assessment_date": old_date,
                "result": "gap",
            }
        )
        new_assessment = self.env["pm.qms.competency.assessment"].create(
            {
                "person_id": person.id,
                "competency_id": competency.id,
                "assessment_date": fields.Date.context_today(self.env.user) - timedelta(days=20),
                "result": "competent",
                "valid_until": valid_date,
            }
        )
        line.invalidate_recordset()

        self.assertEqual(line.latest_assessment_id, new_assessment)
        self.assertEqual(line.status, "competent")
        self.assertTrue(old_assessment.exists())

        expired_date = fields.Date.context_today(self.env.user) - timedelta(days=1)
        self.env["pm.qms.competency.assessment"].create(
            {
                "person_id": person.id,
                "competency_id": competency.id,
                "assessment_date": fields.Date.context_today(self.env.user) - timedelta(days=10),
                "result": "competent",
                "valid_until": expired_date,
            }
        )
        line.invalidate_recordset()
        self.assertEqual(line.status, "expired")

    def test_role_removal_updates_matrix_without_deleting_assessments(self):
        person = self._person()
        role = self._role()
        competency = self._competency()
        self.env["pm.qms.role.competency.requirement"].create({"role_id": role.id, "competency_id": competency.id})
        assignment = self.env["pm.qms.person.role.assignment"].create({"person_id": person.id, "role_id": role.id})
        assessment = self.env["pm.qms.competency.assessment"].create(
            {"person_id": person.id, "competency_id": competency.id, "result": "competent"}
        )
        self.assertTrue(self.env["pm.qms.competency.matrix.line"].search([("person_id", "=", person.id)]))

        assignment.write({"active": False})

        self.assertFalse(self.env["pm.qms.competency.matrix.line"].search([("person_id", "=", person.id)]))
        self.assertTrue(assessment.exists())

    def test_training_history_and_overdue_detection(self):
        person = self._person()
        competency = self._competency()
        course = self.env["pm.qms.training.course"].create(
            {
                "name": "Inspection Training",
                "code": "PM-TRN-001",
                "company_id": self.company.id,
                "competency_ids": [Command.link(competency.id)],
                "validity_months": 12,
            }
        )
        completed = self.env["pm.qms.training.record"].create(
            {
                "person_id": person.id,
                "course_id": course.id,
                "completion_date": fields.Date.context_today(self.env.user),
                "result": "satisfactory",
            }
        )
        overdue = self.env["pm.qms.training.record"].create(
            {
                "person_id": person.id,
                "course_id": course.id,
                "due_date": fields.Date.context_today(self.env.user) - timedelta(days=1),
            }
        )

        self.assertEqual(completed.state, "completed")
        self.assertTrue(completed.valid_until)
        self.assertEqual(overdue.state, "overdue")
        self.assertNotEqual(completed.id, overdue.id)

    def test_qualification_status_and_idempotent_reminder(self):
        person = self._person()
        qualification_type = self.env["pm.qms.qualification.type"].create(
            {"name": "Auditor Qualification", "code": "PM-QUAL-001", "company_id": self.company.id, "expiring_soon_days": 30}
        )
        record = self.env["pm.qms.qualification.record"].create(
            {
                "person_id": person.id,
                "qualification_type_id": qualification_type.id,
                "issue_date": fields.Date.context_today(self.env.user) - timedelta(days=30),
                "expiration_date": fields.Date.context_today(self.env.user) + timedelta(days=5),
            }
        )

        self.assertEqual(record.status, "expiring")
        record._ensure_expiration_activities()
        record._ensure_expiration_activities()
        activities = self.env["mail.activity"].search(
            [("res_model", "=", record._name), ("res_id", "=", record.id), ("summary", "ilike", "Review qualification")]
        )
        self.assertEqual(len(activities), 1)

    def test_document_acknowledgment_is_revision_specific_and_idempotent(self):
        person = self._person(user=self.user)
        other_person = self._person("Other Linked Person", user=self.other_user)
        role = self._role()
        self.env["pm.qms.person.role.assignment"].create({"person_id": person.id, "role_id": role.id})
        self.env["pm.qms.person.role.assignment"].create({"person_id": other_person.id, "role_id": role.id})
        document = self.env["pm.qms.document"].create(
            {
                "name": "People Awareness Procedure",
                "code": "PM-DOC-PEOPLE-AWARE",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "document_type": "procedure",
            }
        )
        rev_a = self.env["pm.qms.document.revision"].create(
            {"document_id": document.id, "revision": "A", "state": "active", "effective_date": fields.Date.context_today(self.env.user)}
        )
        document.with_context(pm_qms_document_workflow=True).write({"state": "active", "current_revision_id": rev_a.id})
        requirement = self.env["pm.qms.role.document.requirement"].create(
            {"role_id": role.id, "document_id": document.id, "due_within_days": 7}
        )

        Ack = self.env["pm.qms.document.acknowledgment"]
        Ack.sync_for_document_requirements(requirement)
        Ack.sync_for_document_requirements(requirement)
        rev_a_ack = Ack.search([("person_id", "=", person.id), ("revision_id", "=", rev_a.id)])
        self.assertEqual(len(rev_a_ack), 1)

        rev_a_ack.with_user(self.user).action_acknowledge()
        self.assertEqual(rev_a_ack.state, "acknowledged")

        rev_b = self.env["pm.qms.document.revision"].create(
            {"document_id": document.id, "revision": "B", "state": "approved"}
        )
        rev_b.with_user(self.manager).action_activate()
        rev_b_ack = Ack.search([("person_id", "=", person.id), ("revision_id", "=", rev_b.id)])

        self.assertEqual(len(rev_b_ack), 1)
        self.assertEqual(rev_b_ack.state, "pending")
        self.assertEqual(rev_a_ack.state, "acknowledged")

        other_ack = Ack.search([("person_id", "=", other_person.id), ("revision_id", "=", rev_b.id)], limit=1)
        with self.assertRaises(AccessError):
            other_ack.with_user(self.user).action_acknowledge()

    def test_dashboard_people_metrics_are_real_counts(self):
        person = self._person()
        role = self._role()
        competency = self._competency()
        self.env["pm.qms.role.competency.requirement"].create({"role_id": role.id, "competency_id": competency.id})
        self.env["pm.qms.person.role.assignment"].create({"person_id": person.id, "role_id": role.id})
        dashboard = self.env["pm.qms.dashboard"].create({"organization_id": self.organization.id})

        self.assertGreaterEqual(dashboard.attention_competency_gaps, 1)
