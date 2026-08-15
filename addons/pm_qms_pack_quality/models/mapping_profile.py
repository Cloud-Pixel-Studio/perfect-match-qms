from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsMappingProfile(models.Model):
    _name = "pm.qms.mapping.profile"
    _description = "Perfect Match QMS External Mapping Profile"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code, edition, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    pack_id = fields.Many2one(
        "pm.qms.framework.pack",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    standard_name = fields.Char(required=True, tracking=True)
    edition = fields.Char(required=True, tracking=True)
    publisher = fields.Char(required=True, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("retired", "Retired"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    effective_date = fields.Date()
    retirement_date = fields.Date()
    notes = fields.Text(
        help="Perfect Match notes only. Do not copy external standard requirement text here."
    )
    active = fields.Boolean(default=True)
    mapping_ids = fields.One2many(
        "pm.qms.external.mapping",
        "mapping_profile_id",
        string="Mappings",
        copy=False,
    )

    total_control_count = fields.Integer(compute="_compute_mapping_counts")
    mapped_control_count = fields.Integer(compute="_compute_mapping_counts")
    unmapped_control_count = fields.Integer(compute="_compute_mapping_counts")
    pending_mapping_count = fields.Integer(compute="_compute_mapping_counts")
    rejected_mapping_count = fields.Integer(compute="_compute_mapping_counts")
    mapping_completeness_percent = fields.Float(compute="_compute_mapping_counts")

    _code_edition_company_uniq = models.Constraint(
        "UNIQUE(code, edition, company_id)",
        "Mapping profile code and edition must be unique per company.",
    )

    @api.depends(
        "pack_id.control_line_ids.active",
        "pack_id.control_line_ids.control_id",
        "mapping_ids.active",
        "mapping_ids.control_id",
        "mapping_ids.review_status",
    )
    def _compute_mapping_counts(self):
        for profile in self:
            controls = profile.pack_id.control_line_ids.filtered("active").mapped("control_id")
            approved = profile.mapping_ids.filtered(
                lambda mapping: mapping.active and mapping.review_status == "approved"
            ).mapped("control_id")
            pending = profile.mapping_ids.filtered(
                lambda mapping: mapping.active and mapping.review_status in {"draft", "reviewed"}
            )
            rejected = profile.mapping_ids.filtered(
                lambda mapping: mapping.active and mapping.review_status == "rejected"
            )
            total = len(controls)
            mapped = len(set(approved.ids))
            profile.total_control_count = total
            profile.mapped_control_count = mapped
            profile.unmapped_control_count = max(total - mapped, 0)
            profile.pending_mapping_count = len(pending)
            profile.rejected_mapping_count = len(rejected)
            profile.mapping_completeness_percent = (mapped / total * 100.0) if total else 0.0

    def _check_admin(self):
        if self.env.context.get("install_mode") or self.env.context.get("module") or self.env.context.get("pm_qms_quality_seed"):
            return
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
            raise AccessError("Only QMS Administrators can configure or approve external mapping profiles.")

    @api.constrains("company_id", "pack_id", "effective_date", "retirement_date")
    def _check_profile_constraints(self):
        for profile in self:
            if profile.pack_id.company_id != profile.company_id:
                raise ValidationError("Mapping profile pack must belong to the same company.")
            if (
                profile.effective_date
                and profile.retirement_date
                and profile.retirement_date < profile.effective_date
            ):
                raise ValidationError("Mapping profile retirement date cannot be before its effective date.")

    def _ensure_definition_mutable(self):
        locked = self.filtered(lambda profile: profile.state != "draft")
        if locked:
            raise UserError("Create a new mapping profile instead of changing an active or retired profile.")

    def action_activate(self):
        self._check_admin()
        for profile in self:
            if profile.state != "draft":
                raise UserError("Only draft mapping profiles can be activated.")
            if profile.pack_id.state != "active":
                raise UserError("The related framework pack must be active before activating a mapping profile.")
        previous = {profile.id: profile.state for profile in self}
        self.with_context(pm_qms_mapping_profile_workflow=True).write(
            {"state": "active", "effective_date": fields.Date.context_today(self)}
        )
        for profile in self:
            profile._log_qms_event(
                event_type="workflow",
                previous_state=previous[profile.id],
                new_state="active",
                decision="External mapping profile activated",
            )

    def action_retire(self):
        self._check_admin()
        previous = {profile.id: profile.state for profile in self}
        self.with_context(pm_qms_mapping_profile_workflow=True).write(
            {"state": "retired", "retirement_date": fields.Date.context_today(self)}
        )
        for profile in self:
            profile._log_qms_event(
                event_type="workflow",
                previous_state=previous[profile.id],
                new_state="retired",
                decision="External mapping profile retired",
            )

    def action_reset_to_draft(self):
        self._check_admin()
        if any(profile.mapping_ids.filtered(lambda mapping: mapping.review_status == "approved") for profile in self):
            raise UserError("A profile with approved mappings cannot be reset to draft.")
        previous = {profile.id: profile.state for profile in self}
        self.with_context(pm_qms_mapping_profile_workflow=True).write({"state": "draft"})
        for profile in self:
            profile._log_qms_event(
                event_type="workflow",
                previous_state=previous[profile.id],
                new_state="draft",
                decision="External mapping profile reset to draft",
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_mapping_profile_workflow"):
            raise AccessError("Use mapping profile workflow actions to change status.")
        definition_fields = {"code", "company_id", "pack_id", "standard_name", "edition", "publisher"}
        if definition_fields.intersection(vals):
            self._check_admin()
            self._ensure_definition_mutable()
        return super().write(vals)

    def unlink(self):
        self._check_admin()
        if any(profile.state != "draft" or profile.mapping_ids for profile in self):
            raise UserError("Only unused draft mapping profiles can be deleted.")
        return super().unlink()
