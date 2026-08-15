from odoo import api, fields, models
from odoo.exceptions import AccessError


class PmQmsManagementReviewDecision(models.Model):
    _name = "pm.qms.management.review.decision"
    _description = "Perfect Match QMS Management Review Decision"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "decision_date desc, id desc"

    review_id = fields.Many2one("pm.qms.management.review", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="review_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="review_id.organization_id", store=True, readonly=True, index=True)
    name = fields.Char(required=True, tracking=True)
    description = fields.Text(required=True)
    decision_type = fields.Selection(
        [
            ("continue", "Continue"),
            ("change", "Change"),
            ("approve", "Approve"),
            ("reject", "Reject"),
            ("resource", "Resource"),
            ("improvement", "Improvement"),
            ("strategic", "Strategic"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
        tracking=True,
    )
    owner_id = fields.Many2one("res.users", tracking=True)
    decision_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    notes = fields.Text()
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for decision in records:
            decision.review_id._log_qms_event(
                event_type="review",
                previous_state=False,
                new_state=decision.decision_type,
                reviewer=self.env.user,
                decision="Management review decision recorded",
                notes=decision.name,
            )
        return records

    def _check_review_editable(self):
        for decision in self:
            if decision.review_id.state == "completed":
                if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
                    raise AccessError("Only QMS Administrators can correct decisions after review completion.")

    def write(self, vals):
        if vals:
            self._check_review_editable()
        return super().write(vals)

    def unlink(self):
        self._check_review_editable()
        return super().unlink()
