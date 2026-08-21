from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsCalibrationEvent(models.Model):
    _name = "pm.qms.calibration.event"
    _description = "Perfect Match QMS Calibration / Verification Event"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "calibration_date desc, code desc, id desc"
    _rec_name = "code"

    code = fields.Char(default="New", required=True, copy=False, tracking=True, string="Event Number")
    equipment_id = fields.Many2one("pm.qms.equipment", required=True, ondelete="restrict", index=True, tracking=True)
    organization_id = fields.Many2one(related="equipment_id.organization_id", store=True, readonly=True, index=True)
    company_id = fields.Many2one(related="equipment_id.company_id", store=True, readonly=True, index=True)
    event_type = fields.Selection(
        [("calibration", "Calibration"), ("verification", "Verification")],
        default="calibration",
        required=True,
        tracking=True,
    )
    date_sent = fields.Date(string="Date Sent / Started")
    calibration_date = fields.Date(string="Calibration / Completion Date", tracking=True)
    strategy = fields.Selection(
        [("internal", "Internal"), ("external", "External")],
        default="external",
        required=True,
        tracking=True,
    )
    technician_person_id = fields.Many2one("pm.qms.person", string="Technician", ondelete="restrict")
    provider_id = fields.Many2one("pm.qms.calibration.provider", ondelete="restrict")
    method = fields.Char()
    certificate_number = fields.Char()
    certificate_attachment_id = fields.Many2one("ir.attachment", ondelete="restrict")
    related_evidence_ids = fields.Many2many(
        "pm.qms.evidence",
        "pm_qms_cal_event_evidence_rel",
        "event_id",
        "evidence_id",
        string="Related Evidence",
    )
    result = fields.Selection(
        [
            ("pass", "Pass"),
            ("conditional", "Conditional"),
            ("fail", "Fail"),
            ("out_of_tolerance", "Out of Tolerance"),
        ],
        required=True,
        default="pass",
        tracking=True,
    )
    as_found_condition = fields.Text()
    as_left_condition = fields.Text()
    notes = fields.Text()
    next_due_date = fields.Date()
    reviewed_by_id = fields.Many2one("res.users", readonly=True)
    review_date = fields.Date(readonly=True)
    impact_assessment_id = fields.Many2one("pm.qms.calibration.impact.assessment", readonly=True)
    ncr_id = fields.Many2one(related="impact_assessment_id.ncr_id", store=True, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("awaiting_review", "Awaiting Review"),
            ("accepted", "Accepted"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    measurement_line_ids = fields.One2many("pm.qms.calibration.measurement.line", "event_id", string="Measurements")
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Calibration event number must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.calibration.event") or "PM-CAL-00000"
            if vals.get("equipment_id"):
                equipment = self.env["pm.qms.equipment"].browse(vals["equipment_id"])
                vals.setdefault("strategy", equipment.calibration_strategy)
                vals.setdefault("provider_id", equipment.default_provider_id.id)
                vals.setdefault("method", equipment.calibration_method)
        records = super().create(vals_list)
        records._sync_certificate_attachment()
        return records

    @api.onchange("equipment_id", "calibration_date")
    def _onchange_schedule_defaults(self):
        for event in self:
            if event.equipment_id:
                event.strategy = event.strategy or event.equipment_id.calibration_strategy
                event.provider_id = event.provider_id or event.equipment_id.default_provider_id
                event.method = event.method or event.equipment_id.calibration_method
            if event.equipment_id and event.calibration_date and not event.next_due_date:
                event.next_due_date = event.equipment_id._add_interval(event.calibration_date)

    @api.constrains("equipment_id", "technician_person_id", "provider_id", "related_evidence_ids", "calibration_date", "date_sent", "next_due_date")
    def _check_alignment_and_dates(self):
        for event in self:
            if event.technician_person_id and event.technician_person_id.company_id != event.company_id:
                raise ValidationError("Technician must belong to the same company as the equipment.")
            if event.provider_id and event.provider_id.company_id != event.company_id:
                raise ValidationError("Provider must belong to the same company as the equipment.")
            for evidence in event.related_evidence_ids:
                if evidence.company_id != event.company_id or evidence.organization_id != event.organization_id:
                    raise ValidationError("Related evidence must match the calibration event company and organization.")
            if event.date_sent and event.calibration_date and event.calibration_date < event.date_sent:
                raise ValidationError("Completion date cannot be before the sent/started date.")
            if event.calibration_date and event.next_due_date and event.next_due_date <= event.calibration_date:
                raise ValidationError("Next due date must be after the calibration or verification date.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can review calibration records.")

    def action_start(self):
        previous = {event.id: event.state for event in self}
        self.with_context(pm_qms_calibration_workflow=True).write({"state": "in_progress"})
        self.mapped("equipment_id").action_mark_out_for_calibration()
        for event in self:
            event._log_qms_event("workflow", previous[event.id], "in_progress", decision="Calibration event started")

    def action_submit_review(self):
        previous = {event.id: event.state for event in self}
        self.with_context(pm_qms_calibration_workflow=True).write({"state": "awaiting_review"})
        for event in self:
            event._log_qms_event("workflow", previous[event.id], "awaiting_review", decision="Calibration event submitted")

    def action_accept(self):
        self._check_manager_permission()
        today = fields.Date.context_today(self)
        previous = {event.id: event.state for event in self}
        for event in self:
            if not event.calibration_date:
                raise UserError("Calibration or completion date is required before accepting the event.")
            if event.result in ("pass", "conditional") and not event.next_due_date and event.equipment_id.calibration_required:
                event.next_due_date = event.equipment_id._add_interval(event.calibration_date)
        self.with_context(pm_qms_calibration_workflow=True).write(
            {"state": "accepted", "reviewed_by_id": self.env.user.id, "review_date": today}
        )
        for event in self:
            if event.result in ("pass", "conditional"):
                if event.equipment_id.lifecycle_state != "retired":
                    event.equipment_id.write({"lifecycle_state": "in_service"})
            else:
                assessment = event._ensure_impact_assessment()
                event.write({"impact_assessment_id": assessment.id})
                event.equipment_id.action_quarantine()
            event._sync_certificate_attachment()
            event._log_qms_event("approval", previous[event.id], "accepted", reviewer=self.env.user, decision="Calibration event accepted")

    def action_cancel(self):
        self._check_manager_permission()
        previous = {event.id: event.state for event in self}
        self.with_context(pm_qms_calibration_workflow=True).write({"state": "cancelled"})
        for event in self:
            event._log_qms_event("closure", previous[event.id], "cancelled", reviewer=self.env.user, decision="Calibration event cancelled")

    def _ensure_impact_assessment(self):
        self.ensure_one()
        assessment = self.impact_assessment_id or self.env["pm.qms.calibration.impact.assessment"].search(
            [("event_id", "=", self.id), ("state", "!=", "cancelled")],
            limit=1,
        )
        if assessment:
            return assessment
        previous_accepted = self.equipment_id.event_ids.filtered(
            lambda event: event.id != self.id
            and event.state == "accepted"
            and event.result in ("pass", "conditional")
            and event.calibration_date
            and event.calibration_date <= self.calibration_date
        ).sorted(lambda event: (event.calibration_date, event.id), reverse=True)[:1]
        return self.env["pm.qms.calibration.impact.assessment"].create(
            {
                "equipment_id": self.equipment_id.id,
                "event_id": self.id,
                "last_acceptable_event_id": previous_accepted.id,
                "exposure_start": previous_accepted.calibration_date if previous_accepted else False,
                "exposure_end": self.calibration_date,
                "used_during_exposure": "unknown",
                "impact_conclusion": "unknown",
            }
        )

    def _sync_certificate_attachment(self):
        for event in self:
            attachment = event.certificate_attachment_id
            if attachment and (not attachment.res_model or (attachment.res_model == event._name and attachment.res_id in (0, event.id))):
                attachment.write({"res_model": event._name, "res_id": event.id})

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_calibration_workflow"):
            raise AccessError("Use calibration workflow actions to change event status.")
        locked = {"equipment_id", "result", "calibration_date", "next_due_date", "measurement_line_ids"}
        if locked.intersection(vals) and any(event.state == "accepted" for event in self):
            if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
                raise AccessError("Only QMS Administrators can correct accepted calibration history.")
        result = super().write(vals)
        if "certificate_attachment_id" in vals:
            self._sync_certificate_attachment()
        return result


class PmQmsCalibrationMeasurementLine(models.Model):
    _name = "pm.qms.calibration.measurement.line"
    _description = "Perfect Match QMS Calibration Measurement Line"
    _order = "event_id, sequence, id"

    event_id = fields.Many2one("pm.qms.calibration.event", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="event_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="event_id.organization_id", store=True, readonly=True, index=True)
    parameter = fields.Char(required=True)
    nominal_value = fields.Char()
    lower_limit = fields.Char()
    upper_limit = fields.Char()
    as_found_value = fields.Char()
    as_left_value = fields.Char()
    result = fields.Selection(
        [("pass", "Pass"), ("fail", "Fail"), ("not_evaluated", "Not Evaluated")],
        default="not_evaluated",
        required=True,
    )
    notes = fields.Text()
