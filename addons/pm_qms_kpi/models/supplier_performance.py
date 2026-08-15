from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsSupplierPerformance(models.Model):
    _name = "pm.qms.supplier.performance"
    _description = "Perfect Match QMS Supplier Performance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "period_end desc, supplier_id, id desc"

    supplier_id = fields.Many2one("res.partner", required=True, ondelete="restrict", index=True, tracking=True)
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
    quality_score = fields.Float(tracking=True)
    delivery_score = fields.Float(tracking=True)
    overall_score = fields.Float(compute="_compute_overall_score", store=True)
    received_quantity = fields.Float(tracking=True)
    rejected_quantity = fields.Float(tracking=True)
    late_delivery_count = fields.Integer(tracking=True)
    total_delivery_count = fields.Integer(tracking=True)
    supplier_ncr_count = fields.Integer(compute="_compute_supplier_ncr_count")
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _supplier_period_uniq = models.Constraint(
        "UNIQUE(supplier_id, organization_id, period_start, period_end)",
        "Supplier performance already exists for this organization, supplier, and period.",
    )

    @api.depends("quality_score", "delivery_score")
    def _compute_overall_score(self):
        for performance in self:
            performance.overall_score = (performance.quality_score + performance.delivery_score) / 2.0

    @api.depends("supplier_id", "organization_id", "period_start", "period_end")
    def _compute_supplier_ncr_count(self):
        Ncr = self.env["pm.qms.nonconformity"]
        for performance in self:
            if not performance.supplier_id or not performance.period_start or not performance.period_end:
                performance.supplier_ncr_count = 0
                continue
            performance.supplier_ncr_count = Ncr.search_count(
                [
                    ("source_type", "=", "supplier"),
                    ("company_id", "=", performance.company_id.id),
                    ("organization_id", "=", performance.organization_id.id),
                    ("detected_date", ">=", performance.period_start),
                    ("detected_date", "<=", performance.period_end),
                ]
            )

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for performance in self:
            if performance.period_end < performance.period_start:
                raise ValidationError("Supplier performance period end cannot be before period start.")

    @api.constrains(
        "quality_score",
        "delivery_score",
        "received_quantity",
        "rejected_quantity",
        "late_delivery_count",
        "total_delivery_count",
    )
    def _check_metric_bounds(self):
        for performance in self:
            if performance.quality_score < 0 or performance.quality_score > 100:
                raise ValidationError("Supplier quality score must be between 0 and 100.")
            if performance.delivery_score < 0 or performance.delivery_score > 100:
                raise ValidationError("Supplier delivery score must be between 0 and 100.")
            if performance.received_quantity < 0 or performance.rejected_quantity < 0:
                raise ValidationError("Supplier quantities cannot be negative.")
            if performance.rejected_quantity > performance.received_quantity:
                raise ValidationError("Rejected quantity cannot exceed received quantity.")
            if performance.late_delivery_count < 0 or performance.total_delivery_count < 0:
                raise ValidationError("Supplier delivery counts cannot be negative.")
            if performance.late_delivery_count > performance.total_delivery_count:
                raise ValidationError("Late delivery count cannot exceed total delivery count.")

    @api.constrains("supplier_id", "organization_id")
    def _check_supplier_company(self):
        for performance in self:
            if performance.supplier_id.company_id and performance.supplier_id.company_id != performance.company_id:
                raise ValidationError("Supplier partner must belong to the same company or be shared.")
