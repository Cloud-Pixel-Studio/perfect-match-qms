from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsRisk(models.Model):
    _name = "pm.qms.risk"
    _description = "Perfect Match QMS Risk or Opportunity"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
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
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True)
    owner_id = fields.Many2one("res.users", tracking=True)
    risk_type = fields.Selection(
        [("risk", "Risk"), ("opportunity", "Opportunity")],
        default="risk",
        required=True,
        tracking=True,
    )
    category = fields.Selection(
        [
            ("strategic", "Strategic"),
            ("operational", "Operational"),
            ("process", "Process"),
            ("supplier", "Supplier"),
            ("document", "Document"),
            ("customer", "Customer"),
            ("security", "Security"),
            ("other", "Other"),
        ],
        default="operational",
        required=True,
        tracking=True,
    )
    source = fields.Char()
    description = fields.Text(required=True)
    cause = fields.Text()
    potential_effect = fields.Text()
    benefit = fields.Text()
    opportunity_action = fields.Text()
    likelihood = fields.Integer(default=1, required=True, tracking=True)
    impact = fields.Integer(default=1, required=True, tracking=True)
    initial_score = fields.Integer(compute="_compute_scores", store=True)
    initial_level = fields.Selection(
        [("low", "Low"), ("moderate", "Moderate"), ("high", "High"), ("critical", "Critical")],
        compute="_compute_scores",
        store=True,
    )
    response_strategy = fields.Selection(
        [
            ("accept", "Accept"),
            ("mitigate", "Mitigate"),
            ("transfer", "Transfer"),
            ("avoid", "Avoid"),
            ("exploit", "Exploit"),
            ("enhance", "Enhance"),
            ("share", "Share"),
        ],
        default="mitigate",
        tracking=True,
    )
    mitigation_plan = fields.Text()
    target_date = fields.Date()
    residual_likelihood = fields.Integer(default=1, required=True, tracking=True)
    residual_impact = fields.Integer(default=1, required=True, tracking=True)
    residual_score = fields.Integer(compute="_compute_scores", store=True)
    residual_level = fields.Selection(
        [("low", "Low"), ("moderate", "Moderate"), ("high", "High"), ("critical", "Critical")],
        compute="_compute_scores",
        store=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("assessed", "Assessed"),
            ("action_required", "Action Required"),
            ("monitoring", "Monitoring"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    assessment_date = fields.Date(readonly=True)
    assessor_id = fields.Many2one("res.users", readonly=True)
    review_date = fields.Date()
    last_review_date = fields.Date(readonly=True)
    closure_date = fields.Date(readonly=True)
    closed_by_id = fields.Many2one("res.users", readonly=True)
    closure_notes = fields.Text()
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    related_control_instance_ids = fields.Many2many(
        "pm.qms.control.instance",
        "pm_qms_risk_control_instance_rel",
        "risk_id",
        "control_instance_id",
        string="Related Control Instances",
    )
    related_document_ids = fields.Many2many(
        "pm.qms.document",
        "pm_qms_risk_document_rel",
        "risk_id",
        "document_id",
        string="Related Documents",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "pm_qms_risk_attachment_rel",
        "risk_id",
        "attachment_id",
        string="Attachments",
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Risk code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.risk") or "PM-RISK-00000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.depends("likelihood", "impact", "residual_likelihood", "residual_impact")
    def _compute_scores(self):
        for risk in self:
            risk.initial_score = risk.likelihood * risk.impact
            risk.residual_score = risk.residual_likelihood * risk.residual_impact
            risk.initial_level = risk._risk_level(risk.initial_score)
            risk.residual_level = risk._risk_level(risk.residual_score)

    def _risk_level(self, score):
        params = self.env["ir.config_parameter"].sudo()
        moderate = int(params.get_param("pm_qms_risk.threshold.moderate", "5"))
        high = int(params.get_param("pm_qms_risk.threshold.high", "10"))
        critical = int(params.get_param("pm_qms_risk.threshold.critical", "16"))
        if score >= critical:
            return "critical"
        if score >= high:
            return "high"
        if score >= moderate:
            return "moderate"
        return "low"

    @api.depends("target_date", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for risk in self:
            overdue = bool(risk.target_date and risk.state not in ("closed",) and risk.target_date < today)
            risk.is_overdue = overdue
            risk.days_overdue = (today - risk.target_date).days if overdue else 0

    @api.constrains("likelihood", "impact", "residual_likelihood", "residual_impact")
    def _check_score_bounds(self):
        for risk in self:
            values = [risk.likelihood, risk.impact, risk.residual_likelihood, risk.residual_impact]
            if any(value < 1 or value > 5 for value in values):
                raise ValidationError("Risk likelihood and impact values must be between 1 and 5.")

    @api.constrains("organization_id", "process_id")
    def _check_process_alignment(self):
        for risk in self:
            if risk.process_id.company_id != risk.company_id:
                raise ValidationError("Risk process must belong to the same company as the organization.")
            if risk.process_id.organization_id and risk.process_id.organization_id != risk.organization_id:
                raise ValidationError("Risk process must belong to the selected organization.")

    @api.constrains("related_control_instance_ids", "related_document_ids")
    def _check_related_records_alignment(self):
        for risk in self:
            if any(instance.company_id != risk.company_id for instance in risk.related_control_instance_ids):
                raise ValidationError("Related control instances must belong to the same company as the risk.")
            if any(instance.organization_id != risk.organization_id for instance in risk.related_control_instance_ids):
                raise ValidationError("Related control instances must belong to the same organization as the risk.")
            if any(document.company_id != risk.company_id for document in risk.related_document_ids):
                raise ValidationError("Related documents must belong to the same company as the risk.")
            if any(document.organization_id != risk.organization_id for document in risk.related_document_ids):
                raise ValidationError("Related documents must belong to the same organization as the risk.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can perform risk workflow actions.")

    def _transition(self, state, decision, event_type="workflow", notes=None, extra_values=None):
        self._check_manager_permission()
        for risk in self:
            previous = risk.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            risk.with_context(pm_qms_risk_workflow=True).write(values)
            risk._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=state,
                reviewer=self.env.user,
                approver=self.env.user if event_type in ("closure", "approval") else None,
                decision=decision,
                notes=notes,
            )

    def action_assess(self):
        self._transition(
            "assessed",
            "Risk assessed",
            extra_values={"assessment_date": fields.Date.context_today(self), "assessor_id": self.env.user.id},
        )

    def action_require_action(self):
        self._transition("action_required", "Risk response action required")

    def action_start_monitoring(self):
        self._transition("monitoring", "Risk moved to monitoring")

    def action_review(self):
        self._transition(
            "monitoring",
            "Risk reviewed",
            event_type="review",
            extra_values={"last_review_date": fields.Date.context_today(self)},
        )

    def action_close(self):
        self._check_manager_permission()
        for risk in self:
            if not risk.closure_notes:
                raise UserError("Closure notes are required before closing a risk or opportunity.")
        self._transition(
            "closed",
            "Risk closed",
            event_type="closure",
            notes="Closure notes retained on the record.",
            extra_values={"closure_date": fields.Date.context_today(self), "closed_by_id": self.env.user.id},
        )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_risk_workflow"):
            raise AccessError("Use risk workflow actions to change risk status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(risk.state != "draft" for risk in self):
            raise UserError("Only draft risks and opportunities can be deleted.")
        return super().unlink()
