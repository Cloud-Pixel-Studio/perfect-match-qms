from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


QUALITY_COST_CATEGORIES = [
    ("prevention", "Prevention"),
    ("appraisal", "Appraisal"),
    ("internal_failure", "Internal Failure"),
    ("external_failure", "External Failure"),
]

COPQ_CATEGORIES = {"internal_failure", "external_failure"}


class PmQmsCostType(models.Model):
    _name = "pm.qms.cost.type"
    _description = "Perfect Match QMS Cost Type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "category, code, name"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    category = fields.Selection(QUALITY_COST_CATEGORIES, required=True, tracking=True)
    description = fields.Text()
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "Cost type code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.cost.type") or "PM-CQT-0000"
        return super().create(vals_list)


class PmQmsCostEvent(models.Model):
    _name = "pm.qms.cost.event"
    _description = "Perfect Match QMS Cost of Quality Event"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "event_date desc, code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="organization_id.company_id", store=True, readonly=True, index=True)
    process_id = fields.Many2one("pm.qms.process", ondelete="restrict", index=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)
    event_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        default="draft",
        required=True,
        tracking=True,
    )
    source_model = fields.Selection(selection="_selection_source_models", tracking=True)
    source_id = fields.Integer(tracking=True)
    source_identifier = fields.Char(readonly=True)
    source_title = fields.Char(readonly=True)
    notes = fields.Text()
    correction_of_id = fields.Many2one("pm.qms.cost.event", ondelete="restrict", readonly=True)
    correction_event_ids = fields.One2many("pm.qms.cost.event", "correction_of_id", string="Correction Events")
    line_ids = fields.One2many("pm.qms.cost.line", "event_id", string="Cost Lines")
    quality_cost_total = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    recovery_total = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    net_quality_cost = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    prevention_total = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    appraisal_total = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    internal_failure_total = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    external_failure_total = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    copq_amount = fields.Monetary(compute="_compute_amounts", store=True, currency_field="currency_id")
    line_count = fields.Integer(compute="_compute_amounts", store=True)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "Cost event code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.cost.event") or "PM-CQ-00000"
        records = super().create(vals_list)
        records._sync_source_snapshot()
        return records

    @api.depends("line_ids.amount", "line_ids.recovery_amount", "line_ids.category")
    def _compute_amounts(self):
        for event in self:
            totals = {key: 0.0 for key, _label in QUALITY_COST_CATEGORIES}
            recovery = 0.0
            for line in event.line_ids:
                totals[line.category] += line.amount
                recovery += line.recovery_amount
            event.quality_cost_total = sum(totals.values())
            event.recovery_total = recovery
            event.net_quality_cost = event.quality_cost_total - recovery
            event.prevention_total = totals["prevention"]
            event.appraisal_total = totals["appraisal"]
            event.internal_failure_total = totals["internal_failure"]
            event.external_failure_total = totals["external_failure"]
            event.copq_amount = totals["internal_failure"] + totals["external_failure"]
            event.line_count = len(event.line_ids)

    @api.constrains("organization_id", "process_id", "source_model", "source_id", "correction_of_id")
    def _check_alignment(self):
        for event in self:
            if event.process_id:
                if event.process_id.company_id != event.company_id:
                    raise ValidationError("Cost event process must belong to the same company as the organization.")
                if event.process_id.organization_id and event.process_id.organization_id != event.organization_id:
                    raise ValidationError("Cost event process must belong to the selected organization.")
            source = event._source_record_or_false()
            if source:
                if "company_id" in source._fields and source.company_id and source.company_id != event.company_id:
                    raise ValidationError("Cost event source must match the event company.")
                if "organization_id" in source._fields and source.organization_id and source.organization_id != event.organization_id:
                    raise ValidationError("Cost event source must match the event organization.")
            if event.correction_of_id and event.correction_of_id.company_id != event.company_id:
                raise ValidationError("Correction events must remain in the same company.")

    @api.constrains("line_ids")
    def _check_confirm_ready(self):
        for event in self:
            if event.state == "confirmed" and not event.line_ids:
                raise ValidationError("Confirmed cost events must include at least one cost line.")

    def action_confirm(self):
        self._check_manager_permission()
        for event in self:
            if not event.line_ids:
                raise UserError("Add at least one cost line before confirming the cost event.")
            event._sync_source_snapshot()
            event.with_context(pm_qms_cost_event_workflow=True).write({"state": "confirmed"})
            event._log_qms_event(event_type="approval", previous_state="draft", new_state="confirmed", reviewer=self.env.user, decision="Cost event confirmed")

    def action_cancel(self):
        self._check_manager_permission()
        self.with_context(pm_qms_cost_event_workflow=True).write({"state": "cancelled"})

    def action_create_correction(self):
        self.ensure_one()
        if self.state != "confirmed":
            raise UserError("Only confirmed cost events need correction events.")
        correction = self.copy({"name": f"Correction for {self.code}", "state": "draft", "correction_of_id": self.id})
        correction.line_ids.unlink()
        return correction.get_formview_action()

    def action_open_source(self):
        self.ensure_one()
        source = self._source_record_or_false()
        if not source:
            raise UserError("No readable source record is linked to this cost event.")
        source.check_access("read")
        return {"type": "ir.actions.act_window", "name": source.display_name, "res_model": source._name, "res_id": source.id, "view_mode": "form", "target": "current"}

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage Cost of Quality workflow.")

    def _sync_source_snapshot(self):
        for event in self:
            source = event._source_record_or_false()
            values = {"source_identifier": False, "source_title": False}
            if source:
                values["source_identifier"] = source["code"] if "code" in source._fields else source.display_name
                values["source_title"] = source["name"] if "name" in source._fields else source.display_name
            if values["source_identifier"] != event.source_identifier or values["source_title"] != event.source_title:
                event.with_context(pm_qms_cost_source_snapshot=True).write(values)

    def _source_record_or_false(self):
        self.ensure_one()
        if not self.source_model or not self.source_id:
            return False
        allowed = {value for value, _label in self._selection_source_models()}
        if self.source_model not in allowed or self.source_model not in self.env:
            raise ValidationError("Cost event source model is not allowed.")
        return self.env[self.source_model].browse(self.source_id).exists()

    @api.model
    def _selection_source_models(self):
        return [
            ("pm.qms.nonconformity", "NCR"),
            ("pm.qms.capa", "CAPA"),
            ("pm.qms.capa.action", "CAPA Action"),
            ("pm.qms.audit.finding", "Audit Finding"),
            ("pm.qms.calibration.impact.assessment", "Calibration Impact Assessment"),
            ("pm.qms.customer.complaint", "Customer Complaint"),
            ("pm.qms.eight.d", "8D"),
            ("pm.qms.supplier.issue", "Supplier Issue"),
            ("pm.qms.scar", "SCAR"),
        ]

    def write(self, vals):
        locked = {"organization_id", "process_id", "event_date", "source_model", "source_id", "line_ids"}
        if vals and any(event.state == "confirmed" for event in self) and locked.intersection(vals) and not self.env.context.get("pm_qms_cost_source_snapshot"):
            raise AccessError("Confirmed cost events are immutable. Create a correction event instead.")
        if "state" in vals and not self.env.context.get("pm_qms_cost_event_workflow"):
            raise AccessError("Use Cost of Quality workflow actions to change state.")
        result = super().write(vals)
        if {"source_model", "source_id"}.intersection(vals):
            self._sync_source_snapshot()
        return result

    def unlink(self):
        if any(event.state == "confirmed" for event in self):
            raise UserError("Confirmed cost events cannot be deleted; cancel drafts or create correction events.")
        return super().unlink()


class PmQmsCostLine(models.Model):
    _name = "pm.qms.cost.line"
    _description = "Perfect Match QMS Cost of Quality Line"
    _order = "event_id, id"

    event_id = fields.Many2one("pm.qms.cost.event", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="event_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="event_id.organization_id", store=True, readonly=True, index=True)
    currency_id = fields.Many2one(related="event_id.currency_id", store=True, readonly=True)
    cost_type_id = fields.Many2one("pm.qms.cost.type", required=True, ondelete="restrict", index=True)
    category = fields.Selection(related="cost_type_id.category", store=True, readonly=True)
    description = fields.Char(required=True)
    amount = fields.Monetary(required=True, default=0.0, currency_field="currency_id")
    recovery_amount = fields.Monetary(default=0.0, currency_field="currency_id")
    net_amount = fields.Monetary(compute="_compute_net_amount", store=True, currency_field="currency_id")
    is_estimated = fields.Boolean(string="Estimated")
    notes = fields.Text()

    @api.depends("amount", "recovery_amount")
    def _compute_net_amount(self):
        for line in self:
            line.net_amount = line.amount - line.recovery_amount

    @api.constrains("amount", "recovery_amount", "cost_type_id")
    def _check_values(self):
        for line in self:
            if line.amount < 0 or line.recovery_amount < 0:
                raise ValidationError("Cost and recovery amounts must be zero or positive.")
            if line.cost_type_id.company_id != line.company_id:
                raise ValidationError("Cost line type must belong to the same company as the cost event.")

    def _check_event_editable(self):
        if any(line.event_id.state == "confirmed" for line in self):
            raise AccessError("Lines on confirmed cost events are immutable. Create a correction event instead.")

    def write(self, vals):
        if vals:
            self._check_event_editable()
        return super().write(vals)

    def unlink(self):
        self._check_event_editable()
        return super().unlink()
