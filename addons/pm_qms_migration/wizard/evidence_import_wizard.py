import base64
import csv
from io import StringIO

from odoo import Command, fields, models
from odoo.exceptions import AccessError, UserError


class PmQmsEvidenceImportWizard(models.TransientModel):
    _name = "pm.qms.evidence.import.wizard"
    _description = "Perfect Match QMS Evidence Import Wizard"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    organization_id = fields.Many2one("pm.qms.organization", required=True)
    csv_file = fields.Binary(required=True)
    filename = fields.Char()

    def _check_manager(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can import evidence metadata.")

    def _rows(self):
        self.ensure_one()
        try:
            text = base64.b64decode(self.csv_file).decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UserError("Evidence import CSV must be UTF-8 encoded.") from exc
        reader = csv.DictReader(StringIO(text))
        required = {
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
        }
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise UserError(f"Evidence import CSV is missing required columns: {', '.join(sorted(missing))}")
        return list(reader)

    def _parse_date(self, value, row_number):
        value = (value or "").strip()
        if not value:
            return fields.Date.context_today(self)
        try:
            return fields.Date.to_date(value)
        except ValueError as exc:
            raise UserError(f"Row {row_number}: evidence_date must use YYYY-MM-DD format.") from exc

    def _attachment_values(self, row, row_number):
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
            "res_model": "pm.qms.evidence",
            "type": "binary",
        }

    def _resolve_rows(self):
        self.ensure_one()
        if self.organization_id.company_id != self.company_id:
            raise UserError("Selected organization must belong to the selected company.")
        allowed_types = dict(self.env["pm.qms.evidence"]._fields["evidence_type"].selection)
        allowed_states = {"draft", "submitted", "under_review", "rejected"}
        resolved = []
        for row_number, row in enumerate(self._rows(), start=2):
            name = (row.get("evidence_name") or "").strip()
            instance_code = (row.get("control_instance_code") or "").strip()
            requirement_name = (row.get("evidence_requirement_name") or "").strip()
            evidence_type = (row.get("evidence_type") or "record").strip()
            state = (row.get("state") or "draft").strip()
            if not name or not instance_code or not requirement_name:
                raise UserError(
                    f"Row {row_number}: evidence_name, control_instance_code, and evidence_requirement_name are required."
                )
            if evidence_type not in allowed_types:
                raise UserError(f"Row {row_number}: unsupported evidence_type '{evidence_type}'.")
            if state not in allowed_states:
                raise UserError(f"Row {row_number}: unsupported state '{state}'. Imported evidence cannot be accepted.")
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
            requirement = self.env["pm.qms.evidence.requirement"].search(
                [
                    ("name", "=", requirement_name),
                    ("control_id", "=", instance.control_id.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if not requirement:
                raise UserError(f"Row {row_number}: evidence_requirement_name was not found for the control instance.")
            document = False
            document_code = (row.get("document_code") or "").strip()
            if document_code:
                document = self.env["pm.qms.document"].search(
                    [
                        ("code", "=", document_code),
                        ("company_id", "=", self.company_id.id),
                        ("organization_id", "=", self.organization_id.id),
                    ],
                    limit=1,
                )
                if not document:
                    raise UserError(f"Row {row_number}: document_code was not found in the selected organization.")
            resolved.append(
                {
                    "name": name,
                    "instance": instance,
                    "requirement": requirement,
                    "evidence_type": evidence_type,
                    "evidence_date": self._parse_date(row.get("evidence_date"), row_number),
                    "state": state,
                    "document": document,
                    "migration_note": (row.get("migration_note") or "").strip(),
                    "attachment": self._attachment_values(row, row_number),
                }
            )
        return resolved

    def action_import(self):
        self._check_manager()
        Evidence = self.env["pm.qms.evidence"]
        Attachment = self.env["ir.attachment"]
        created = Evidence
        for item in self._resolve_rows():
            description = "Migrated evidence metadata from authorized customer inventory."
            if item["migration_note"]:
                description = f"{description}\n{item['migration_note']}"
            evidence = Evidence.create(
                {
                    "name": item["name"],
                    "control_instance_id": item["instance"].id,
                    "evidence_requirement_id": item["requirement"].id,
                    "evidence_type": item["evidence_type"],
                    "evidence_date": item["evidence_date"],
                    "description": description,
                    "document_ids": [Command.set(item["document"].ids)] if item["document"] else False,
                    "owner_id": self.env.user.id,
                }
            )
            if item["attachment"]:
                attachment = Attachment.create({**item["attachment"], "res_id": evidence.id})
                evidence.write({"attachment_ids": [Command.link(attachment.id)]})
            if item["state"] in {"submitted", "under_review", "rejected"}:
                evidence.action_submit()
            if item["state"] in {"under_review", "rejected"}:
                evidence.action_review()
            if item["state"] == "rejected":
                evidence.action_reject()
            created |= evidence
        return {
            "type": "ir.actions.act_window",
            "name": "Imported Evidence",
            "res_model": "pm.qms.evidence",
            "view_mode": "list,form",
            "domain": [("id", "in", created.ids)],
        }
