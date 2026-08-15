from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsObjective(models.Model):
    _name = "pm.qms.objective"
    _description = "Perfect Match QMS Objective"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "target_date, code, id"
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
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True, tracking=True)
    owner_id = fields.Many2one("res.users", tracking=True)
    active = fields.Boolean(default=True)

    description = fields.Text()
    purpose = fields.Text()
    date_start = fields.Date(required=True, tracking=True)
    target_date = fields.Date(required=True, tracking=True)
    review_date = fields.Date(tracking=True)
    baseline_value = fields.Float(tracking=True)
    baseline_date = fields.Date(tracking=True)
    target_value = fields.Float(required=True, tracking=True)
    target_operator = fields.Selection(
        [
            ("ge", ">="),
            ("le", "<="),
            ("eq", "="),
            ("gt", ">"),
            ("lt", "<"),
        ],
        default="ge",
        required=True,
        tracking=True,
    )
    unit_of_measure = fields.Char(required=True)
    auto_evaluation = fields.Boolean(
        string="Allow KPI Evaluation",
        help="When enabled, a manager may explicitly evaluate this objective from related KPI statuses.",
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("achieved", "Achieved"),
            ("not_achieved", "Not Achieved"),
            ("cancelled", "Cancelled"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    related_control_instance_ids = fields.Many2many(
        "pm.qms.control.instance",
        "pm_qms_objective_control_instance_rel",
        "objective_id",
        "control_instance_id",
        string="Related Control Instances",
    )
    kpi_ids = fields.Many2many(
        "pm.qms.kpi",
        "pm_qms_objective_kpi_rel",
        "objective_id",
        "kpi_id",
        string="KPIs",
    )
    related_risk_ids = fields.Many2many(
        "pm.qms.risk",
        "pm_qms_objective_risk_rel",
        "objective_id",
        "risk_id",
        string="Related Risks",
    )
    kpi_count = fields.Integer(compute="_compute_kpi_summary")
    kpi_on_target_count = fields.Integer(compute="_compute_kpi_summary")
    kpi_off_target_count = fields.Integer(compute="_compute_kpi_summary")
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Objective code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.objective") or "PM-OBJ-00000"
        return super().create(vals_list)

    @api.depends("target_date", "status")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for objective in self:
            overdue = bool(
                objective.target_date
                and objective.status in ("draft", "active", "not_achieved")
                and objective.target_date < today
            )
            objective.is_overdue = overdue
            objective.days_overdue = (today - objective.target_date).days if overdue else 0

    @api.depends("kpi_ids.latest_status")
    def _compute_kpi_summary(self):
        for objective in self:
            kpis = objective.kpi_ids
            objective.kpi_count = len(kpis)
            objective.kpi_on_target_count = len(kpis.filtered(lambda kpi: kpi.latest_status == "on_target"))
            objective.kpi_off_target_count = len(kpis.filtered(lambda kpi: kpi.latest_status == "off_target"))

    @api.constrains("date_start", "target_date", "baseline_date", "review_date")
    def _check_dates(self):
        for objective in self:
            if objective.date_start and objective.target_date and objective.target_date < objective.date_start:
                raise ValidationError("Objective target date cannot be before the start date.")
            if objective.baseline_date and objective.date_start and objective.baseline_date > objective.target_date:
                raise ValidationError("Objective baseline date cannot be after the target date.")

    @api.constrains("organization_id", "process_id")
    def _check_process_alignment(self):
        for objective in self:
            if objective.process_id.company_id != objective.company_id:
                raise ValidationError("Objective process must belong to the same company as the organization.")
            if objective.process_id.organization_id and objective.process_id.organization_id != objective.organization_id:
                raise ValidationError("Objective process must belong to the selected organization.")

    @api.constrains("related_control_instance_ids", "kpi_ids", "related_risk_ids")
    def _check_related_records_alignment(self):
        for objective in self:
            for instance in objective.related_control_instance_ids:
                if instance.company_id != objective.company_id or instance.organization_id != objective.organization_id:
                    raise ValidationError("Related control instances must match the objective company and organization.")
            for kpi in objective.kpi_ids:
                if kpi.company_id != objective.company_id or kpi.organization_id != objective.organization_id:
                    raise ValidationError("Related KPIs must match the objective company and organization.")
            for risk in objective.related_risk_ids:
                if risk.company_id != objective.company_id or risk.organization_id != objective.organization_id:
                    raise ValidationError("Related risks must match the objective company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage objective workflow.")

    def _transition(self, status, decision, event_type="workflow", extra_values=None):
        self._check_manager_permission()
        for objective in self:
            previous = objective.status
            values = {"status": status}
            if extra_values:
                values.update(extra_values)
            objective.with_context(pm_qms_objective_workflow=True).write(values)
            objective._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=status,
                reviewer=self.env.user,
                approver=self.env.user if event_type == "closure" else None,
                decision=decision,
            )

    def action_activate(self):
        self._transition("active", "Objective activated")

    def action_mark_achieved(self):
        self._transition("achieved", "Objective manually marked achieved")

    def action_mark_not_achieved(self):
        self._transition("not_achieved", "Objective manually marked not achieved")

    def action_evaluate_from_kpis(self):
        self._check_manager_permission()
        for objective in self:
            if not objective.auto_evaluation:
                raise UserError("Enable KPI evaluation before evaluating this objective from KPI results.")
            active_kpis = objective.kpi_ids.filtered(lambda kpi: kpi.status == "active")
            if not active_kpis:
                raise UserError("At least one active KPI is required for KPI-based objective evaluation.")
            if all(kpi.latest_status == "on_target" for kpi in active_kpis):
                objective._transition("achieved", "Objective evaluated from related KPIs", event_type="review")
            elif any(kpi.latest_status == "off_target" for kpi in active_kpis):
                objective._transition("not_achieved", "Objective evaluated from related KPIs", event_type="review")
            else:
                objective._transition("active", "Objective KPI evaluation retained active status", event_type="review")

    def action_close(self):
        self._transition("closed", "Objective closed", event_type="closure")

    def action_cancel(self):
        self._transition("cancelled", "Objective cancelled", event_type="closure")

    def write(self, vals):
        if "status" in vals and not self.env.context.get("pm_qms_objective_workflow"):
            raise AccessError("Use objective workflow actions to change objective status.")
        return super().write(vals)

    def unlink(self):
        if any(objective.status != "draft" for objective in self):
            raise UserError("Only draft objectives can be deleted.")
        return super().unlink()
