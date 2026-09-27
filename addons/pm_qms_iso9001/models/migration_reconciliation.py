import hashlib
import json

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


DISPOSITIONS = [
    ("created", "Created"),
    ("reused", "Reused"),
    ("skipped", "Skipped"),
    ("rejected", "Rejected"),
    ("manual_review", "Manual Review"),
]
REFERENCE_FIELDS = (
    "source_system_reference",
    "source_record_reference",
    "target_record_reference",
    "rationale",
    "evidence_reference",
    "source_record_sha256",
    "target_record_sha256",
)


class PmQmsIso9001MigrationExecution(models.Model):
    _inherit = "pm.qms.iso9001.migration.execution"

    reconciliation_line_ids = fields.One2many(
        "pm.qms.iso9001.migration.reconciliation",
        "execution_id",
        string="Record Reconciliation",
        copy=False,
    )
    reconciliation_ledger_started = fields.Boolean(
        default=False, readonly=True, copy=False
    )
    created_count = fields.Integer(
        compute="_compute_reconciliation_counts", store=True, readonly=True
    )
    reused_count = fields.Integer(
        compute="_compute_reconciliation_counts", store=True, readonly=True
    )
    skipped_count = fields.Integer(
        compute="_compute_reconciliation_counts", store=True, readonly=True
    )
    rejected_count = fields.Integer(
        compute="_compute_reconciliation_counts", store=True, readonly=True
    )
    manual_review_count = fields.Integer(
        compute="_compute_reconciliation_counts", store=True, readonly=True
    )

    @api.depends(
        "reconciliation_line_ids.disposition",
        "report_snapshot",
        "reconciliation_ledger_started",
        "state",
    )
    def _compute_reconciliation_counts(self):
        for execution in self:
            lines = execution.reconciliation_line_ids
            if lines:
                counts = {
                    disposition: len(
                        lines.filtered(lambda line: line.disposition == disposition)
                    )
                    for disposition, _label in DISPOSITIONS
                }
            elif execution.report_snapshot:
                try:
                    legacy_report = json.loads(execution.report_snapshot)
                except (TypeError, ValueError):
                    legacy_report = {}
                if "reconciliation_items" not in legacy_report:
                    counts = {
                        disposition: legacy_report.get(
                            f"{disposition}_count", execution[f"{disposition}_count"]
                        )
                        for disposition, _label in DISPOSITIONS
                    }
                else:
                    counts = {
                        disposition: legacy_report.get(f"{disposition}_count", 0)
                        for disposition, _label in DISPOSITIONS
                    }
            elif execution.reconciliation_ledger_started:
                counts = {disposition: 0 for disposition, _label in DISPOSITIONS}
            else:
                counts = {
                    disposition: execution[f"{disposition}_count"]
                    for disposition, _label in DISPOSITIONS
                }
            for disposition, _label in DISPOSITIONS:
                execution[f"{disposition}_count"] = counts[disposition]

    def _report_values(self):
        values = super()._report_values()
        for execution in self:
            if not execution.reconciliation_line_ids and execution.report_snapshot:
                try:
                    previous_report = json.loads(execution.report_snapshot)
                except (TypeError, ValueError):
                    previous_report = {}
                if "reconciliation_items" not in previous_report:
                    continue
            lines = execution.reconciliation_line_ids.sorted(
                key=lambda line: (
                    line.source_system_reference,
                    line.source_record_reference,
                )
            )
            values["reconciliation_items"] = [
                line._snapshot_values() for line in lines
            ]
        return values

    def action_record_start(self):
        result = super().action_record_start()
        for execution in self:
            execution._write_workflow({"reconciliation_ledger_started": True})
        return result

    def action_return(self):
        result = super().action_return()
        for execution in self:
            execution._write_workflow({"reconciliation_ledger_started": True})
        return result

    def write(self, vals):
        if "reconciliation_ledger_started" in vals:
            raise AccessError("Reconciliation lifecycle is system controlled.")
        report_fields = {
            "execution_log_reference",
            "execution_log_sha256",
            "post_migration_checks",
            "rollback_decision",
            "rollback_evidence",
            "outcome",
        }
        if report_fields.intersection(vals) and any(
            execution.state != "in_progress"
            or execution.operator_id != self.env.user
            for execution in self
        ):
            raise AccessError(
                "Only the assigned operator can record outcome evidence while in progress."
            )
        derived_counts = {
            "created_count",
            "reused_count",
            "skipped_count",
            "rejected_count",
            "manual_review_count",
        }
        if derived_counts.intersection(vals):
            raise AccessError(
                "Reconciliation counts are derived from record-level entries."
            )
        if "reconciliation_line_ids" in vals and any(
            execution.state != "in_progress"
            or execution.operator_id != self.env.user
            for execution in self
        ):
            raise AccessError(
                "Only the assigned operator can edit reconciliation entries while in progress."
            )
        return super().write(vals)


class PmQmsIso9001MigrationReconciliation(models.Model):
    _name = "pm.qms.iso9001.migration.reconciliation"
    _description = "PM-QMS ISO 9001 Migration Record Reconciliation"
    _order = "source_system_reference, source_record_reference, id"
    _rec_name = "source_record_reference"

    execution_id = fields.Many2one(
        "pm.qms.iso9001.migration.execution",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="execution_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    source_edition = fields.Char(
        related="execution_id.package_id.source_edition_snapshot",
        store=True,
        readonly=True,
    )
    target_edition = fields.Char(
        related="execution_id.package_id.target_edition_snapshot",
        store=True,
        readonly=True,
    )
    source_system_reference = fields.Char(
        required=True,
        size=128,
        help=(
            "Opaque, non-secret identifier for the source system; "
            "never enter a connection string."
        ),
    )
    source_record_reference = fields.Char(
        required=True,
        size=256,
        help="Opaque identifier only; do not copy record content or personal data here.",
    )
    source_record_sha256 = fields.Char(
        size=64,
        help="Optional SHA-256 of an approved external source export or record manifest.",
    )
    target_record_reference = fields.Char(
        size=256,
        help="Opaque target identifier; required for created or reused records.",
    )
    target_record_sha256 = fields.Char(
        size=64,
        help="Optional SHA-256 of an approved external target export or record manifest.",
    )
    disposition = fields.Selection(DISPOSITIONS, required=True, index=True)
    historical_source_preserved = fields.Boolean(
        required=True,
        default=False,
        help="Explicit operator attestation that the historical source record remains preserved.",
    )
    rationale = fields.Text(
        required=True,
        help="Concise reason for this disposition; do not include source record contents.",
    )
    evidence_reference = fields.Char(
        size=512,
        help="Non-secret reference to controlled evidence stored outside this record.",
    )
    item_snapshot_sha256 = fields.Char(
        compute="_compute_item_snapshot_sha256",
        store=True,
        readonly=True,
        help="Deterministic digest of this reconciliation entry's non-secret metadata.",
    )

    _source_record_uniq = models.Constraint(
        "UNIQUE(execution_id, source_system_reference, source_record_reference)",
        "Each source record can appear only once in an execution reconciliation.",
    )

    @api.depends(
        "source_system_reference",
        "source_record_reference",
        "source_record_sha256",
        "target_record_reference",
        "target_record_sha256",
        "disposition",
        "historical_source_preserved",
        "rationale",
        "evidence_reference",
        "execution_id.package_id.source_edition_snapshot",
        "execution_id.package_id.target_edition_snapshot",
    )
    def _compute_item_snapshot_sha256(self):
        for line in self:
            payload = json.dumps(
                line._snapshot_values(include_digest=False),
                sort_keys=True,
                separators=(",", ":"),
            )
            line.item_snapshot_sha256 = hashlib.sha256(
                payload.encode("utf-8")
            ).hexdigest()

    def _snapshot_values(self, include_digest=True):
        self.ensure_one()
        values = {
            "source_edition": self.source_edition,
            "target_edition": self.target_edition,
            "source_system_reference": self.source_system_reference,
            "source_record_reference": self.source_record_reference,
            "source_record_sha256": self.source_record_sha256 or "",
            "target_record_reference": self.target_record_reference or "",
            "target_record_sha256": self.target_record_sha256 or "",
            "disposition": self.disposition,
            "historical_source_preserved": self.historical_source_preserved,
            "rationale": self.rationale,
            "evidence_reference": self.evidence_reference or "",
        }
        if include_digest:
            values["item_snapshot_sha256"] = self.item_snapshot_sha256
        return values

    def _check_edit_permission(self, execution):
        execution._check_manager_permission()
        if execution.state != "in_progress":
            raise AccessError(
                "Reconciliation entries are editable only while execution is in progress."
            )
        if execution.operator_id != self.env.user:
            raise AccessError(
                "Only the assigned execution operator can edit reconciliation entries."
            )

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            execution = self.env[
                "pm.qms.iso9001.migration.execution"
            ].browse(values.get("execution_id")).exists()
            if not execution:
                raise ValidationError("A valid execution record is required.")
            self._check_edit_permission(execution)
            for field_name in REFERENCE_FIELDS:
                if values.get(field_name):
                    values[field_name] = values[field_name].strip()
            if values.get("source_record_sha256"):
                values["source_record_sha256"] = values[
                    "source_record_sha256"
                ].lower()
            if values.get("target_record_sha256"):
                values["target_record_sha256"] = values[
                    "target_record_sha256"
                ].lower()
            if (
                "historical_source_preserved" in values
                and not values["historical_source_preserved"]
            ):
                raise ValidationError(
                    "Historical source records must remain preserved."
                )
        records = super().create(vals_list)
        for execution in records.mapped("execution_id"):
            if not execution.reconciliation_ledger_started:
                execution._write_workflow({"reconciliation_ledger_started": True})
        return records

    def write(self, vals):
        if "item_snapshot_sha256" in vals or "company_id" in vals:
            raise AccessError("Snapshot and company fields are system controlled.")
        if "execution_id" in vals:
            raise AccessError("A reconciliation entry cannot be moved to another execution.")
        for line in self:
            self._check_edit_permission(line.execution_id)
        values = dict(vals)
        for field_name in REFERENCE_FIELDS:
            if values.get(field_name):
                values[field_name] = values[field_name].strip()
        if values.get("source_record_sha256"):
            values["source_record_sha256"] = values["source_record_sha256"].lower()
        if values.get("target_record_sha256"):
            values["target_record_sha256"] = values["target_record_sha256"].lower()
        if (
            "historical_source_preserved" in values
            and not values["historical_source_preserved"]
        ):
            raise ValidationError("Historical source records must remain preserved.")
        return super().write(values)

    def unlink(self):
        for line in self:
            self._check_edit_permission(line.execution_id)
        return super().unlink()

    def copy(self, default=None):
        raise AccessError("Reconciliation entries cannot be copied.")

    @api.constrains(
        "source_system_reference",
        "source_record_reference",
        "target_record_reference",
        "source_record_sha256",
        "target_record_sha256",
        "disposition",
        "historical_source_preserved",
        "rationale",
    )
    def _check_reconciliation_values(self):
        for line in self:
            if not (line.source_system_reference or "").strip():
                raise ValidationError("A source system reference is required.")
            if not (line.source_record_reference or "").strip():
                raise ValidationError("A source record reference is required.")
            if not line.historical_source_preserved:
                raise ValidationError(
                    "Historical source records must remain preserved."
                )
            if not (line.rationale or "").strip():
                raise ValidationError("Document a rationale for every disposition.")
            if line.disposition in ("created", "reused") and not (
                line.target_record_reference or "").strip():
                raise ValidationError(
                    "Created and reused records require a target record reference."
                )
            for value in (
                line.source_record_sha256,
                line.target_record_sha256,
            ):
                if value and (
                    len(value) != 64
                    or any(character not in "0123456789abcdef" for character in value)
                ):
                    raise ValidationError(
                        "Record SHA-256 values must contain 64 lowercase hexadecimal characters."
                    )
