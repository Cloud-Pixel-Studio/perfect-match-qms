from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsQualityAlert(models.Model):
    _name = "pm.qms.quality.alert"
    _description = "Perfect Match QMS Quality Alert"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one("res.company", related="organization_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    description = fields.Text(required=True)
    complaint_id = fields.Many2one("pm.qms.customer.complaint", ondelete="restrict")
    ncr_id = fields.Many2one("pm.qms.nonconformity", ondelete="restrict")
    supplier_issue_id = fields.Many2one("pm.qms.supplier.issue", ondelete="restrict")
    scar_id = fields.Many2one("pm.qms.scar", ondelete="restrict")
    effective_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    review_date = fields.Date(string="Expiration / Review Date")
    owner_id = fields.Many2one("res.users", tracking=True)
    affected_area = fields.Char()
    affected_reference = fields.Char()
    audience_notes = fields.Text(string="Required Audience / Roles")
    attachment_ids = fields.Many2many("ir.attachment", "pm_qms_quality_alert_attachment_rel", "alert_id", "attachment_id")
    state = fields.Selection(
        [("draft", "Draft"), ("published", "Published"), ("expired", "Expired"), ("closed", "Closed"), ("cancelled", "Cancelled")],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "Quality alert code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.quality.alert") or "QA-0000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.constrains("complaint_id", "ncr_id", "supplier_issue_id", "scar_id")
    def _check_source_alignment(self):
        for alert in self:
            for sources in (alert.complaint_id, alert.ncr_id, alert.supplier_issue_id, alert.scar_id):
                for source in sources:
                    if source.company_id != alert.company_id or source.organization_id != alert.organization_id:
                        raise ValidationError("Quality alert sources must match the alert company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage quality alerts.")

    def _transition(self, state, decision, event_type="workflow"):
        self._check_manager_permission()
        for alert in self:
            previous = alert.state
            alert.with_context(pm_qms_quality_alert_workflow=True).write({"state": state})
            alert._log_qms_event(event_type=event_type, previous_state=previous, new_state=state, reviewer=self.env.user, decision=decision)

    def action_publish(self):
        self._transition("published", "Quality alert published")

    def action_expire(self):
        self._transition("expired", "Quality alert expired")

    def action_close(self):
        self._transition("closed", "Quality alert closed", event_type="closure")

    def action_cancel(self):
        self._transition("cancelled", "Quality alert cancelled", event_type="closure")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_quality_alert_workflow"):
            raise AccessError("Use quality alert workflow actions to change alert status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(alert.state != "draft" for alert in self):
            raise UserError("Only draft quality alerts can be deleted.")
        return super().unlink()
