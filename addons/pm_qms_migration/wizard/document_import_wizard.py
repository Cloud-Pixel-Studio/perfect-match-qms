import base64
import csv
from io import StringIO

from odoo import Command, fields, models
from odoo.exceptions import AccessError, UserError


class PmQmsDocumentImportWizard(models.TransientModel):
    _name = "pm.qms.document.import.wizard"
    _description = "Perfect Match QMS Document Import Wizard"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    organization_id = fields.Many2one("pm.qms.organization", required=True)
    csv_file = fields.Binary(required=True)
    filename = fields.Char()

    def _check_manager(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can import document metadata.")

    def _rows(self):
        self.ensure_one()
        try:
            text = base64.b64decode(self.csv_file).decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UserError("Document import CSV must be UTF-8 encoded.") from exc
        reader = csv.DictReader(StringIO(text))
        required = {
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
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise UserError(f"Document import CSV is missing required columns: {', '.join(sorted(missing))}")
        return list(reader)

    def _parse_date(self, value, row_number, label, required=False):
        value = (value or "").strip()
        if not value:
            if required:
                raise UserError(f"Row {row_number}: {label} is required.")
            return False
        try:
            return fields.Date.to_date(value)
        except ValueError as exc:
            raise UserError(f"Row {row_number}: {label} must use YYYY-MM-DD format.") from exc

    def _attachment_values(self, row, row_number, model_name):
        filename = (row.get("attachment_filename") or "").strip()
        payload = (row.get("attachment_base64") or "").strip()
        if any(separator in filename for separator in ("/", "\\")):
            raise UserError(f"Row {row_number}: attachment_filename must be a file name, not a path.")
        if payload and not filename:
            raise UserError(f"Row {row_number}: attachment_filename is required when attachment_base64 is supplied.")
        if not payload:
            return False
        try:
            base64.b64decode(payload, validate=True)
        except Exception as exc:
            raise UserError(f"Row {row_number}: attachment_base64 is not valid base64.") from exc
        return {
            "name": filename,
            "datas": payload,
            "res_model": model_name,
            "type": "binary",
        }

    def _resolve_rows(self):
        self.ensure_one()
        if self.organization_id.company_id != self.company_id:
            raise UserError("Selected organization must belong to the selected company.")
        allowed_types = dict(self.env["pm.qms.document"]._fields["document_type"].selection)
        allowed_statuses = {"draft", "under_review", "approved", "active", "obsolete"}
        seen_codes = set()
        resolved = []
        for row_number, row in enumerate(self._rows(), start=2):
            code = (row.get("document_code") or "").strip()
            title = (row.get("title") or "").strip()
            revision = (row.get("revision") or "").strip()
            process_code = (row.get("process_code") or "").strip()
            document_type = (row.get("document_type") or "procedure").strip()
            status = (row.get("status") or "draft").strip()
            if not code or not title or not revision:
                raise UserError(f"Row {row_number}: document_code, title, and revision are required.")
            if code in seen_codes:
                raise UserError(f"Row {row_number}: duplicate document_code in import file.")
            seen_codes.add(code)
            if document_type not in allowed_types:
                raise UserError(f"Row {row_number}: unsupported document_type '{document_type}'.")
            if status not in allowed_statuses:
                raise UserError(f"Row {row_number}: unsupported status '{status}'.")
            if self.env["pm.qms.document"].search_count([("code", "=", code), ("company_id", "=", self.company_id.id)]):
                raise UserError(f"Row {row_number}: document_code already exists for this company.")
            process = self.env["pm.qms.process"].search(
                [
                    ("code", "=", process_code),
                    ("company_id", "=", self.company_id.id),
                    ("organization_id", "=", self.organization_id.id),
                ],
                limit=1,
            )
            if not process:
                raise UserError(f"Row {row_number}: process_code was not found in the selected organization.")
            owner = False
            owner_login = (row.get("owner_login") or "").strip()
            if owner_login:
                owner = self.env["res.users"].search(
                    [
                        ("login", "=", owner_login),
                        ("company_ids", "in", [self.company_id.id]),
                    ],
                    limit=1,
                )
                if not owner:
                    raise UserError(f"Row {row_number}: owner_login was not found for the selected company.")
            instance = False
            instance_code = (row.get("control_instance_code") or "").strip()
            if instance_code:
                instance = self.env["pm.qms.control.instance"].search(
                    [
                        ("code", "=", instance_code),
                        ("company_id", "=", self.company_id.id),
                        ("organization_id", "=", self.organization_id.id),
                    ],
                    limit=1,
                )
                if not instance:
                    raise UserError(f"Row {row_number}: control_instance_code was not found in the selected organization.")
            resolved.append(
                {
                    "code": code,
                    "title": title,
                    "revision": revision,
                    "effective_date": self._parse_date(row.get("effective_date"), row_number, "effective_date"),
                    "owner": owner,
                    "process": process,
                    "document_type": document_type,
                    "status": status,
                    "migration_note": (row.get("migration_note") or "").strip(),
                    "attachment": self._attachment_values(row, row_number, "pm.qms.document.revision"),
                    "attachment_filename": (row.get("attachment_filename") or "").strip(),
                    "instance": instance,
                }
            )
        return resolved

    def action_import(self):
        self._check_manager()
        Document = self.env["pm.qms.document"]
        Revision = self.env["pm.qms.document.revision"]
        Attachment = self.env["ir.attachment"]
        created = Document
        for item in self._resolve_rows():
            document = Document.create(
                {
                    "name": item["title"],
                    "code": item["code"],
                    "organization_id": self.organization_id.id,
                    "process_id": item["process"].id,
                    "document_type": item["document_type"],
                    "owner_id": item["owner"].id if item["owner"] else False,
                    "related_control_instance_ids": [Command.set(item["instance"].ids)] if item["instance"] else False,
                }
            )
            note_lines = ["Migrated current revision from authorized customer inventory."]
            if item["migration_note"]:
                note_lines.append(item["migration_note"])
            if item["attachment_filename"] and not item["attachment"]:
                note_lines.append(f"Source attachment filename recorded: {item['attachment_filename']}.")
            revision = Revision.create(
                {
                    "document_id": document.id,
                    "revision": item["revision"],
                    "effective_date": item["effective_date"],
                    "change_summary": "\n".join(note_lines),
                    "prepared_by": self.env.user.id,
                }
            )
            if item["attachment"]:
                attachment = Attachment.create({**item["attachment"], "res_id": revision.id})
                revision.write({"attachment_id": attachment.id})
            status = item["status"]
            if status in {"under_review", "approved", "active", "obsolete"}:
                document.action_submit_for_review()
            if status in {"approved", "active", "obsolete"}:
                document.action_approve()
            if status in {"active", "obsolete"}:
                revision.action_activate()
            if status == "obsolete":
                document.action_obsolete()
            created |= document
        return {
            "type": "ir.actions.act_window",
            "name": "Imported Documents",
            "res_model": "pm.qms.document",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }
