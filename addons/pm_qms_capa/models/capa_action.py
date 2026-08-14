from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class PmQmsCapaAction(models.Model):
    _name = "pm.qms.capa.action"
    _description = "Perfect Match QMS CAPA Action"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "target_date, id"

    capa_id = fields.Many2one("pm.qms.capa", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="capa_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="capa_id.organization_id", store=True, readonly=True, index=True)
    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    owner_id = fields.Many2one("res.users", tracking=True)
    target_date = fields.Date()
    completion_date = fields.Date(readonly=True)
    status = fields.Selection(
        [
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("verified", "Verified"),
            ("cancelled", "Cancelled"),
        ],
        default="open",
        required=True,
        tracking=True,
    )
    verification_notes = fields.Text()
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)

    @api.depends("target_date", "status")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for action in self:
            overdue = bool(action.target_date and action.status not in ("completed", "verified", "cancelled") and action.target_date < today)
            action.is_overdue = overdue
            action.days_overdue = (today - action.target_date).days if overdue else 0

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can verify CAPA actions.")

    def _transition(self, status, decision, require_manager=False, extra_values=None):
        if require_manager:
            self._check_manager_permission()
        for action in self:
            previous = action.status
            values = {"status": status}
            if extra_values:
                values.update(extra_values)
            action.with_context(pm_qms_capa_action_workflow=True).write(values)
            action._log_qms_event(
                event_type="workflow",
                previous_state=previous,
                new_state=status,
                reviewer=self.env.user if require_manager else None,
                decision=decision,
            )

    def action_start(self):
        self._transition("in_progress", "CAPA action started")

    def action_complete(self):
        self._transition(
            "completed",
            "CAPA action completed",
            extra_values={"completion_date": fields.Date.context_today(self)},
        )

    def action_verify(self):
        self._transition("verified", "CAPA action verified", require_manager=True)

    def action_cancel(self):
        self._transition("cancelled", "CAPA action cancelled", require_manager=True)

    def write(self, vals):
        if "status" in vals and not self.env.context.get("pm_qms_capa_action_workflow"):
            raise AccessError("Use CAPA action workflow actions to change action status.")
        return super().write(vals)

    def unlink(self):
        if any(action.capa_id.state != "draft" for action in self):
            raise UserError("CAPA actions cannot be deleted after CAPA workflow starts.")
        return super().unlink()
