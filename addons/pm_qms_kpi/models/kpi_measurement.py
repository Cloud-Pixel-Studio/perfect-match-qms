from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsKpiMeasurement(models.Model):
    _name = "pm.qms.kpi.measurement"
    _description = "Perfect Match QMS KPI Measurement"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "measurement_date desc, period_end desc, id desc"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True)
    kpi_id = fields.Many2one("pm.qms.kpi", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="kpi_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one(
        "pm.qms.organization",
        related="kpi_id.organization_id",
        store=True,
        readonly=True,
        index=True,
    )
    measurement_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    period_start = fields.Date(required=True, tracking=True)
    period_end = fields.Date(required=True, tracking=True)
    value = fields.Float(required=True, tracking=True)
    target_value_snapshot = fields.Float(required=True, readonly=True)
    warning_value_snapshot = fields.Float(readonly=True)
    direction_snapshot = fields.Selection(
        [
            ("higher_is_better", "Higher Is Better"),
            ("lower_is_better", "Lower Is Better"),
            ("target_range", "Target Range"),
        ],
        required=True,
        readonly=True,
    )
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
    status = fields.Selection(
        [
            ("on_target", "On Target"),
            ("warning", "Warning"),
            ("off_target", "Off Target"),
            ("not_evaluated", "Not Evaluated"),
        ],
        compute="_compute_status",
        store=True,
    )
    notes = fields.Text()
    recorded_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    recorded_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    verified_by_id = fields.Many2one("res.users", readonly=True)
    verification_date = fields.Datetime(readonly=True)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            kpi = self.env["pm.qms.kpi"].browse(vals["kpi_id"])
            vals.setdefault("target_value_snapshot", kpi.target_value)
            vals.setdefault("warning_value_snapshot", kpi.warning_value)
            vals.setdefault("direction_snapshot", kpi.direction)
            vals.setdefault("source_type", kpi.source_type)
        records = super().create(vals_list)
        return records

    @api.depends("kpi_id.code", "period_start", "period_end")
    def _compute_name(self):
        for measurement in self:
            if measurement.kpi_id and measurement.period_start and measurement.period_end:
                measurement.name = f"{measurement.kpi_id.code}: {measurement.period_start} - {measurement.period_end}"
            else:
                measurement.name = "KPI Measurement"

    @api.depends("value", "target_value_snapshot", "warning_value_snapshot", "direction_snapshot")
    def _compute_status(self):
        for measurement in self:
            measurement.status = measurement._evaluate_status()

    def _evaluate_status(self):
        self.ensure_one()
        value = self.value
        target = self.target_value_snapshot
        warning = self.warning_value_snapshot
        if self.direction_snapshot == "higher_is_better":
            if value >= target:
                return "on_target"
            if warning and value >= warning:
                return "warning"
            return "off_target"
        if self.direction_snapshot == "lower_is_better":
            if value <= target:
                return "on_target"
            if warning and value <= warning:
                return "warning"
            return "off_target"
        if warning:
            lower = min(target, warning)
            upper = max(target, warning)
            return "on_target" if lower <= value <= upper else "off_target"
        return "on_target" if value == target else "off_target"

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for measurement in self:
            if measurement.period_end < measurement.period_start:
                raise ValidationError("Measurement period end cannot be before period start.")

    @api.constrains("kpi_id", "period_start", "period_end")
    def _check_unique_period(self):
        for measurement in self:
            duplicate = self.search(
                [
                    ("id", "!=", measurement.id),
                    ("kpi_id", "=", measurement.kpi_id.id),
                    ("period_start", "=", measurement.period_start),
                    ("period_end", "=", measurement.period_end),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError("Only one KPI measurement is allowed for the same KPI and period.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can verify KPI measurements.")

    def action_verify(self):
        self._check_manager_permission()
        for measurement in self:
            previous = "unverified"
            measurement.with_context(pm_qms_kpi_measurement_verify=True).write(
                {"verified_by_id": self.env.user.id, "verification_date": fields.Datetime.now()}
            )
            measurement._log_qms_event(
                event_type="review",
                previous_state=previous,
                new_state="verified",
                reviewer=self.env.user,
                decision="KPI measurement verified",
            )

    def write(self, vals):
        protected = {"target_value_snapshot", "warning_value_snapshot", "direction_snapshot"}
        if protected.intersection(vals) and not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
            raise AccessError("Only QMS Administrators can correct historical KPI snapshots.")
        measured_fields = {"kpi_id", "measurement_date", "period_start", "period_end", "value", "source_type"}
        if measured_fields.intersection(vals) and any(measurement.verified_by_id for measurement in self):
            if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
                raise AccessError("Only QMS Administrators can correct verified KPI measurements.")
        return super().write(vals)

    def unlink(self):
        if any(measurement.verified_by_id for measurement in self):
            raise UserError("Verified KPI measurements cannot be deleted.")
        return super().unlink()
