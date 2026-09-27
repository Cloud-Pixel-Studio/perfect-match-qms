import hashlib
import json
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PmQmsIso9001MigrationPackage(models.Model):
    _inherit = "pm.qms.iso9001.migration.package"

    execution_record_id = fields.Many2one(
        "pm.qms.iso9001.migration.execution",
        compute="_compute_execution_record",
        string="Execution Record",
    )

    def _compute_execution_record(self):
        Execution = self.env["pm.qms.iso9001.migration.execution"]
        for package in self:
            package.execution_record_id = Execution.search(
                [("package_id", "=", package.id)], limit=1
            )

    def action_prepare_execution_record(self):
        self.ensure_one()
        self._check_manager_permission()
        record = self.env[
            "pm.qms.iso9001.migration.execution"
        ]._prepare_from_package(self)
        return {
            "type": "ir.actions.act_window",
            "name": "ISO 9001 Migration Execution Record",
            "res_model": "pm.qms.iso9001.migration.execution",
            "res_id": record.id,
            "view_mode": "form",
        }


class PmQmsIso9001MigrationExecution(models.Model):
    _name = "pm.qms.iso9001.migration.execution"
    _description = "PM-QMS ISO 9001 Controlled Migration Execution Record"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, code desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, readonly=True, copy=False, index=True)
    package_id = fields.Many2one(
        "pm.qms.iso9001.migration.package",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="package_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    package_manifest_sha256 = fields.Char(required=True, readonly=True)
    operator_id = fields.Many2one(
        "res.users", required=True, ondelete="restrict", tracking=True
    )
    reviewer_id = fields.Many2one(
        "res.users", required=True, ondelete="restrict", tracking=True
    )
    environment_reference = fields.Char(
        required=True,
        help="Non-secret identifier for the approved target environment.",
    )
    fresh_preflight_evidence = fields.Text(required=True)
    backup_access_evidence = fields.Text(required=True)
    restoration_test_evidence = fields.Text(required=True)
    dry_run_evidence = fields.Text(required=True)
    authorization_notes = fields.Text(required=True)
    execution_log_reference = fields.Char(
        help="Non-secret reference to the immutable external execution log."
    )
    execution_log_sha256 = fields.Char(
        help="SHA-256 of the immutable external execution log."
    )
    post_migration_checks = fields.Text()
    rollback_decision = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("required", "Required"),
            ("executed", "Executed"),
        ]
    )
    rollback_evidence = fields.Text()
    created_count = fields.Integer(default=0)
    reused_count = fields.Integer(default=0)
    skipped_count = fields.Integer(default=0)
    rejected_count = fields.Integer(default=0)
    manual_review_count = fields.Integer(default=0)
    outcome = fields.Selection(
        [
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("rolled_back", "Rolled Back"),
        ]
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("preflight_passed", "Preflight Passed"),
            ("authorized", "Authorized"),
            ("in_progress", "In Progress"),
            ("recorded", "Outcome Recorded"),
            ("submitted", "Submitted for Closeout"),
            ("returned", "Returned"),
            ("closed", "Closed"),
        ],
        required=True,
        default="draft",
        readonly=True,
        tracking=True,
    )
    control_snapshot = fields.Text(readonly=True)
    control_sha256 = fields.Char(readonly=True)
    report_snapshot = fields.Text(readonly=True)
    report_sha256 = fields.Char(readonly=True)
    preflight_by_id = fields.Many2one("res.users", readonly=True)
    preflight_date = fields.Datetime(readonly=True)
    authorized_by_id = fields.Many2one("res.users", readonly=True)
    authorized_date = fields.Datetime(readonly=True)
    started_by_id = fields.Many2one("res.users", readonly=True)
    started_date = fields.Datetime(readonly=True)
    finished_by_id = fields.Many2one("res.users", readonly=True)
    finished_date = fields.Datetime(readonly=True)
    submitted_by_id = fields.Many2one("res.users", readonly=True)
    submitted_date = fields.Datetime(readonly=True)
    closed_by_id = fields.Many2one("res.users", readonly=True)
    closed_date = fields.Datetime(readonly=True)
    return_reason = fields.Text()
    closeout_notes = fields.Text()

    _package_execution_uniq = models.Constraint(
        "UNIQUE(package_id)",
        "Each approved migration package may have only one execution record.",
    )

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError(
                "Only QMS Managers or Administrators can manage migration execution records."
            )

    def _write_workflow(self, values):
        self.ensure_one()
        return super().write(values)

    @api.model
    def _prepare_from_package(self, package):
        package.ensure_one()
        package._check_manager_permission()
        if package.state != "approved":
            raise UserError("An approved migration package is required.")
        existing = self.search([("package_id", "=", package.id)], limit=1)
        if existing:
            return existing
        return super().create(
            {
                "name": f"{package.name} - execution record",
                "code": f"{package.code}-EXEC-01",
                "package_id": package.id,
                "package_manifest_sha256": package.manifest_sha256,
                "operator_id": package.submitted_by_id.id,
                "reviewer_id": package.approved_by_id.id,
                "environment_reference": "PENDING-CONTROLLED-ENVIRONMENT",
                "fresh_preflight_evidence": "Document fresh environment preflight evidence.",
                "backup_access_evidence": "Document backup accessibility evidence.",
                "restoration_test_evidence": "Document restoration-test evidence.",
                "dry_run_evidence": "Document isolated dry-run evidence.",
                "authorization_notes": "Document explicit execution authorization.",
            }
        )

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(
            "Prepare execution records from an approved migration package."
        )

    @api.constrains("operator_id", "reviewer_id")
    def _check_participants(self):
        for record in self:
            if record.operator_id == record.reviewer_id:
                raise ValidationError(
                    "The execution operator and closeout reviewer must be different users."
                )
            for user in (record.operator_id, record.reviewer_id):
                if record.company_id not in user.company_ids:
                    raise ValidationError(
                        "Execution participants must have access to the record company."
                    )
                if not user.has_group("pm_qms_core.group_pm_qms_manager"):
                    raise ValidationError(
                        "Execution participants must be QMS Managers or Administrators."
                    )

    @api.constrains("execution_log_sha256")
    def _check_execution_log_digest(self):
        for record in self:
            digest = (record.execution_log_sha256 or "").lower()
            if digest and not SHA256_RE.fullmatch(digest):
                raise ValidationError(
                    "Execution log SHA-256 must contain exactly 64 lowercase hexadecimal characters."
                )

    @api.constrains(
        "created_count",
        "reused_count",
        "skipped_count",
        "rejected_count",
        "manual_review_count",
    )
    def _check_counts(self):
        for record in self:
            counts = (
                record.created_count,
                record.reused_count,
                record.skipped_count,
                record.rejected_count,
                record.manual_review_count,
            )
            if any(count < 0 for count in counts):
                raise ValidationError("Execution result counts cannot be negative.")

    def _control_values(self):
        self.ensure_one()
        return {
            "schema": 1,
            "execution_code": self.code,
            "package_id": self.package_id.id,
            "package_manifest_sha256": self.package_manifest_sha256,
            "company_id": self.company_id.id,
            "operator_id": self.operator_id.id,
            "reviewer_id": self.reviewer_id.id,
            "environment_reference": self.environment_reference,
            "fresh_preflight_evidence": self.fresh_preflight_evidence,
            "backup_access_evidence": self.backup_access_evidence,
            "restoration_test_evidence": self.restoration_test_evidence,
            "dry_run_evidence": self.dry_run_evidence,
            "authorization_notes": self.authorization_notes,
        }

    def _render_control_snapshot(self):
        self.ensure_one()
        return json.dumps(
            self._control_values(), sort_keys=True, separators=(",", ":")
        )

    def _report_values(self):
        self.ensure_one()
        return {
            "execution_log_reference": self.execution_log_reference,
            "execution_log_sha256": self.execution_log_sha256,
            "post_migration_checks": self.post_migration_checks,
            "rollback_decision": self.rollback_decision,
            "rollback_evidence": self.rollback_evidence or "",
            "outcome": self.outcome,
            "created_count": self.created_count,
            "reused_count": self.reused_count,
            "skipped_count": self.skipped_count,
            "rejected_count": self.rejected_count,
            "manual_review_count": self.manual_review_count,
        }

    def _render_report_snapshot(self):
        self.ensure_one()
        return json.dumps(
            self._report_values(), sort_keys=True, separators=(",", ":")
        )

    def _assert_package_integrity(self):
        self.ensure_one()
        package = self.package_id
        if package.state != "approved":
            raise UserError("The source migration package is no longer approved.")
        if package.manifest_sha256 != self.package_manifest_sha256:
            raise UserError("The approved package manifest reference changed.")
        digest = hashlib.sha256(package.manifest_snapshot.encode()).hexdigest()
        if digest != package.manifest_sha256:
            raise UserError("The approved package manifest integrity check failed.")

    def action_run_preflight(self):
        self._check_manager_permission()
        placeholders = {
            "environment_reference": "PENDING-CONTROLLED-ENVIRONMENT",
            "fresh_preflight_evidence": "Document fresh environment preflight evidence.",
            "backup_access_evidence": "Document backup accessibility evidence.",
            "restoration_test_evidence": "Document restoration-test evidence.",
            "dry_run_evidence": "Document isolated dry-run evidence.",
            "authorization_notes": "Document explicit execution authorization.",
        }
        for record in self:
            if record.state not in ("draft", "returned"):
                raise UserError("Preflight is allowed only for draft or returned records.")
            record._assert_package_integrity()
            incomplete = [
                name for name, placeholder in placeholders.items()
                if record[name] == placeholder
            ]
            if incomplete:
                raise UserError(
                    "Replace every execution placeholder before preflight: "
                    + ", ".join(sorted(incomplete))
                )
            snapshot = record._render_control_snapshot()
            record._write_workflow(
                {
                    "state": "preflight_passed",
                    "control_snapshot": snapshot,
                    "control_sha256": hashlib.sha256(snapshot.encode()).hexdigest(),
                    "preflight_by_id": self.env.user.id,
                    "preflight_date": fields.Datetime.now(),
                    "return_reason": False,
                }
            )
        return True

    def action_authorize(self):
        self._check_manager_permission()
        for record in self:
            if record.state != "preflight_passed":
                raise UserError("Pass fresh preflight before authorization.")
            if record.reviewer_id != self.env.user:
                raise AccessError("Only the assigned independent reviewer can authorize.")
            if record.operator_id == self.env.user:
                raise AccessError("The operator cannot authorize their own execution.")
            record._assert_package_integrity()
            if record._render_control_snapshot() != record.control_snapshot:
                raise UserError("Execution controls changed after preflight.")
            if hashlib.sha256(record.control_snapshot.encode()).hexdigest() != record.control_sha256:
                raise UserError("Execution control snapshot integrity check failed.")
            record._write_workflow(
                {
                    "state": "authorized",
                    "authorized_by_id": self.env.user.id,
                    "authorized_date": fields.Datetime.now(),
                }
            )
        return True

    def action_record_start(self):
        self._check_manager_permission()
        for record in self:
            if record.state != "authorized":
                raise UserError("Independent authorization is required before start.")
            if record.operator_id != self.env.user:
                raise AccessError("Only the assigned operator can record the start.")
            record._assert_package_integrity()
            record._write_workflow(
                {
                    "state": "in_progress",
                    "started_by_id": self.env.user.id,
                    "started_date": fields.Datetime.now(),
                }
            )
        return True

    def action_record_outcome(self):
        self._check_manager_permission()
        for record in self:
            if record.state != "in_progress":
                raise UserError("Record start before recording the outcome.")
            if record.operator_id != self.env.user:
                raise AccessError("Only the assigned operator can record the outcome.")
            if not record.outcome:
                raise UserError("Select the controlled execution outcome.")
            required = {
                "execution_log_reference": record.execution_log_reference,
                "execution_log_sha256": record.execution_log_sha256,
                "post_migration_checks": record.post_migration_checks,
                "rollback_decision": record.rollback_decision,
            }
            missing = [name for name, value in required.items() if not value]
            if missing:
                raise UserError(
                    "Complete execution evidence before recording the outcome: "
                    + ", ".join(sorted(missing))
                )
            if record.outcome == "rolled_back" and record.rollback_decision != "executed":
                raise UserError("A rolled-back outcome requires an executed rollback decision.")
            if record.rollback_decision == "executed" and not record.rollback_evidence:
                raise UserError("Document rollback evidence when rollback was executed.")
            report = record._render_report_snapshot()
            record._write_workflow(
                {
                    "state": "recorded",
                    "report_snapshot": report,
                    "report_sha256": hashlib.sha256(report.encode()).hexdigest(),
                    "finished_by_id": self.env.user.id,
                    "finished_date": fields.Datetime.now(),
                }
            )
        return True

    def action_submit_closeout(self):
        self._check_manager_permission()
        for record in self:
            if record.state != "recorded":
                raise UserError("Record the outcome before closeout submission.")
            if record.operator_id != self.env.user:
                raise AccessError("Only the assigned operator can submit closeout.")
            if record._render_report_snapshot() != record.report_snapshot:
                raise UserError("Execution report changed after outcome recording.")
            if hashlib.sha256(record.report_snapshot.encode()).hexdigest() != record.report_sha256:
                raise UserError("Execution report integrity check failed.")
            record._write_workflow(
                {
                    "state": "submitted",
                    "submitted_by_id": self.env.user.id,
                    "submitted_date": fields.Datetime.now(),
                }
            )
        return True

    def action_return(self):
        self._check_manager_permission()
        for record in self:
            if record.state != "submitted":
                raise UserError("Only submitted execution records can be returned.")
            if record.reviewer_id != self.env.user:
                raise AccessError("Only the assigned reviewer can return closeout.")
            if not record.return_reason:
                raise UserError("Document a return reason.")
            record._write_workflow(
                {
                    "state": "in_progress",
                    "report_snapshot": False,
                    "report_sha256": False,
                    "finished_by_id": False,
                    "finished_date": False,
                    "submitted_by_id": False,
                    "submitted_date": False,
                }
            )
        return True

    def action_close(self):
        self._check_manager_permission()
        for record in self:
            if record.state != "submitted":
                raise UserError("Only submitted execution records can be closed.")
            if record.reviewer_id != self.env.user:
                raise AccessError("Only the assigned independent reviewer can close.")
            if record.operator_id == self.env.user:
                raise AccessError("The operator cannot approve their own closeout.")
            if not record.closeout_notes:
                raise UserError("Document independent closeout notes.")
            record._assert_package_integrity()
            if record._render_report_snapshot() != record.report_snapshot:
                raise UserError("Execution report changed after outcome recording.")
            if hashlib.sha256(record.report_snapshot.encode()).hexdigest() != record.report_sha256:
                raise UserError("Execution report integrity check failed.")
            record._write_workflow(
                {
                    "state": "closed",
                    "closed_by_id": self.env.user.id,
                    "closed_date": fields.Datetime.now(),
                }
            )
        return True

    def write(self, vals):
        if any(record.state == "closed" for record in self):
            raise AccessError("Closed migration execution records are immutable.")
        workflow_fields = {
            "state", "code", "package_id", "package_manifest_sha256",
            "control_snapshot", "control_sha256", "report_snapshot", "report_sha256", "preflight_by_id",
            "preflight_date", "authorized_by_id", "authorized_date",
            "started_by_id", "started_date", "finished_by_id", "finished_date",
            "submitted_by_id", "submitted_date", "closed_by_id", "closed_date",
        }
        if workflow_fields.intersection(vals):
            raise AccessError("Workflow and snapshot fields cannot be changed directly.")
        self._check_manager_permission()
        control_fields = {
            "operator_id", "reviewer_id", "environment_reference",
            "fresh_preflight_evidence", "backup_access_evidence",
            "restoration_test_evidence", "dry_run_evidence", "authorization_notes",
        }
        report_fields = {
            "execution_log_reference", "execution_log_sha256",
            "post_migration_checks", "rollback_decision", "rollback_evidence",
            "outcome", "created_count", "reused_count", "skipped_count",
            "rejected_count", "manual_review_count",
        }
        if report_fields.intersection(vals) and any(
            record.state != "in_progress" for record in self
        ):
            raise AccessError("Execution report fields are editable only while in progress.")
        if control_fields.intersection(vals) and any(
            record.state not in ("draft", "returned", "preflight_passed")
            for record in self
        ):
            raise AccessError("Authorized execution controls are locked.")
        result = super().write(vals)
        for record in self.filtered(
            lambda item: item.state in ("preflight_passed", "returned")
            and control_fields.intersection(vals)
        ):
            record._write_workflow(
                {
                    "state": "draft",
                    "control_snapshot": False,
                    "control_sha256": False,
                    "preflight_by_id": False,
                    "preflight_date": False,
                }
            )
        return result

    def unlink(self):
        self._check_manager_permission()
        if any(record.state not in ("draft", "returned") for record in self):
            raise UserError("Only draft or returned execution records can be deleted.")
        return super().unlink()

    def copy(self, default=None):
        raise UserError("Migration execution records cannot be copied.")
