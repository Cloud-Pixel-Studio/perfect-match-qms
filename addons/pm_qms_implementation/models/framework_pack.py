from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PmQmsFrameworkPack(models.Model):
    _name = "pm.qms.framework.pack"
    _description = "Perfect Match QMS Framework Pack"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code, version, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    version = fields.Char(required=True, default="1.0", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    description = fields.Text()
    pack_type = fields.Selection(
        [
            ("core", "Core"),
            ("standard", "Standard"),
            ("industry", "Industry"),
            ("customer", "Customer"),
            ("custom", "Custom"),
        ],
        default="core",
        required=True,
        tracking=True,
    )
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
    active = fields.Boolean(default=True)
    control_line_ids = fields.One2many(
        "pm.qms.framework.pack.control",
        "pack_id",
        string="Pack Controls",
        copy=True,
    )
    implementation_project_ids = fields.Many2many(
        "pm.qms.implementation.project",
        "pm_qms_implementation_project_pack_rel",
        "pack_id",
        "implementation_project_id",
        string="Implementation Projects",
        readonly=True,
    )
    control_count = fields.Integer(compute="_compute_counts")
    implementation_project_count = fields.Integer(compute="_compute_counts")

    _code_version_company_uniq = models.Constraint(
        "UNIQUE(code, version, company_id)",
        "Framework pack code and version must be unique per company.",
    )

    @api.depends("control_line_ids", "implementation_project_ids")
    def _compute_counts(self):
        for pack in self:
            pack.control_count = len(pack.control_line_ids.filtered("active"))
            pack.implementation_project_count = len(pack.implementation_project_ids)

    @api.constrains("effective_date", "retirement_date")
    def _check_dates(self):
        for pack in self:
            if pack.effective_date and pack.retirement_date and pack.retirement_date < pack.effective_date:
                raise ValidationError("Pack retirement date cannot be before its effective date.")

    def _ensure_draft_for_definition_change(self):
        locked = self.filtered(lambda pack: pack.state != "draft")
        if locked:
            raise UserError("Create a new pack version instead of modifying an active or retired pack definition.")

    def action_activate(self):
        for pack in self:
            if pack.state != "draft":
                raise UserError("Only draft packs can be activated.")
            if not pack.control_line_ids.filtered("active"):
                raise UserError("A framework pack needs at least one control before activation.")
        previous = {pack.id: pack.state for pack in self}
        self.with_context(pm_qms_pack_workflow=True).write(
            {
                "state": "active",
                "effective_date": fields.Date.context_today(self),
            }
        )
        for pack in self:
            pack._log_qms_event(
                event_type="workflow",
                previous_state=previous[pack.id],
                new_state="active",
                decision="Framework pack activated",
            )

    def action_retire(self):
        previous = {pack.id: pack.state for pack in self}
        self.with_context(pm_qms_pack_workflow=True).write(
            {
                "state": "retired",
                "retirement_date": fields.Date.context_today(self),
            }
        )
        for pack in self:
            pack._log_qms_event(
                event_type="workflow",
                previous_state=previous[pack.id],
                new_state="retired",
                decision="Framework pack retired",
            )

    def action_reset_to_draft(self):
        if any(pack.implementation_project_ids for pack in self):
            raise UserError("A pack already used by an implementation project cannot be reset to draft.")
        previous = {pack.id: pack.state for pack in self}
        self.with_context(pm_qms_pack_workflow=True).write({"state": "draft"})
        for pack in self:
            pack._log_qms_event(
                event_type="workflow",
                previous_state=previous[pack.id],
                new_state="draft",
                decision="Framework pack reset to draft",
            )

    def write(self, vals):
        definition_fields = {"code", "version", "company_id", "control_line_ids"}
        if "state" in vals and not self.env.context.get("pm_qms_pack_workflow"):
            raise UserError("Use framework pack workflow actions to change status.")
        if definition_fields.intersection(vals):
            self._ensure_draft_for_definition_change()
        return super().write(vals)

    def unlink(self):
        if any(pack.state != "draft" or pack.implementation_project_ids for pack in self):
            raise UserError("Only unused draft packs can be deleted.")
        return super().unlink()


class PmQmsFrameworkPackControl(models.Model):
    _name = "pm.qms.framework.pack.control"
    _description = "Perfect Match QMS Framework Pack Control"
    _order = "pack_id, sequence, id"

    pack_id = fields.Many2one("pm.qms.framework.pack", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="pack_id.company_id", store=True, readonly=True, index=True)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="restrict", index=True)
    sequence = fields.Integer(default=10)
    required = fields.Boolean(default=True)
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _pack_control_uniq = models.Constraint(
        "UNIQUE(pack_id, control_id)",
        "A control can appear only once in the same framework pack.",
    )

    def _is_module_loading(self):
        return bool(self.env.context.get("install_mode") or self.env.context.get("module"))

    @api.constrains("pack_id", "control_id")
    def _check_company_alignment(self):
        for line in self:
            if line.control_id.company_id != line.pack_id.company_id:
                raise ValidationError("Pack controls must belong to the same company as the framework pack.")

    def _ensure_pack_mutable(self):
        if self._is_module_loading():
            return
        if any(line.pack_id.state != "draft" for line in self):
            raise UserError("Create a new pack version instead of modifying controls on an active or retired pack.")

    @api.model_create_multi
    def create(self, vals_list):
        pack_ids = [vals.get("pack_id") for vals in vals_list if vals.get("pack_id")]
        packs = self.env["pm.qms.framework.pack"].browse(pack_ids)
        if any(pack.state != "draft" for pack in packs) and not self._is_module_loading():
            raise UserError("Controls can only be added to draft framework packs.")
        return super().create(vals_list)

    def write(self, vals):
        if {"pack_id", "control_id", "sequence", "required", "active", "notes"}.intersection(vals):
            self._ensure_pack_mutable()
        return super().write(vals)

    def unlink(self):
        self._ensure_pack_mutable()
        return super().unlink()
