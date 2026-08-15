from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsManagementReviewAction(models.Model):
    _name = "pm.qms.management.review.action"
    _description = "Perfect Match QMS Management Review Action"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "target_date, code, id"
    _rec_name = "code"

    review_id = fields.Many2one("pm.qms.management.review", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="review_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="review_id.organization_id", store=True, readonly=True, index=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    owner_id = fields.Many2one("res.users", tracking=True)
    target_date = fields.Date(tracking=True)
    completion_date = fields.Date(readonly=True)
    verified_by_id = fields.Many2one("res.users", readonly=True)
    verified_date = fields.Date(readonly=True)
    priority = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        required=True,
        tracking=True,
    )
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
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.management.review.action") or "PM-MRA-00000"
        records = super().create(vals_list)
        for action in records:
            action.review_id._log_qms_event(
                event_type="workflow",
                previous_state=False,
                new_state=action.status,
                reviewer=self.env.user,
                decision="Management review action created",
                notes=action.code,
            )
        return records

    @api.depends("target_date", "status")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for action in self:
            overdue = bool(action.target_date and action.status not in ("completed", "verified", "cancelled") and action.target_date < today)
            action.is_overdue = overdue
            action.days_overdue = (today - action.target_date).days if overdue else 0

    @api.constrains("target_date", "completion_date", "verified_date")
    def _check_dates(self):
        for action in self:
            if action.completion_date and action.review_id.actual_date and action.completion_date < action.review_id.actual_date:
                raise ValidationError("Action completion cannot be before the management review meeting date.")
            if action.verified_date and action.completion_date and action.verified_date < action.completion_date:
                raise ValidationError("Action verification cannot be before completion.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can verify or cancel management review actions.")

    def _check_owner_or_manager(self):
        if self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            return
        for action in self:
            if action.owner_id != self.env.user:
                raise AccessError("Only the assigned owner or QMS Manager can update this management review action.")

    def _transition(self, status, decision, require_manager=False, extra_values=None):
        if require_manager:
            self._check_manager_permission()
        else:
            self._check_owner_or_manager()
        for action in self:
            previous = action.status
            values = {"status": status}
            if extra_values:
                values.update(extra_values)
            action.with_context(pm_qms_management_review_action_workflow=True).write(values)
            action._log_qms_event(
                event_type="workflow",
                previous_state=previous,
                new_state=status,
                reviewer=self.env.user if require_manager else None,
                decision=decision,
            )

    def action_start(self):
        self._transition("in_progress", "Management review action started")

    def action_complete(self):
        self._transition(
            "completed",
            "Management review action completed",
            extra_values={"completion_date": fields.Date.context_today(self)},
        )

    def action_verify(self):
        self._transition(
            "verified",
            "Management review action verified",
            require_manager=True,
            extra_values={"verified_by_id": self.env.user.id, "verified_date": fields.Date.context_today(self)},
        )

    def action_cancel(self):
        self._transition("cancelled", "Management review action cancelled", require_manager=True)

    def write(self, vals):
        if "status" in vals and not self.env.context.get("pm_qms_management_review_action_workflow"):
            raise AccessError("Use management review action workflow actions to change status.")
        if vals and not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            self._check_owner_or_manager()
            forbidden = {
                "review_id",
                "company_id",
                "organization_id",
                "code",
                "owner_id",
                "target_date",
                "priority",
                "verified_by_id",
                "verified_date",
            }
            if forbidden.intersection(vals):
                raise AccessError("Only QMS Managers can reassign or replan management review actions.")
        return super().write(vals)

    def unlink(self):
        if any(action.review_id.state != "draft" for action in self):
            raise UserError("Management review actions cannot be deleted after review workflow starts.")
        return super().unlink()
