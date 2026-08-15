from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsAuditProgram(models.Model):
    _name = "pm.qms.audit.program"
    _description = "Perfect Match QMS Audit Program"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "date_start desc, code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    owner_id = fields.Many2one("res.users", tracking=True)
    date_start = fields.Date(required=True)
    date_end = fields.Date(required=True)
    objective = fields.Text()
    description = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    audit_ids = fields.One2many("pm.qms.audit", "program_id", string="Audits")
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Audit program code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.audit.program") or "PM-AUDPROG-00000"
        return super().create(vals_list)

    @api.constrains("date_start", "date_end")
    def _check_dates(self):
        for program in self:
            if program.date_start and program.date_end and program.date_end < program.date_start:
                raise ValidationError("Audit program end date cannot be before the start date.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage audit program workflow.")

    def _transition(self, state, decision, event_type="workflow"):
        self._check_manager_permission()
        for program in self:
            previous = program.state
            program.with_context(pm_qms_audit_program_workflow=True).write({"state": state})
            program._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=state,
                reviewer=self.env.user,
                approver=self.env.user if event_type in ("approval", "closure") else None,
                decision=decision,
            )

    def action_approve(self):
        for program in self:
            if program.state != "draft":
                raise UserError("Only draft audit programs can be approved.")
        self._transition("approved", "Audit program approved", event_type="approval")

    def action_activate(self):
        for program in self:
            if program.state != "approved":
                raise UserError("Only approved audit programs can be activated.")
        self._transition("active", "Audit program activated")

    def action_complete(self):
        for program in self:
            if program.state != "active":
                raise UserError("Only active audit programs can be completed.")
        self._transition("completed", "Audit program completed", event_type="closure")

    def action_cancel(self):
        for program in self:
            if program.state in ("completed", "cancelled"):
                raise UserError("Completed or cancelled audit programs cannot be cancelled again.")
        self._transition("cancelled", "Audit program cancelled", event_type="closure")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_audit_program_workflow"):
            raise AccessError("Use audit program workflow actions to change audit program status.")
        return super().write(vals)

    def unlink(self):
        if any(program.state != "draft" for program in self):
            raise UserError("Only draft audit programs can be deleted.")
        return super().unlink()
