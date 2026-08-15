from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsCustomerSatisfaction(models.Model):
    _name = "pm.qms.customer.satisfaction"
    _description = "Perfect Match QMS Customer Satisfaction Measurement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "measurement_date desc, id desc"

    customer_id = fields.Many2one("res.partner", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    measurement_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    period_start = fields.Date(required=True, tracking=True)
    period_end = fields.Date(required=True, tracking=True)
    measurement_method = fields.Selection(
        [
            ("survey", "Survey"),
            ("scorecard", "Scorecard"),
            ("direct_feedback", "Direct Feedback"),
            ("complaint_analysis", "Complaint Analysis"),
            ("customer_rating", "Customer Rating"),
            ("other", "Other"),
        ],
        default="survey",
        required=True,
        tracking=True,
    )
    score = fields.Float(required=True, tracking=True)
    score_scale_max = fields.Float(default=100.0, required=True, tracking=True)
    score_percent = fields.Float(compute="_compute_score_percent", store=True)
    response_count = fields.Integer(tracking=True)
    notes = fields.Text()
    owner_id = fields.Many2one("res.users", tracking=True)
    active = fields.Boolean(default=True)

    _customer_satisfaction_period_uniq = models.Constraint(
        "UNIQUE(customer_id, organization_id, measurement_method, period_start, period_end)",
        "Customer satisfaction measurement already exists for this customer, method, organization, and period.",
    )

    @api.depends("score", "score_scale_max")
    def _compute_score_percent(self):
        for satisfaction in self:
            satisfaction.score_percent = (
                (satisfaction.score / satisfaction.score_scale_max) * 100 if satisfaction.score_scale_max else 0.0
            )

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for satisfaction in self:
            if satisfaction.period_end < satisfaction.period_start:
                raise ValidationError("Customer satisfaction period end cannot be before period start.")

    @api.constrains("score", "score_scale_max", "response_count")
    def _check_score(self):
        for satisfaction in self:
            if satisfaction.score_scale_max <= 0:
                raise ValidationError("Customer satisfaction score scale must be greater than zero.")
            if satisfaction.score < 0 or satisfaction.score > satisfaction.score_scale_max:
                raise ValidationError("Customer satisfaction score must be within the configured scale.")
            if satisfaction.response_count < 0:
                raise ValidationError("Customer satisfaction response count cannot be negative.")

    @api.constrains("customer_id", "organization_id")
    def _check_customer_company(self):
        for satisfaction in self:
            if satisfaction.customer_id.company_id and satisfaction.customer_id.company_id != satisfaction.company_id:
                raise ValidationError("Customer partner must belong to the same company or be shared.")
