import hashlib
import json
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PmQmsIso9001TransitionReview(models.Model):
    _inherit = "pm.qms.iso9001.transition.review"

    migration_package_id = fields.Many2one(
        "pm.qms.iso9001.migration.package",
        compute="_compute_migration_package",
        string="Migration Package",
    )

    def _compute_migration_package(self):
        Package = self.env["pm.qms.iso9001.migration.package"]
        for review in self:
            review.migration_package_id = Package.search(
                [("readiness_review_id", "=", review.id)], limit=1
            )

    def action_prepare_migration_package(self):
        self.ensure_one()
        self._check_manager_permission()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            self
        )
        return {
            "type": "ir.actions.act_window",
            "name": "ISO 9001 Migration Package",
            "res_model": "pm.qms.iso9001.migration.package",
            "res_id": package.id,
            "view_mode": "form",
        }


class PmQmsIso9001MigrationPackage(models.Model):
    _name = "pm.qms.iso9001.migration.package"
    _description = "PM-QMS ISO 9001 Controlled Migration Package"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, code desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, readonly=True, copy=False, index=True)
    package_version = fields.Char(required=True, default="1.0", tracking=True)
    readiness_review_id = fields.Many2one(
        "pm.qms.iso9001.transition.review",
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    assessment_id = fields.Many2one(
        "pm.qms.iso9001.gap.assessment",
        related="readiness_review_id.assessment_id",
        store=True,
        readonly=True,
    )
    implementation_project_id = fields.Many2one(
        "pm.qms.implementation.project",
        related="readiness_review_id.implementation_project_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="readiness_review_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    source_edition_snapshot = fields.Char(required=True, readonly=True)
    target_edition_snapshot = fields.Char(required=True, readonly=True)
    migration_scope = fields.Text(required=True)
    source_inventory = fields.Text(required=True)
    compatibility_notes = fields.Text(required=True)
    dry_run_plan = fields.Text(required=True)
    backup_reference = fields.Char(
        required=True,
        help="Non-secret reference to the approved backup artifact.",
    )
    backup_sha256 = fields.Char(required=True)
    backup_verified = fields.Boolean(default=False)
    rollback_plan = fields.Text(required=True)
    rollback_acceptance_criteria = fields.Text(required=True)
    execution_window = fields.Char(
        help="Planned window only; this package does not execute a migration."
    )
    reviewer_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("preflight_passed", "Preflight Passed"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("returned", "Returned"),
            ("voided", "Voided"),
        ],
        required=True,
        default="draft",
        readonly=True,
        tracking=True,
    )
    manifest_snapshot = fields.Text(readonly=True)
    manifest_sha256 = fields.Char(readonly=True)
    preflight_by_id = fields.Many2one("res.users", readonly=True)
    preflight_date = fields.Datetime(readonly=True)
    submitted_by_id = fields.Many2one("res.users", readonly=True)
    submitted_date = fields.Datetime(readonly=True)
    approved_by_id = fields.Many2one("res.users", readonly=True)
    approved_date = fields.Datetime(readonly=True)
    returned_by_id = fields.Many2one("res.users", readonly=True)
    returned_date = fields.Datetime(readonly=True)
    return_reason = fields.Text(readonly=True)
    void_reason = fields.Text(readonly=True)

    _review_package_uniq = models.Constraint(
        "UNIQUE(readiness_review_id)",
        "Each readiness review may have only one controlled migration package.",
    )

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError(
                "Only QMS Managers or Administrators can manage migration packages."
            )

    def _write_workflow(self, values):
        self.ensure_one()
        return super().write(values)

    @api.model
    def _prepare_from_review(self, review):
        review.ensure_one()
        review._check_manager_permission()
        if review.state != "approved" or review.decision != "internal_review":
            raise UserError(
                "An approved readiness review with the internal-review decision is required."
            )
        existing = self.search([("readiness_review_id", "=", review.id)], limit=1)
        if existing:
            return existing
        return super().create(
            {
                "name": f"{review.name} - migration package",
                "code": self.env["ir.sequence"].next_by_code(
                    "pm.qms.iso9001.migration.package"
                )
                or "ISO-MIG-00000",
                "readiness_review_id": review.id,
                "source_edition_snapshot": review.source_edition_snapshot,
                "target_edition_snapshot": review.target_edition_snapshot,
                "migration_scope": "Document the approved companies, sites, processes, records, and exclusions.",
                "source_inventory": "Reference the controlled source inventory; do not embed credentials or raw backups.",
                "compatibility_notes": "Document approved compatibility findings and unresolved exceptions.",
                "dry_run_plan": "Document the isolated rehearsal, validation steps, and acceptance evidence.",
                "backup_reference": "PENDING-CONTROLLED-BACKUP",
                "backup_sha256": "0" * 64,
                "rollback_plan": "Document restoration steps, owners, decision points, and maximum recovery window.",
                "rollback_acceptance_criteria": "Document integrity, availability, relationship, and historical-record checks.",
                "reviewer_id": self.env.user.id,
            }
        )

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(
            "Prepare migration packages from an approved transition readiness review."
        )

    @api.constrains(
        "readiness_review_id",
        "reviewer_id",
        "source_edition_snapshot",
        "target_edition_snapshot",
        "backup_sha256",
    )
    def _check_relationships(self):
        for package in self:
            review = package.readiness_review_id
            if package.source_edition_snapshot != review.source_edition_snapshot:
                raise ValidationError("Migration package source edition must match its review.")
            if package.target_edition_snapshot != review.target_edition_snapshot:
                raise ValidationError("Migration package target edition must match its review.")
            if package.company_id not in package.reviewer_id.company_ids:
                raise ValidationError(
                    "The assigned reviewer must have access to the package company."
                )
            if not package.reviewer_id.has_group(
                "pm_qms_core.group_pm_qms_manager"
            ):
                raise ValidationError(
                    "The assigned reviewer must be a QMS Manager or Administrator."
                )
            digest = (package.backup_sha256 or "").lower()
            if digest and not SHA256_RE.fullmatch(digest):
                raise ValidationError(
                    "Backup SHA-256 must contain exactly 64 lowercase hexadecimal characters."
                )

    def _manifest_values(self):
        self.ensure_one()
        review = self.readiness_review_id
        actions = review.assessment_id.transition_action_ids.sorted("id")
        return {
            "schema": 1,
            "package_code": self.code,
            "package_version": self.package_version,
            "company_id": self.company_id.id,
            "readiness_review_id": review.id,
            "assessment_id": self.assessment_id.id,
            "implementation_project_id": self.implementation_project_id.id,
            "source_edition": self.source_edition_snapshot,
            "target_edition": self.target_edition_snapshot,
            "migration_scope": self.migration_scope,
            "source_inventory": self.source_inventory,
            "compatibility_notes": self.compatibility_notes,
            "dry_run_plan": self.dry_run_plan,
            "backup_reference": self.backup_reference,
            "backup_sha256": self.backup_sha256,
            "rollback_plan": self.rollback_plan,
            "rollback_acceptance_criteria": self.rollback_acceptance_criteria,
            "execution_window": self.execution_window or "",
            "transition_actions": [
                {
                    "id": action.id,
                    "code": action.code,
                    "state": action.state,
                    "project_id": action.implementation_project_id.id,
                    "submitted_by_id": action.submitted_by_id.id,
                    "verified_by_id": action.verified_by_id.id,
                }
                for action in actions
            ],
        }

    def _render_manifest(self):
        self.ensure_one()
        return json.dumps(
            self._manifest_values(),
            sort_keys=True,
            separators=(",", ":"),
        )

    def action_run_preflight(self):
        self._check_manager_permission()
        for package in self:
            if package.state not in ("draft", "returned"):
                raise UserError("Preflight is allowed only for draft or returned packages.")
            review = package.readiness_review_id
            if review.state != "approved" or review.decision != "internal_review":
                raise UserError("The readiness review is no longer approved for internal review.")
            actions = review.assessment_id.transition_action_ids
            if not actions or any(action.state != "completed" for action in actions):
                raise UserError("Every transition action must remain completed.")
            if any(
                not action.submitted_by_id
                or not action.verified_by_id
                or action.submitted_by_id == action.verified_by_id
                for action in actions
            ):
                raise UserError("Every transition action requires independent verification.")
            if actions.mapped("implementation_project_id") != package.implementation_project_id:
                raise UserError("Transition actions no longer match the implementation project.")
            if not package.backup_verified:
                raise UserError("Verify the controlled backup before passing preflight.")
            if package.backup_reference == "PENDING-CONTROLLED-BACKUP":
                raise UserError("Replace the placeholder with the controlled backup reference.")
            manifest = package._render_manifest()
            package._write_workflow(
                {
                    "state": "preflight_passed",
                    "manifest_snapshot": manifest,
                    "manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
                    "preflight_by_id": self.env.user.id,
                    "preflight_date": fields.Datetime.now(),
                    "returned_by_id": False,
                    "returned_date": False,
                    "return_reason": False,
                }
            )
        return True

    def action_submit(self):
        self._check_manager_permission()
        for package in self:
            if package.state != "preflight_passed":
                raise UserError("Pass preflight before submitting the migration package.")
            if package.reviewer_id == self.env.user:
                raise UserError("The package submitter and reviewer must be different users.")
            if package._render_manifest() != package.manifest_snapshot:
                raise UserError("Package inputs changed after preflight; run preflight again.")
            package._write_workflow(
                {
                    "state": "submitted",
                    "submitted_by_id": self.env.user.id,
                    "submitted_date": fields.Datetime.now(),
                }
            )
        return True

    def action_approve(self):
        self._check_manager_permission()
        for package in self:
            if package.state != "submitted":
                raise UserError("Only submitted migration packages can be approved.")
            if package.reviewer_id != self.env.user:
                raise AccessError("Only the assigned independent reviewer can approve.")
            if package.submitted_by_id == self.env.user:
                raise AccessError("The submitter cannot approve their own migration package.")
            if package._render_manifest() != package.manifest_snapshot:
                raise UserError("Package inputs changed after preflight; return and revalidate it.")
            digest = hashlib.sha256(package.manifest_snapshot.encode()).hexdigest()
            if digest != package.manifest_sha256:
                raise UserError("Migration package manifest integrity check failed.")
            package._write_workflow(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_date": fields.Datetime.now(),
                }
            )
        return True

    def action_return(self):
        self._check_manager_permission()
        for package in self:
            if package.state != "submitted":
                raise UserError("Only submitted migration packages can be returned.")
            if package.reviewer_id != self.env.user:
                raise AccessError("Only the assigned independent reviewer can return it.")
            if not package.return_reason:
                raise UserError("Document a return reason before returning the package.")
            package._write_workflow(
                {
                    "state": "returned",
                    "returned_by_id": self.env.user.id,
                    "returned_date": fields.Datetime.now(),
                }
            )
        return True

    def action_void(self):
        self._check_manager_permission()
        for package in self:
            if package.state == "approved":
                raise UserError("Approved migration packages are immutable and cannot be voided.")
            if not package.void_reason:
                raise UserError("Document a void reason before voiding the package.")
            package._write_workflow({"state": "voided"})
        return True

    def write(self, vals):
        if any(package.state in ("approved", "voided") for package in self):
            raise AccessError("Approved or voided migration packages are immutable.")
        workflow_fields = {
            "state",
            "code",
            "readiness_review_id",
            "source_edition_snapshot",
            "target_edition_snapshot",
            "manifest_snapshot",
            "manifest_sha256",
            "preflight_by_id",
            "preflight_date",
            "submitted_by_id",
            "submitted_date",
            "approved_by_id",
            "approved_date",
            "returned_by_id",
            "returned_date",
        }
        if workflow_fields.intersection(vals):
            raise AccessError("Workflow and snapshot fields cannot be changed directly.")
        if any(package.state == "submitted" for package in self):
            allowed = {"return_reason"}
            if set(vals) - allowed:
                raise AccessError("Submitted migration packages are locked.")
        self._check_manager_permission()
        result = super().write(vals)
        if any(package.state == "preflight_passed" for package in self):
            super(PmQmsIso9001MigrationPackage, self.filtered(
                lambda package: package.state == "preflight_passed"
            )).write(
                {
                    "state": "draft",
                    "manifest_snapshot": False,
                    "manifest_sha256": False,
                    "preflight_by_id": False,
                    "preflight_date": False,
                }
            )
        return result

    def unlink(self):
        self._check_manager_permission()
        if any(package.state not in ("draft", "returned") for package in self):
            raise UserError("Only draft or returned migration packages can be deleted.")
        return super().unlink()

    def copy(self, default=None):
        raise UserError("Migration packages cannot be copied.")
