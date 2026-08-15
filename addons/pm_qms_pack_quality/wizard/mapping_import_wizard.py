import base64
import csv
import io
import uuid
from datetime import date

from odoo import fields, models
from odoo.exceptions import AccessError, UserError


class PmQmsMappingImportWizard(models.TransientModel):
    _name = "pm.qms.mapping.import.wizard"
    _description = "Perfect Match QMS Mapping Import Wizard"

    mapping_profile_id = fields.Many2one("pm.qms.mapping.profile", required=True)
    csv_file = fields.Binary(required=True)
    filename = fields.Char()

    def _check_admin(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
            raise AccessError("Only QMS Administrators can import external mapping metadata.")

    def _parse_date(self, value, row_number):
        value = (value or "").strip()
        if not value:
            return False
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise UserError(f"Row {row_number}: review_date must use YYYY-MM-DD format.") from error

    def _reviewed_by(self, value):
        value = (value or "").strip()
        if not value:
            return self.env.user
        user = self.env["res.users"].search(["|", ("login", "=", value), ("email", "=", value)], limit=1)
        return user or self.env.user

    def action_import(self):
        self.ensure_one()
        self._check_admin()
        profile = self.mapping_profile_id
        if profile.state == "retired":
            raise UserError("Cannot import mappings into a retired mapping profile.")
        required_columns = {
            "pm_control_code",
            "standard_name",
            "edition",
            "reference",
            "mapping_type",
            "review_status",
            "reviewed_by",
            "review_date",
            "notes",
        }
        forbidden_columns = {"requirement_text", "standard_text", "clause_text", "copyright_text"}
        try:
            decoded = base64.b64decode(self.csv_file).decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise UserError("Mapping CSV must be UTF-8 encoded.") from error
        reader = csv.DictReader(io.StringIO(decoded))
        fieldnames = set(reader.fieldnames or [])
        if not required_columns.issubset(fieldnames):
            missing = ", ".join(sorted(required_columns - fieldnames))
            raise UserError(f"Mapping CSV is missing required columns: {missing}")
        if forbidden_columns.intersection(fieldnames):
            raise UserError("Mapping CSV must not include external requirement text columns.")

        rows = []
        seen = set()
        batch = str(uuid.uuid4())
        controls_by_code = {
            control.code: control
            for control in profile.pack_id.control_line_ids.filtered("active").mapped("control_id")
        }
        allowed_types = {"direct", "supporting", "partial"}
        allowed_statuses = {"draft", "reviewed", "approved", "rejected"}
        for row_number, row in enumerate(reader, start=2):
            control_code = (row.get("pm_control_code") or "").strip()
            standard_name = (row.get("standard_name") or profile.standard_name or "").strip()
            edition = (row.get("edition") or profile.edition or "").strip()
            reference = (row.get("reference") or "").strip()
            mapping_type = (row.get("mapping_type") or "supporting").strip()
            review_status = (row.get("review_status") or "draft").strip()
            if not control_code:
                raise UserError(f"Row {row_number}: pm_control_code is required.")
            if control_code not in controls_by_code:
                raise UserError(f"Row {row_number}: control {control_code} is not part of the selected pack.")
            if standard_name != profile.standard_name or edition != profile.edition:
                raise UserError(f"Row {row_number}: standard_name and edition must match the mapping profile.")
            if not reference:
                raise UserError(f"Row {row_number}: reference is required.")
            if mapping_type not in allowed_types:
                raise UserError(f"Row {row_number}: mapping_type must be direct, supporting, or partial.")
            if review_status not in allowed_statuses:
                raise UserError(f"Row {row_number}: review_status must be draft, reviewed, approved, or rejected.")
            if review_status == "approved" and (not row.get("reviewed_by") or not row.get("review_date")):
                raise UserError(f"Row {row_number}: approved mappings require reviewed_by and review_date.")
            key = (control_code, standard_name, edition, reference)
            if key in seen:
                raise UserError(f"Row {row_number}: duplicate mapping in import file.")
            seen.add(key)
            existing = self.env["pm.qms.external.mapping"].search(
                [
                    ("control_id", "=", controls_by_code[control_code].id),
                    ("standard_name", "=", standard_name),
                    ("edition", "=", edition),
                    ("reference", "=", reference),
                ],
                limit=1,
            )
            if existing:
                raise UserError(f"Row {row_number}: mapping already exists for {control_code} / {reference}.")
            rows.append(
                {
                    "mapping_profile_id": profile.id,
                    "control_id": controls_by_code[control_code].id,
                    "standard_name": standard_name,
                    "edition": edition,
                    "reference": reference,
                    "mapping_type": mapping_type,
                    "review_status": review_status,
                    "reviewed_by_id": self._reviewed_by(row.get("reviewed_by")).id if review_status != "draft" else False,
                    "review_date": self._parse_date(row.get("review_date"), row_number) if review_status != "draft" else False,
                    "note": (row.get("notes") or "").strip(),
                    "import_batch": batch,
                }
            )
        if not rows:
            raise UserError("Mapping CSV contains no mapping rows.")
        mappings = self.env["pm.qms.external.mapping"].create(rows)
        return {
            "type": "ir.actions.act_window",
            "name": "Imported External Mappings",
            "res_model": "pm.qms.external.mapping",
            "view_mode": "list,form",
            "domain": [("id", "in", mappings.ids)],
        }
