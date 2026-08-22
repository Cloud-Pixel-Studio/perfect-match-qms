from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsCustomerComplaint(models.Model):
    _name = "pm.qms.customer.complaint"
    _description = "Perfect Match QMS Customer Complaint"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(string="Subject", required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        "res.company", related="organization_id.company_id", store=True, readonly=True, index=True
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True)
    customer_id = fields.Many2one("res.partner", required=True, ondelete="restrict", index=True, tracking=True)
    customer_contact_id = fields.Many2one("res.partner", ondelete="restrict")
    received_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    received_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, tracking=True)
    channel = fields.Selection(
        [("email", "Email"), ("phone", "Phone"), ("portal", "Portal"), ("customer_form", "Customer Form"), ("other", "Other")],
        default="email",
        required=True,
        tracking=True,
    )
    description = fields.Text(required=True)
    customer_reference = fields.Char(tracking=True)
    product_reference = fields.Char(string="Product / Part / Service Reference")
    order_reference = fields.Char(string="PO / Order Reference")
    lot_serial_reference = fields.Char(string="Lot / Serial / Shipment Reference")
    quantity_affected = fields.Float()
    unit_of_measure_text = fields.Char(string="Unit of Measure")
    severity = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
        required=True,
        tracking=True,
    )
    priority = fields.Selection(
        [("low", "Low"), ("normal", "Normal"), ("high", "High"), ("urgent", "Urgent")],
        default="normal",
        required=True,
        tracking=True,
    )
    owner_id = fields.Many2one("res.users", tracking=True)
    response_due_date = fields.Date(tracking=True)
    customer_response_date = fields.Date(tracking=True)
    customer_response_summary = fields.Text()
    response_owner_id = fields.Many2one("res.users")
    customer_acceptance = fields.Selection(
        [("pending", "Pending"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("not_required", "Not Required")],
        default="pending",
        required=True,
        tracking=True,
    )
    containment_required = fields.Boolean(default=False, tracking=True)
    containment_owner_id = fields.Many2one("res.users")
    containment_due_date = fields.Date()
    containment_action = fields.Text()
    containment_completion_date = fields.Date()
    containment_verification = fields.Text()
    containment_status = fields.Selection(
        [("not_required", "Not Required"), ("required", "Required"), ("in_progress", "In Progress"), ("complete", "Complete")],
        compute="_compute_containment_status",
        store=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("under_review", "Under Review"),
            ("containment", "Containment"),
            ("investigation", "Investigation"),
            ("corrective_action", "Corrective Action"),
            ("awaiting_customer", "Awaiting Customer"),
            ("effectiveness_review", "Effectiveness Review"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="new",
        required=True,
        tracking=True,
    )
    ncr_id = fields.Many2one("pm.qms.nonconformity", string="NCR", ondelete="restrict", tracking=True)
    capa_id = fields.Many2one("pm.qms.capa", string="CAPA", ondelete="restrict", tracking=True)
    eight_d_id = fields.Many2one("pm.qms.eight.d", string="8D Case", ondelete="restrict", tracking=True)
    root_cause_analysis_id = fields.Many2one("pm.qms.root.cause.analysis", ondelete="restrict")
    quality_alert_ids = fields.One2many("pm.qms.quality.alert", "complaint_id", string="Quality Alerts")
    related_document_ids = fields.Many2many(
        "pm.qms.document", "pm_qms_complaint_document_rel", "complaint_id", "document_id", string="Related Documents"
    )
    related_evidence_ids = fields.Many2many(
        "pm.qms.evidence", "pm_qms_complaint_evidence_rel", "complaint_id", "evidence_id", string="Related Evidence"
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", "pm_qms_complaint_attachment_rel", "complaint_id", "attachment_id", string="Attachments"
    )
    closure_notes = fields.Text()
    lessons_learned = fields.Text()
    is_response_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_response_overdue = fields.Integer(compute="_compute_overdue", store=True)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "Complaint code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.customer.complaint") or "CC-0000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.depends("containment_required", "containment_action", "containment_completion_date")
    def _compute_containment_status(self):
        for complaint in self:
            if not complaint.containment_required:
                complaint.containment_status = "not_required"
            elif complaint.containment_completion_date:
                complaint.containment_status = "complete"
            elif complaint.containment_action:
                complaint.containment_status = "in_progress"
            else:
                complaint.containment_status = "required"

    @api.depends("response_due_date", "customer_response_date", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for complaint in self:
            overdue = bool(
                complaint.response_due_date
                and not complaint.customer_response_date
                and complaint.state not in ("closed", "cancelled")
                and complaint.response_due_date < today
            )
            complaint.is_response_overdue = overdue
            complaint.days_response_overdue = (today - complaint.response_due_date).days if overdue else 0

    @api.constrains("organization_id", "process_id", "customer_id", "customer_contact_id")
    def _check_alignment(self):
        for complaint in self:
            if complaint.process_id.company_id != complaint.company_id:
                raise ValidationError("Complaint process must belong to the same company as the organization.")
            if complaint.process_id.organization_id and complaint.process_id.organization_id != complaint.organization_id:
                raise ValidationError("Complaint process must belong to the selected organization.")
            for partner in complaint.customer_id | complaint.customer_contact_id:
                if partner.company_id and partner.company_id != complaint.company_id:
                    raise ValidationError("Customer partners must belong to the complaint company or be shared.")

    @api.constrains("related_document_ids", "related_evidence_ids", "ncr_id", "capa_id")
    def _check_related_alignment(self):
        for complaint in self:
            for document in complaint.related_document_ids:
                if document.company_id != complaint.company_id or document.organization_id != complaint.organization_id:
                    raise ValidationError("Related documents must match the complaint company and organization.")
            for evidence in complaint.related_evidence_ids:
                if evidence.company_id != complaint.company_id or evidence.organization_id != complaint.organization_id:
                    raise ValidationError("Related evidence must match the complaint company and organization.")
            if complaint.ncr_id and (
                complaint.ncr_id.company_id != complaint.company_id or complaint.ncr_id.organization_id != complaint.organization_id
            ):
                raise ValidationError("Linked NCR must match the complaint company and organization.")
            if complaint.capa_id and (
                complaint.capa_id.company_id != complaint.company_id or complaint.capa_id.organization_id != complaint.organization_id
            ):
                raise ValidationError("Linked CAPA must match the complaint company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can perform customer quality workflow actions.")

    def _transition(self, state, decision, event_type="workflow", extra_values=None, require_manager=True):
        if require_manager:
            self._check_manager_permission()
        for complaint in self:
            previous = complaint.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            complaint.with_context(pm_qms_complaint_workflow=True).write(values)
            complaint._log_qms_event(event_type=event_type, previous_state=previous, new_state=state, reviewer=self.env.user if require_manager else None, decision=decision)

    def action_under_review(self):
        self._transition("under_review", "Complaint moved to review", require_manager=False)

    def action_start_containment(self):
        for complaint in self:
            if not complaint.containment_required:
                raise UserError("Containment must be required before moving the complaint to containment.")
        self._transition("containment", "Complaint containment started")

    def action_complete_containment(self):
        for complaint in self:
            if not complaint.containment_action:
                raise UserError("Containment action is required before completion.")
        self._transition(
            "investigation",
            "Complaint containment completed",
            event_type="review",
            extra_values={"containment_completion_date": fields.Date.context_today(self)},
        )

    def action_start_investigation(self):
        self._transition("investigation", "Complaint investigation started")

    def action_corrective_action(self):
        self._transition("corrective_action", "Complaint moved to corrective action")

    def action_await_customer(self):
        self._transition("awaiting_customer", "Complaint awaiting customer response")

    def action_record_customer_response(self):
        self._transition(
            "effectiveness_review",
            "Customer response recorded",
            event_type="review",
            extra_values={"customer_response_date": fields.Date.context_today(self), "response_owner_id": self.env.user.id},
        )

    def action_close(self):
        self._check_manager_permission()
        for complaint in self:
            if not complaint.closure_notes:
                raise UserError("Closure notes are required before closing a complaint.")
            if complaint.containment_required and not complaint.containment_completion_date:
                raise UserError("Required containment must be completed before closing a complaint.")
        self._transition("closed", "Complaint closed", event_type="closure")

    def action_cancel(self):
        self._transition("cancelled", "Complaint cancelled", event_type="closure")

    def _ncr_severity(self):
        self.ensure_one()
        return {"low": "minor", "medium": "minor", "high": "major", "critical": "critical"}[self.severity]

    def action_create_ncr(self):
        self.ensure_one()
        if self.ncr_id:
            return self.ncr_id.get_formview_action()
        ncr = self.env["pm.qms.nonconformity"].create(
            {
                "name": f"Customer complaint {self.code}: {self.name}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "customer",
                "severity": self._ncr_severity(),
                "description": self.description,
                "detected_date": self.received_date,
                "owner_id": self.owner_id.id,
                "target_date": self.response_due_date,
                "containment_required": self.containment_required,
                "containment_action": self.containment_action,
                "containment_owner_id": self.containment_owner_id.id,
                "customer_complaint_id": self.id,
                "related_document_ids": [(6, 0, self.related_document_ids.ids)],
                "related_evidence_ids": [(6, 0, self.related_evidence_ids.ids)],
            }
        )
        self.write({"ncr_id": ncr.id})
        self._log_qms_event(event_type="system", decision="NCR created from complaint", notes=ncr.code)
        return ncr.get_formview_action()

    def action_create_eight_d(self):
        self.ensure_one()
        if self.eight_d_id:
            return self.eight_d_id.get_formview_action()
        case = self.env["pm.qms.eight.d"].create(
            {
                "name": f"8D for {self.code}: {self.name}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "complaint",
                "complaint_id": self.id,
                "ncr_id": self.ncr_id.id,
                "customer_id": self.customer_id.id,
                "owner_id": self.owner_id.id,
                "problem_statement": self.description,
                "due_date": self.response_due_date,
            }
        )
        self.write({"eight_d_id": case.id})
        return case.get_formview_action()

    def action_create_quality_alert(self):
        self.ensure_one()
        alert = self.env["pm.qms.quality.alert"].create(
            {
                "name": f"Quality alert for {self.code}",
                "organization_id": self.organization_id.id,
                "description": self.containment_action or self.description,
                "complaint_id": self.id,
                "ncr_id": self.ncr_id.id,
                "owner_id": self.owner_id.id,
                "affected_reference": self.product_reference or self.lot_serial_reference,
            }
        )
        return alert.get_formview_action()

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_complaint_workflow"):
            raise AccessError("Use complaint workflow actions to change complaint status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(complaint.state != "new" for complaint in self):
            raise UserError("Only new complaints can be deleted.")
        return super().unlink()
