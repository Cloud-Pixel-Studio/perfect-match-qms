import base64
import csv
from io import StringIO

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsMigration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Migration Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.manager = cls._create_user("migration_manager", cls.qms_manager_group)
        cls.user = cls._create_user("migration_user", cls.qms_user_group)
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Migration Test Organization", "code": "MIG-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Migration Test Process",
                "code": "MIG-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", "PM-QMS-QUALITY"),
                ("version", "=", "1.0"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.project = cls._generate_project()
        cls.line = cls.project.implementation_control_ids[:1]
        cls.requirement = cls.line.control_id.evidence_requirement_ids.filtered("active")[:1]

    @classmethod
    def _create_user(cls, login, group):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, group.id])],
            }
        )

    @classmethod
    def _generate_project(cls):
        project = cls.env["pm.qms.implementation.project"].with_user(cls.manager).generate_from_wizard(
            {
                "name": "Migration Pack Validation",
                "company_id": cls.company.id,
                "organization_id": cls.organization.id,
                "project_manager_id": cls.manager.id,
                "date_start": fields.Date.to_date("2026-08-15"),
                "target_date": fields.Date.to_date("2026-11-30"),
                "implementation_type": "migration",
                "pack_ids": cls.pack.ids,
                "create_odoo_project": True,
                "notes": "PILOT VALIDATION DATA - fictional migration test.",
            }
        )
        return project

    def _payload(self, header, rows):
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        writer.writerows(rows)
        return base64.b64encode(buffer.getvalue().encode()).decode()

    def _document_payload(self, rows):
        return self._payload(
            [
                "document_code",
                "title",
                "revision",
                "effective_date",
                "owner_login",
                "process_code",
                "document_type",
                "status",
                "attachment_filename",
                "attachment_base64",
                "migration_note",
                "control_instance_code",
            ],
            rows,
        )

    def _evidence_payload(self, rows):
        return self._payload(
            [
                "evidence_name",
                "control_instance_code",
                "evidence_requirement_name",
                "evidence_type",
                "evidence_date",
                "state",
                "document_code",
                "attachment_filename",
                "attachment_base64",
                "migration_note",
            ],
            rows,
        )

    def test_document_import_preserves_current_revision_and_validates_scope(self):
        attachment = base64.b64encode(b"pilot validation document").decode()
        payload = self._document_payload(
            [
                [
                    "PILOT-DOC-001",
                    "PILOT VALIDATION - Controlled Document",
                    "A",
                    "2026-08-15",
                    self.manager.login,
                    self.process.code,
                    "procedure",
                    "active",
                    "pilot-document.txt",
                    attachment,
                    "PILOT VALIDATION DATA - not production approval.",
                    self.line.control_instance_id.code,
                ]
            ]
        )
        wizard = self.env["pm.qms.document.import.wizard"].with_user(self.manager).create(
            {
                "company_id": self.company.id,
                "organization_id": self.organization.id,
                "csv_file": payload,
                "filename": "documents.csv",
            }
        )
        wizard.action_import()
        document = self.env["pm.qms.document"].search([("code", "=", "PILOT-DOC-001")])
        self.assertEqual(document.state, "active")
        self.assertEqual(document.current_revision, "A")
        self.assertEqual(document.current_revision_id.attachment_id.name, "pilot-document.txt")
        self.assertIn(self.line.control_instance_id, document.related_control_instance_ids)
        self.assertIn("PILOT VALIDATION DATA", document.current_revision_id.change_summary)

        other_org = self.env["pm.qms.organization"].create(
            {"name": "Other Migration Org", "code": "MIG-OTHER", "company_id": self.company.id}
        )
        bad_payload = self._document_payload(
            [["PILOT-DOC-002", "Bad Organization", "1", "", "", self.process.code, "procedure", "draft", "", "", "", ""]]
        )
        wizard = self.env["pm.qms.document.import.wizard"].with_user(self.manager).create(
            {
                "company_id": self.company.id,
                "organization_id": other_org.id,
                "csv_file": bad_payload,
                "filename": "bad.csv",
            }
        )
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_evidence_import_requires_review_and_rejects_accepted_state(self):
        document = self.env["pm.qms.document"].with_user(self.manager).create(
            {
                "name": "PILOT VALIDATION - Evidence Source",
                "code": "PILOT-DOC-003",
                "organization_id": self.organization.id,
                "process_id": self.process.id,
                "document_type": "form",
                "related_control_instance_ids": [Command.link(self.line.control_instance_id.id)],
            }
        )
        attachment = base64.b64encode(b"pilot validation evidence").decode()
        payload = self._evidence_payload(
            [
                [
                    "PILOT VALIDATION - Imported Evidence",
                    self.line.control_instance_id.code,
                    self.requirement.name,
                    self.requirement.evidence_type,
                    "2026-08-15",
                    "under_review",
                    document.code,
                    "pilot-evidence.txt",
                    attachment,
                    "PILOT VALIDATION DATA - requires review.",
                ]
            ]
        )
        wizard = self.env["pm.qms.evidence.import.wizard"].with_user(self.manager).create(
            {
                "company_id": self.company.id,
                "organization_id": self.organization.id,
                "csv_file": payload,
                "filename": "evidence.csv",
            }
        )
        wizard.action_import()
        evidence = self.env["pm.qms.evidence"].search([("name", "=", "PILOT VALIDATION - Imported Evidence")])
        self.assertEqual(evidence.state, "under_review")
        self.assertEqual(evidence.attachment_ids.name, "pilot-evidence.txt")
        self.assertIn(document, evidence.document_ids)
        self.assertEqual(evidence.organization_id, self.organization)

        accepted_payload = self._evidence_payload(
            [
                [
                    "Bad Accepted Evidence",
                    self.line.control_instance_id.code,
                    self.requirement.name,
                    self.requirement.evidence_type,
                    "2026-08-15",
                    "accepted",
                    "",
                    "",
                    "",
                    "",
                ]
            ]
        )
        wizard = self.env["pm.qms.evidence.import.wizard"].with_user(self.manager).create(
            {
                "company_id": self.company.id,
                "organization_id": self.organization.id,
                "csv_file": accepted_payload,
                "filename": "bad-evidence.csv",
            }
        )
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_user_cannot_import_migration_files(self):
        payload = self._document_payload(
            [["PILOT-DOC-004", "Unauthorized", "1", "", "", self.process.code, "procedure", "draft", "", "", "", ""]]
        )
        with self.assertRaises(AccessError):
            self.env["pm.qms.document.import.wizard"].with_user(self.user).create(
                {
                    "company_id": self.company.id,
                    "organization_id": self.organization.id,
                    "csv_file": payload,
                    "filename": "unauthorized.csv",
                }
            )
