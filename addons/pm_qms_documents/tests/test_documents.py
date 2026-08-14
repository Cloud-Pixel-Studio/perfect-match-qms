from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestPmQmsDocuments(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Document Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.organization = cls.env["pm.qms.organization"].create(
            {
                "name": "Document Organization",
                "code": "PM-DOC-ORG",
                "company_id": cls.company.id,
            }
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Document Management",
                "code": "PM-DOC-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Controlled Document Authorization",
                "code": "PM-QMS-DOC-001",
                "objective": "Establish an internal authorization method for managed documents.",
                "process_id": cls.process.id,
            }
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "Document control implementation",
                "code": "DOC-PM-QMS-DOC-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {
                "name": "Document Other Organization",
                "code": "PM-DOC-ORG2",
                "company_id": cls.other_company.id,
            }
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Document Management",
                "code": "PM-DOC-PROC2",
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

    @classmethod
    def _document_values(cls, **extra_values):
        values = {
            "name": "Quality Procedure",
            "code": "PM-DEMO-PROC-001",
            "organization_id": cls.organization.id,
            "process_id": cls.process.id,
            "document_type": "procedure",
            "related_control_ids": [(6, 0, [cls.control.id])],
            "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
        }
        values.update(extra_values)
        return values

    def test_document_and_revision_workflow(self):
        manager = self._create_test_user("pmqms.doc.manager", self.qms_manager_group)
        document = self.env["pm.qms.document"].with_user(manager).create(self._document_values())
        revision = self.env["pm.qms.document.revision"].with_user(manager).create(
            {
                "document_id": document.id,
                "revision": "01",
                "change_summary": "Initial controlled release.",
            }
        )

        revision.with_user(manager).action_submit_for_review()
        self.assertEqual(revision.state, "under_review")
        revision.with_user(manager).action_approve()
        self.assertEqual(revision.state, "approved")
        self.assertEqual(revision.approved_by, manager)
        revision.with_user(manager).action_activate()

        self.assertEqual(revision.state, "active")
        self.assertEqual(document.current_revision_id, revision)
        self.assertEqual(document.state, "active")
        events = self.env["pm.qms.event"].search(
            [("res_model", "=", "pm.qms.document.revision"), ("res_id", "=", revision.id)]
        )
        self.assertIn("active", events.mapped("new_state"))

    def test_revision_uniqueness_and_history_preservation(self):
        manager = self._create_test_user("pmqms.doc.manager2", self.qms_manager_group)
        document = self.env["pm.qms.document"].with_user(manager).create(
            self._document_values(code="PM-DEMO-PROC-002")
        )
        self.env["pm.qms.document.revision"].with_user(manager).create({"document_id": document.id, "revision": "01"})

        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["pm.qms.document.revision"].with_user(manager).create(
                    {"document_id": document.id, "revision": "01"}
                )

    def test_new_active_revision_supersedes_previous_revision(self):
        manager = self._create_test_user("pmqms.doc.manager3", self.qms_manager_group)
        document = self.env["pm.qms.document"].with_user(manager).create(
            self._document_values(code="PM-DEMO-PROC-003")
        )
        revision_01 = self.env["pm.qms.document.revision"].with_user(manager).create(
            {"document_id": document.id, "revision": "01"}
        )
        revision_01.with_user(manager).action_submit_for_review()
        revision_01.with_user(manager).action_approve()
        revision_01.with_user(manager).action_activate()

        revision_02 = self.env["pm.qms.document.revision"].with_user(manager).create(
            {"document_id": document.id, "revision": "02"}
        )
        revision_02.with_user(manager).action_submit_for_review()
        revision_02.with_user(manager).action_approve()
        revision_02.with_user(manager).action_activate()

        self.assertEqual(revision_01.state, "superseded")
        self.assertEqual(revision_02.state, "active")
        self.assertEqual(document.current_revision_id, revision_02)
        with self.assertRaises(UserError):
            revision_01.with_user(manager).unlink()

    def test_document_permission_enforcement(self):
        qms_user = self._create_test_user("pmqms.doc.user", self.qms_user_group)
        manager = self._create_test_user("pmqms.doc.manager4", self.qms_manager_group)
        document = self.env["pm.qms.document"].with_user(manager).create(
            self._document_values(code="PM-DEMO-PROC-004")
        )
        revision = self.env["pm.qms.document.revision"].with_user(manager).create(
            {"document_id": document.id, "revision": "01"}
        )

        document.with_user(qms_user).read(["name", "code"])
        with self.assertRaises(AccessError):
            revision.with_user(qms_user).action_approve()
        with self.assertRaises(AccessError):
            self.env["pm.qms.document"].with_user(qms_user).create(
                self._document_values(code="PM-DEMO-PROC-USER")
            )
        with self.assertRaises(AccessError):
            self.env["pm.qms.event"].with_user(qms_user).create(
                {
                    "name": "Manual event should fail",
                    "user_id": qms_user.id,
                    "res_model": "pm.qms.document",
                    "res_id": document.id,
                }
            )

    def test_document_multicompany_isolation(self):
        manager = self._create_test_user("pmqms.doc.manager5", self.qms_manager_group)
        other_user = self._create_test_user("pmqms.doc.other", self.qms_user_group, self.other_company)
        document = self.env["pm.qms.document"].with_user(manager).create(
            self._document_values(code="PM-DEMO-PROC-005")
        )
        revision = self.env["pm.qms.document.revision"].with_user(manager).create(
            {"document_id": document.id, "revision": "01"}
        )

        self.assertFalse(self.env["pm.qms.document"].with_user(other_user).search([("id", "=", document.id)]))
        self.assertFalse(
            self.env["pm.qms.document.revision"].with_user(other_user).search([("id", "=", revision.id)])
        )
