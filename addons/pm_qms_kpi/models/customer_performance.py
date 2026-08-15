from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsCustomerPerformance(models.Model):
    _name = "pm.qms.customer.performance"
    _description = "Perfect Match QMS Customer Performance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "period_end desc, customer_id, id desc"

    customer_id = fields.Many2one("res.partner", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    period_start = fields.Date(required=True, tracking=True)
    period_end = fields.Date(required=True, tracking=True)
    customer_satisfaction_score = fields.Float(tracking=True)
    manual_complaint_count = fields.Integer(string="Manual Complaint Count", tracking=True)
    complaint_count = fields.Integer(compute="_compute_ncr_metrics", string="Total Complaint Count")
    open_complaint_count = fields.Integer(compute="_compute_ncr_metrics")
    return_count = fields.Integer(tracking=True)
    rejection_count = fields.Integer(tracking=True)
    delivery_performance = fields.Float(tracking=True)
    survey_response_count = fields.Integer(tracking=True)
    ncr_count = fields.Integer(compute="_compute_ncr_metrics")
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _customer_period_uniq = models.Constraint(
        "UNIQUE(customer_id, organization_id, period_start, period_end)",
        "Customer performance already exists for this organization, customer, and period.",
    )

    @api.depends("customer_id", "organization_id", "period_start", "period_end", "manual_complaint_count")
    def _compute_ncr_metrics(self):
        Ncr = self.env["pm.qms.nonconformity"]
        for performance in self:
            if not performance.customer_id or not performance.period_start or not performance.period_end:
                performance.ncr_count = 0
                performance.open_complaint_count = 0
                performance.complaint_count = performance.manual_complaint_count
                continue
            domain = [
                ("source_type", "=", "customer"),
                ("company_id", "=", performance.company_id.id),
                ("organization_id", "=", performance.organization_id.id),
                ("detected_date", ">=", performance.period_start),
                ("detected_date", "<=", performance.period_end),
            ]
            ncr_count = Ncr.search_count(domain)
            open_count = Ncr.search_count(domain + [("state", "not in", ("closed", "cancelled"))])
            performance.ncr_count = ncr_count
            performance.open_complaint_count = open_count
            performance.complaint_count = performance.manual_complaint_count + ncr_count

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for performance in self:
            if performance.period_end < performance.period_start:
                raise ValidationError("Customer performance period end cannot be before period start.")

    @api.constrains(
        "customer_satisfaction_score",
        "manual_complaint_count",
        "return_count",
        "rejection_count",
        "delivery_performance",
        "survey_response_count",
    )
    def _check_metric_bounds(self):
        for performance in self:
            if performance.customer_satisfaction_score < 0 or performance.customer_satisfaction_score > 100:
                raise ValidationError("Customer satisfaction score must be between 0 and 100.")
            if performance.delivery_performance < 0 or performance.delivery_performance > 100:
                raise ValidationError("Customer delivery performance must be between 0 and 100.")
            counts = [
                performance.manual_complaint_count,
                performance.return_count,
                performance.rejection_count,
                performance.survey_response_count,
            ]
            if any(value < 0 for value in counts):
                raise ValidationError("Customer performance counts cannot be negative.")

    @api.constrains("customer_id", "organization_id")
    def _check_customer_company(self):
        for performance in self:
            if performance.customer_id.company_id and performance.customer_id.company_id != performance.company_id:
                raise ValidationError("Customer partner must belong to the same company or be shared.")


class ResPartner(models.Model):
    _inherit = "res.partner"

    qms_customer_performance_ids = fields.One2many(
        "pm.qms.customer.performance",
        "customer_id",
        string="QMS Customer Performance",
    )
    qms_customer_satisfaction_ids = fields.One2many(
        "pm.qms.customer.satisfaction",
        "customer_id",
        string="QMS Customer Satisfaction",
    )
    qms_supplier_performance_ids = fields.One2many(
        "pm.qms.supplier.performance",
        "supplier_id",
        string="QMS Supplier Performance",
    )
    qms_supplier_evaluation_ids = fields.One2many(
        "pm.qms.supplier.evaluation",
        "supplier_id",
        string="QMS Supplier Evaluations",
    )
