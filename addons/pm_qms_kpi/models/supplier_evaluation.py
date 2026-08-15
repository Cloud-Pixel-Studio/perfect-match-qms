from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsSupplierEvaluation(models.Model):
    _name = "pm.qms.supplier.evaluation"
    _description = "Perfect Match QMS Supplier Evaluation"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "evaluation_date desc, supplier_id, id desc"

    supplier_id = fields.Many2one("res.partner", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    evaluation_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    period_start = fields.Date(required=True, tracking=True)
    period_end = fields.Date(required=True, tracking=True)
    evaluator_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True, tracking=True)
    quality_score = fields.Float(tracking=True)
    delivery_score = fields.Float(tracking=True)
    service_score = fields.Float(tracking=True)
    compliance_score = fields.Float(tracking=True)
    quality_weight = fields.Float(default=40.0, required=True)
    delivery_weight = fields.Float(default=40.0, required=True)
    service_weight = fields.Float(default=20.0, required=True)
    compliance_weight = fields.Float(default=0.0, required=True)
    total_weight_snapshot = fields.Float(compute="_compute_overall_score", store=True)
    overall_score = fields.Float(compute="_compute_overall_score", store=True)
    status = fields.Selection(
        [
            ("approved", "Approved"),
            ("conditional", "Conditional"),
            ("monitor", "Monitor"),
            ("disqualified", "Disqualified"),
        ],
        default="monitor",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _supplier_evaluation_period_uniq = models.Constraint(
        "UNIQUE(supplier_id, organization_id, period_start, period_end)",
        "Supplier evaluation already exists for this organization, supplier, and period.",
    )

    @api.depends(
        "quality_score",
        "delivery_score",
        "service_score",
        "compliance_score",
        "quality_weight",
        "delivery_weight",
        "service_weight",
        "compliance_weight",
    )
    def _compute_overall_score(self):
        for evaluation in self:
            total_weight = (
                evaluation.quality_weight
                + evaluation.delivery_weight
                + evaluation.service_weight
                + evaluation.compliance_weight
            )
            evaluation.total_weight_snapshot = total_weight
            if total_weight:
                evaluation.overall_score = (
                    evaluation.quality_score * evaluation.quality_weight
                    + evaluation.delivery_score * evaluation.delivery_weight
                    + evaluation.service_score * evaluation.service_weight
                    + evaluation.compliance_score * evaluation.compliance_weight
                ) / total_weight
            else:
                evaluation.overall_score = 0.0

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for evaluation in self:
            if evaluation.period_end < evaluation.period_start:
                raise ValidationError("Supplier evaluation period end cannot be before period start.")

    @api.constrains(
        "quality_score",
        "delivery_score",
        "service_score",
        "compliance_score",
        "quality_weight",
        "delivery_weight",
        "service_weight",
        "compliance_weight",
    )
    def _check_scores_and_weights(self):
        for evaluation in self:
            scores = [
                evaluation.quality_score,
                evaluation.delivery_score,
                evaluation.service_score,
                evaluation.compliance_score,
            ]
            if any(score < 0 or score > 100 for score in scores):
                raise ValidationError("Supplier evaluation scores must be between 0 and 100.")
            weights = [
                evaluation.quality_weight,
                evaluation.delivery_weight,
                evaluation.service_weight,
                evaluation.compliance_weight,
            ]
            if any(weight < 0 for weight in weights):
                raise ValidationError("Supplier evaluation weights cannot be negative.")
            if sum(weights) <= 0:
                raise ValidationError("Supplier evaluation total weight must be greater than zero.")

    @api.constrains("supplier_id", "organization_id")
    def _check_supplier_company(self):
        for evaluation in self:
            if evaluation.supplier_id.company_id and evaluation.supplier_id.company_id != evaluation.company_id:
                raise ValidationError("Supplier partner must belong to the same company or be shared.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can complete supplier evaluations.")

    def action_complete(self):
        self._check_manager_permission()
        for evaluation in self:
            previous = evaluation.state
            evaluation.with_context(pm_qms_supplier_evaluation_workflow=True).write({"state": "completed"})
            evaluation._log_qms_event(
                event_type="review",
                previous_state=previous,
                new_state="completed",
                reviewer=self.env.user,
                decision="Supplier evaluation completed",
            )

    def action_cancel(self):
        self._check_manager_permission()
        for evaluation in self:
            previous = evaluation.state
            evaluation.with_context(pm_qms_supplier_evaluation_workflow=True).write({"state": "cancelled"})
            evaluation._log_qms_event(
                event_type="closure",
                previous_state=previous,
                new_state="cancelled",
                approver=self.env.user,
                decision="Supplier evaluation cancelled",
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_supplier_evaluation_workflow"):
            raise AccessError("Use supplier evaluation workflow actions to change state.")
        locked_fields = {
            "supplier_id",
            "organization_id",
            "evaluation_date",
            "period_start",
            "period_end",
            "quality_score",
            "delivery_score",
            "service_score",
            "compliance_score",
            "quality_weight",
            "delivery_weight",
            "service_weight",
            "compliance_weight",
            "status",
        }
        if locked_fields.intersection(vals) and any(evaluation.state == "completed" for evaluation in self):
            if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
                raise AccessError("Only QMS Administrators can correct completed supplier evaluations.")
        return super().write(vals)

    def unlink(self):
        if any(evaluation.state != "draft" for evaluation in self):
            raise UserError("Only draft supplier evaluations can be deleted.")
        return super().unlink()
