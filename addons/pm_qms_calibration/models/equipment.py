from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsEquipmentType(models.Model):
    _name = "pm.qms.equipment.type"
    _description = "Perfect Match QMS Monitoring Resource Type"
    _order = "name, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True, copy=False)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    description = fields.Text()
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Monitoring resource type code must be unique per company.",
    )


class PmQmsCalibrationProvider(models.Model):
    _name = "pm.qms.calibration.provider"
    _description = "Perfect Match QMS Calibration Provider"
    _order = "name, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True, copy=False)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    partner_id = fields.Many2one("res.partner", string="Business Contact", ondelete="restrict")
    scope = fields.Text()
    qualification_reference = fields.Char()
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Calibration provider code must be unique per company.",
    )


class PmQmsEquipment(models.Model):
    _name = "pm.qms.equipment"
    _description = "Perfect Match QMS Monitoring and Measuring Resource"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code, name"
    _rec_name = "code"

    code = fields.Char(default="New", required=True, copy=False, tracking=True, string="Equipment / Gage ID")
    name = fields.Char(required=True, tracking=True)
    type_id = fields.Many2one("pm.qms.equipment.type", string="Type / Category", ondelete="restrict", tracking=True)
    manufacturer = fields.Char()
    model = fields.Char()
    serial_number = fields.Char()
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="organization_id.company_id", store=True, readonly=True, index=True)
    process_id = fields.Many2one("pm.qms.process", ondelete="restrict", index=True)
    location = fields.Char()
    responsible_person_id = fields.Many2one("pm.qms.person", ondelete="restrict", tracking=True)
    lifecycle_state = fields.Selection(
        [
            ("in_service", "In Service"),
            ("out_for_calibration", "Out for Calibration"),
            ("quarantined", "Quarantined"),
            ("out_of_service", "Out of Service"),
            ("retired", "Retired"),
        ],
        default="in_service",
        required=True,
        tracking=True,
    )
    purpose = fields.Text()
    calibration_required = fields.Boolean(default=True, tracking=True)
    verification_required = fields.Boolean(default=False, tracking=True)
    calibration_method = fields.Char()
    calibration_strategy = fields.Selection(
        [("internal", "Internal"), ("external", "External")],
        default="external",
        required=True,
        tracking=True,
    )
    default_provider_id = fields.Many2one("pm.qms.calibration.provider", ondelete="restrict")
    frequency_interval = fields.Integer(default=12, string="Frequency")
    frequency_unit = fields.Selection(
        [("days", "Days"), ("months", "Months"), ("years", "Years")],
        default="months",
        required=True,
    )
    due_soon_days = fields.Integer(default=30)
    last_event_id = fields.Many2one("pm.qms.calibration.event", compute="_compute_event_rollup", store=True)
    last_calibration_date = fields.Date(compute="_compute_event_rollup", store=True)
    next_due_date = fields.Date(compute="_compute_event_rollup", store=True)
    calibration_status = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("no_history", "No Accepted History"),
            ("current", "Current"),
            ("due_soon", "Due Soon"),
            ("due", "Due"),
            ("overdue", "Overdue"),
            ("out_for_calibration", "Out for Calibration"),
            ("quarantined", "Quarantined"),
            ("retired", "Retired"),
        ],
        compute="_compute_calibration_status",
        string="Calibration Status",
    )
    acceptance_criteria = fields.Text()
    notes = fields.Text()
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "pm_qms_equipment_attachment_rel",
        "equipment_id",
        "attachment_id",
        string="Attachments",
    )
    document_ids = fields.Many2many(
        "pm.qms.document",
        "pm_qms_equipment_document_rel",
        "equipment_id",
        "document_id",
        string="Controlled Documents",
    )
    event_ids = fields.One2many("pm.qms.calibration.event", "equipment_id", string="Calibration / Verification Events")
    impact_assessment_ids = fields.One2many("pm.qms.calibration.impact.assessment", "equipment_id")
    open_impact_assessment_count = fields.Integer(compute="_compute_attention_counts")
    overdue_event_count = fields.Integer(compute="_compute_attention_counts")
    active = fields.Boolean(default=True)

    _code_organization_uniq = models.Constraint(
        "UNIQUE(code, organization_id)",
        "Equipment / gage ID must be unique per organization.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            organization = self.env["pm.qms.organization"].browse(vals.get("organization_id")).exists()
            if vals.get("code") and vals["code"] != "New" and organization:
                duplicate = self.sudo().search(
                    [
                        ("code", "=", vals["code"]),
                        ("organization_id", "=", organization.id),
                    ],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError("Equipment / gage ID must be unique per organization.")
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.equipment") or "PM-EQ-00000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.depends("event_ids.state", "event_ids.result", "event_ids.calibration_date", "event_ids.next_due_date")
    def _compute_event_rollup(self):
        for equipment in self:
            accepted = equipment.event_ids.filtered(
                lambda event: event.state == "accepted" and event.result in ("pass", "conditional")
            ).sorted(lambda event: (event.calibration_date or fields.Date.to_date("1900-01-01"), event.id), reverse=True)
            event = accepted[:1]
            equipment.last_event_id = event
            equipment.last_calibration_date = event.calibration_date if event else False
            equipment.next_due_date = event.next_due_date if event else False

    @api.depends("calibration_required", "next_due_date", "lifecycle_state")
    def _compute_calibration_status(self):
        today = fields.Date.context_today(self)
        for equipment in self:
            if equipment.lifecycle_state in ("quarantined", "out_for_calibration", "retired"):
                equipment.calibration_status = equipment.lifecycle_state
            elif not equipment.calibration_required:
                equipment.calibration_status = "not_required"
            elif not equipment.next_due_date:
                equipment.calibration_status = "no_history"
            elif equipment.next_due_date < today:
                equipment.calibration_status = "overdue"
            elif equipment.next_due_date == today:
                equipment.calibration_status = "due"
            elif equipment.next_due_date <= today + relativedelta(days=equipment.due_soon_days or 0):
                equipment.calibration_status = "due_soon"
            else:
                equipment.calibration_status = "current"

    def _compute_attention_counts(self):
        today = fields.Date.context_today(self)
        for equipment in self:
            equipment.open_impact_assessment_count = len(
                equipment.impact_assessment_ids.filtered(lambda item: item.state not in ("closed", "cancelled"))
            )
            equipment.overdue_event_count = 1 if equipment.calibration_required and equipment.next_due_date and equipment.next_due_date < today else 0

    @api.constrains("frequency_interval", "due_soon_days")
    def _check_intervals(self):
        for equipment in self:
            if equipment.frequency_interval < 1:
                raise ValidationError("Calibration frequency must be at least 1.")
            if equipment.due_soon_days < 0:
                raise ValidationError("Due-soon threshold cannot be negative.")

    @api.constrains("organization_id", "process_id", "type_id", "responsible_person_id", "default_provider_id", "document_ids")
    def _check_alignment(self):
        for equipment in self:
            if equipment.process_id:
                if equipment.process_id.company_id != equipment.company_id:
                    raise ValidationError("Equipment process must belong to the same company.")
                if equipment.process_id.organization_id and equipment.process_id.organization_id != equipment.organization_id:
                    raise ValidationError("Equipment process must belong to the selected organization.")
            if equipment.type_id and equipment.type_id.company_id != equipment.company_id:
                raise ValidationError("Equipment type must belong to the same company.")
            if equipment.responsible_person_id and equipment.responsible_person_id.company_id != equipment.company_id:
                raise ValidationError("Responsible person must belong to the same company.")
            if equipment.default_provider_id and equipment.default_provider_id.company_id != equipment.company_id:
                raise ValidationError("Calibration provider must belong to the same company.")
            for document in equipment.document_ids:
                if document.company_id != equipment.company_id or document.organization_id != equipment.organization_id:
                    raise ValidationError("Related documents must match the equipment company and organization.")

    def _add_interval(self, start_date):
        self.ensure_one()
        if self.frequency_unit == "days":
            return start_date + relativedelta(days=self.frequency_interval)
        if self.frequency_unit == "years":
            return start_date + relativedelta(years=self.frequency_interval)
        return start_date + relativedelta(months=self.frequency_interval)

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage equipment status.")

    def action_mark_out_for_calibration(self):
        self._check_manager_permission()
        previous = {record.id: record.lifecycle_state for record in self}
        self.write({"lifecycle_state": "out_for_calibration"})
        for record in self:
            record._log_qms_event("workflow", previous[record.id], "out_for_calibration", decision="Equipment sent for calibration")

    def action_quarantine(self):
        self._check_manager_permission()
        previous = {record.id: record.lifecycle_state for record in self}
        self.write({"lifecycle_state": "quarantined"})
        for record in self:
            record._log_qms_event("workflow", previous[record.id], "quarantined", decision="Equipment quarantined")

    def action_return_to_service(self):
        self._check_manager_permission()
        for equipment in self:
            if equipment.open_impact_assessment_count:
                raise UserError("Close related impact assessments before returning equipment to service.")
            if equipment.last_event_id and equipment.last_event_id.result not in ("pass", "conditional"):
                raise UserError("A passing or conditional calibration/verification event is required before return to service.")
        previous = {record.id: record.lifecycle_state for record in self}
        self.write({"lifecycle_state": "in_service"})
        for record in self:
            record._log_qms_event("workflow", previous[record.id], "in_service", decision="Equipment returned to service")

    def action_schedule_due_activities(self):
        for equipment in self:
            equipment._ensure_due_activity()

    def _ensure_due_activity(self):
        self.ensure_one()
        if not self.calibration_required or not self.next_due_date or self.lifecycle_state in ("retired", "quarantined"):
            return False
        today = fields.Date.context_today(self)
        if self.next_due_date > today + relativedelta(days=self.due_soon_days or 0):
            return False
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        model = self.env["ir.model"]._get(self._name)
        existing = self.env["mail.activity"].search(
            [
                ("res_model_id", "=", model.id),
                ("res_id", "=", self.id),
                ("activity_type_id", "=", activity_type.id),
                ("summary", "=", "Calibration due"),
            ],
            limit=1,
        )
        if existing:
            return existing
        user = self.responsible_person_id.user_id or self.env.user
        return self.activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline=self.next_due_date,
            user_id=user.id,
            summary="Calibration due",
            note="Review this monitoring resource calibration or verification before continued use.",
        )

    def write(self, vals):
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def action_view_events(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("pm_qms_calibration.action_pm_qms_calibration_event")
        action["domain"] = [("equipment_id", "=", self.id)]
        action["context"] = {"default_equipment_id": self.id}
        return action

    def action_view_impact_assessments(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("pm_qms_calibration.action_pm_qms_calibration_impact_assessment")
        action["domain"] = [("equipment_id", "=", self.id)]
        action["context"] = {"default_equipment_id": self.id}
        return action
