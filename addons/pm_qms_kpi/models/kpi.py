from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsKpi(models.Model):
    _name = "pm.qms.kpi"
    _description = "Perfect Match QMS KPI"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code, id"
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
    calculation_description = fields.Text()
    unit_of_measure = fields.Char(required=True)
    direction = fields.Selection(
        [
            ("higher_is_better", "Higher Is Better"),
            ("lower_is_better", "Lower Is Better"),
            ("target_range", "Target Range"),
        ],
        default="higher_is_better",
        required=True,
        tracking=True,
    )
    target_value = fields.Float(required=True, tracking=True)
    warning_value = fields.Float(tracking=True)
    frequency = fields.Selection(
        [
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
            ("quarterly", "Quarterly"),
            ("semiannual", "Semiannual"),
            ("annual", "Annual"),
            ("manual", "Manual"),
        ],
        default="monthly",
        required=True,
        tracking=True,
    )
    start_date = fields.Date(required=True, tracking=True)
    next_measurement_date = fields.Date(compute="_compute_next_measurement_date", store=True)
    source_type = fields.Selection(
        [
            ("manual", "Manual"),
            ("system_calculated", "System Calculated"),
            ("integration", "Integration"),
        ],
        default="manual",
        required=True,
        tracking=True,
    )
    objective_ids = fields.Many2many(
        "pm.qms.objective",
        "pm_qms_objective_kpi_rel",
        "kpi_id",
        "objective_id",
        string="Objectives",
    )
    control_instance_ids = fields.Many2many(
        "pm.qms.control.instance",
        "pm_qms_kpi_control_instance_rel",
        "kpi_id",
        "control_instance_id",
        string="Control Instances",
    )
    measurement_ids = fields.One2many("pm.qms.kpi.measurement", "kpi_id", string="Measurements")
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("inactive", "Inactive"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    latest_value = fields.Float(compute="_compute_measurement_summary", store=True)
    latest_measurement_date = fields.Date(compute="_compute_measurement_summary", store=True)
    latest_status = fields.Selection(
        [
            ("on_target", "On Target"),
            ("warning", "Warning"),
            ("off_target", "Off Target"),
            ("not_evaluated", "Not Evaluated"),
        ],
        compute="_compute_measurement_summary",
        store=True,
    )
    previous_value = fields.Float(compute="_compute_measurement_summary", store=True)
    trend_direction = fields.Selection(
        [
            ("improving", "Improving"),
            ("stable", "Stable"),
            ("declining", "Declining"),
            ("insufficient_data", "Insufficient Data"),
        ],
        compute="_compute_measurement_summary",
        store=True,
    )
    measurement_count = fields.Integer(compute="_compute_measurement_summary", store=True)
    measurement_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "KPI code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.kpi") or "PM-KPI-00000"
        return super().create(vals_list)

    @api.depends(
        "measurement_ids.active",
        "measurement_ids.value",
        "measurement_ids.status",
        "measurement_ids.measurement_date",
        "measurement_ids.period_end",
    )
    def _compute_measurement_summary(self):
        for kpi in self:
            measurements = kpi.measurement_ids.filtered(lambda measurement: measurement.active).sorted(
                key=lambda measurement: (
                    measurement.measurement_date or fields.Date.from_string("1900-01-01"),
                    measurement.period_end or fields.Date.from_string("1900-01-01"),
                    measurement.id,
                ),
                reverse=True,
            )
            kpi.measurement_count = len(measurements)
            if not measurements:
                kpi.latest_value = 0.0
                kpi.previous_value = 0.0
                kpi.latest_measurement_date = False
                kpi.latest_status = "not_evaluated"
                kpi.trend_direction = "insufficient_data"
                continue
            latest = measurements[0]
            previous = measurements[1] if len(measurements) > 1 else False
            kpi.latest_value = latest.value
            kpi.latest_measurement_date = latest.measurement_date
            kpi.latest_status = latest.status
            kpi.previous_value = previous.value if previous else 0.0
            kpi.trend_direction = kpi._trend_from_measurements(latest, previous)

    def _trend_from_measurements(self, latest, previous):
        self.ensure_one()
        if not previous:
            return "insufficient_data"
        if latest.status in ("on_target", "warning", "off_target") or previous.status in (
            "on_target",
            "warning",
            "off_target",
        ):
            score = {"off_target": 0, "warning": 1, "on_target": 2, "not_evaluated": -1}
            if score.get(latest.status, -1) > score.get(previous.status, -1):
                return "improving"
            if score.get(latest.status, -1) < score.get(previous.status, -1):
                return "declining"
        if self.direction == "higher_is_better":
            if latest.value > previous.value:
                return "improving"
            if latest.value < previous.value:
                return "declining"
        elif self.direction == "lower_is_better":
            if latest.value < previous.value:
                return "improving"
            if latest.value > previous.value:
                return "declining"
        else:
            latest_distance = abs(latest.value - latest.target_value_snapshot)
            previous_distance = abs(previous.value - previous.target_value_snapshot)
            if latest_distance < previous_distance:
                return "improving"
            if latest_distance > previous_distance:
                return "declining"
        return "stable"

    @api.depends("status", "next_measurement_date")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for kpi in self:
            overdue = bool(kpi.status == "active" and kpi.next_measurement_date and kpi.next_measurement_date < today)
            kpi.measurement_overdue = overdue
            kpi.days_overdue = (today - kpi.next_measurement_date).days if overdue else 0

    @api.depends(
        "frequency",
        "start_date",
        "measurement_ids.active",
        "measurement_ids.period_end",
        "measurement_ids.measurement_date",
    )
    def _compute_next_measurement_date(self):
        for kpi in self:
            if kpi.frequency == "manual":
                kpi.next_measurement_date = False
                continue
            latest = kpi.measurement_ids.filtered(lambda measurement: measurement.active).sorted(
                key=lambda measurement: (measurement.period_end, measurement.measurement_date, measurement.id),
                reverse=True,
            )[:1]
            anchor = latest.period_end if latest else kpi.start_date
            kpi.next_measurement_date = kpi._next_date_after(anchor) if anchor else False

    @api.constrains("organization_id", "process_id")
    def _check_process_alignment(self):
        for kpi in self:
            if kpi.process_id.company_id != kpi.company_id:
                raise ValidationError("KPI process must belong to the same company as the organization.")
            if kpi.process_id.organization_id and kpi.process_id.organization_id != kpi.organization_id:
                raise ValidationError("KPI process must belong to the selected organization.")

    @api.constrains("objective_ids", "control_instance_ids")
    def _check_related_records_alignment(self):
        for kpi in self:
            for objective in kpi.objective_ids:
                if objective.company_id != kpi.company_id or objective.organization_id != kpi.organization_id:
                    raise ValidationError("Related objectives must match the KPI company and organization.")
            for instance in kpi.control_instance_ids:
                if instance.company_id != kpi.company_id or instance.organization_id != kpi.organization_id:
                    raise ValidationError("Related control instances must match the KPI company and organization.")

    @api.constrains("direction", "target_value", "warning_value")
    def _check_target_configuration(self):
        for kpi in self:
            if kpi.direction == "higher_is_better" and kpi.warning_value and kpi.warning_value > kpi.target_value:
                raise ValidationError("For higher-is-better KPIs, warning value should not exceed target value.")
            if kpi.direction == "lower_is_better" and kpi.warning_value and kpi.warning_value < kpi.target_value:
                raise ValidationError("For lower-is-better KPIs, warning value should not be below target value.")

    def _next_date_after(self, anchor_date):
        self.ensure_one()
        if not anchor_date or self.frequency == "manual":
            return False
        increments = {
            "daily": relativedelta(days=1),
            "weekly": relativedelta(weeks=1),
            "monthly": relativedelta(months=1),
            "quarterly": relativedelta(months=3),
            "semiannual": relativedelta(months=6),
            "annual": relativedelta(years=1),
        }
        return anchor_date + increments[self.frequency]

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage KPI configuration.")

    def _transition(self, status, decision, event_type="workflow"):
        self._check_manager_permission()
        for kpi in self:
            previous = kpi.status
            kpi.with_context(pm_qms_kpi_workflow=True).write({"status": status})
            kpi._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=status,
                reviewer=self.env.user,
                approver=self.env.user if event_type == "closure" else None,
                decision=decision,
            )

    def action_activate(self):
        self._transition("active", "KPI activated")

    def action_deactivate(self):
        self._transition("inactive", "KPI deactivated")

    def action_reset_to_draft(self):
        self._transition("draft", "KPI reset to draft")

    def write(self, vals):
        if "status" in vals and not self.env.context.get("pm_qms_kpi_workflow"):
            raise AccessError("Use KPI workflow actions to change KPI status.")
        tracked_target_keys = {"target_value", "warning_value", "direction"}
        should_log_target = bool(tracked_target_keys.intersection(vals))
        previous = {
            kpi.id: f"{kpi.direction}:{kpi.target_value}:{kpi.warning_value}"
            for kpi in self
        } if should_log_target else {}
        result = super().write(vals)
        if should_log_target:
            for kpi in self:
                kpi._log_qms_event(
                    event_type="system",
                    previous_state=previous[kpi.id],
                    new_state=f"{kpi.direction}:{kpi.target_value}:{kpi.warning_value}",
                    decision="KPI target configuration changed",
                )
        return result

    def unlink(self):
        if any(kpi.status != "draft" for kpi in self):
            raise UserError("Only draft KPIs can be deleted.")
        return super().unlink()
