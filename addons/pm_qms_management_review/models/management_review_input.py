from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsManagementReviewInput(models.Model):
    _name = "pm.qms.management.review.input"
    _description = "Perfect Match QMS Management Review Input Snapshot"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "title"
    _order = "category, title, id"

    review_id = fields.Many2one("pm.qms.management.review", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="review_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="review_id.organization_id", store=True, readonly=True, index=True)
    category = fields.Selection(
        [
            ("previous_actions", "Previous Actions"),
            ("organizational_changes", "Organizational Changes"),
            ("objectives", "Objectives"),
            ("kpi", "KPI"),
            ("customer_performance", "Customer Performance"),
            ("customer_satisfaction", "Customer Satisfaction"),
            ("supplier_performance", "Supplier Performance"),
            ("supplier_evaluation", "Supplier Evaluation"),
            ("audit", "Audit"),
            ("audit_findings", "Audit Findings"),
            ("risks", "Risks"),
            ("opportunities", "Opportunities"),
            ("ncr", "NCR"),
            ("capa", "CAPA"),
            ("resources", "Resources"),
            ("improvement_opportunities", "Improvement Opportunities"),
            ("other", "Other"),
        ],
        required=True,
        index=True,
        tracking=True,
    )
    title = fields.Char(required=True, tracking=True)
    description = fields.Text()
    snapshot_date = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    status_snapshot = fields.Char()
    numeric_value = fields.Float()
    text_value = fields.Text()
    unit_of_measure = fields.Char()
    target_snapshot = fields.Float()
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    source_type = fields.Selection(
        [
            ("manual", "Manual"),
            ("objective", "Objective"),
            ("kpi_measurement", "KPI Measurement"),
            ("customer_performance", "Customer Performance"),
            ("customer_satisfaction", "Customer Satisfaction"),
            ("supplier_performance", "Supplier Performance"),
            ("supplier_evaluation", "Supplier Evaluation"),
            ("audit", "Audit"),
            ("audit_finding", "Audit Finding"),
            ("risk", "Risk or Opportunity"),
            ("ncr", "NCR"),
            ("capa", "CAPA"),
            ("management_review_action", "Management Review Action"),
            ("resource", "Resource"),
            ("organizational_change", "Organizational Change"),
            ("improvement_opportunity", "Improvement Opportunity"),
            ("other", "Other"),
        ],
        default="manual",
        required=True,
        tracking=True,
    )
    source_identifier = fields.Char(
        help="Safe source identifier such as an internal code. This is not a generic record reference."
    )
    notes = fields.Text()
    is_system_generated = fields.Boolean(default=False, readonly=True)
    active = fields.Boolean(default=True)

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for item in self:
            if item.period_end < item.period_start:
                raise ValidationError("Management review input period end cannot be before period start.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("review_id"):
                review = self.env["pm.qms.management.review"].browse(vals["review_id"])
                if not vals.get("period_start"):
                    vals["period_start"] = review.period_start
                if not vals.get("period_end"):
                    vals["period_end"] = review.period_end
                if not vals.get("snapshot_date"):
                    vals["snapshot_date"] = review.snapshot_date or fields.Datetime.now()
        return super().create(vals_list)

    def _check_review_editable(self):
        for item in self:
            if item.review_id.state in ("ready", "in_progress", "completed", "cancelled"):
                if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
                    raise AccessError("Review inputs are locked once the management review is ready or completed.")

    def write(self, vals):
        if vals:
            self._check_review_editable()
        return super().write(vals)

    def unlink(self):
        self._check_review_editable()
        return super().unlink()
