from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsNonconformity(models.Model):
    _name = "pm.qms.nonconformity"
    _description = "Perfect Match QMS Nonconformity"
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
    source_type = fields.Selection(
        [
            ("internal", "Internal"),
            ("customer", "Customer"),
            ("supplier", "Supplier"),
            ("process", "Process"),
            ("product", "Product"),
            ("document", "Document"),
            ("audit", "Audit"),
            ("other", "Other"),
        ],
        default="internal",
        required=True,
        tracking=True,
    )
    description = fields.Text(required=True)
    detected_date = fields.Date(default=fields.Date.context_today, required=True)
    detected_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, string="Detected By")
    owner_id = fields.Many2one("res.users", tracking=True)
    severity = fields.Selection(
        [("minor", "Minor"), ("major", "Major"), ("critical", "Critical")],
        default="minor",
        required=True,
        tracking=True,
    )
    containment_required = fields.Boolean(default=False)
    containment_action = fields.Text()
    containment_owner_id = fields.Many2one("res.users", string="Containment Owner")
    containment_date = fields.Date()
    containment_completed = fields.Boolean(default=False)
    disposition = fields.Selection(
        [
            ("use_as_is", "Use As Is"),
            ("rework", "Rework"),
            ("repair", "Repair"),
            ("return", "Return"),
            ("scrap", "Scrap"),
            ("information_only", "Information Only"),
            ("other", "Other"),
        ],
    )
    disposition_notes = fields.Text()
    root_cause_summary = fields.Text()
    target_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("open", "Open"),
            ("containment", "Containment"),
            ("investigation", "Investigation"),
            ("action_required", "Action Required"),
            ("verification", "Verification"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    opened_by_id = fields.Many2one("res.users", readonly=True)
    opened_on = fields.Datetime(readonly=True)
    reviewed_by_id = fields.Many2one("res.users", readonly=True)
    reviewed_on = fields.Datetime(readonly=True)
    closed_by_id = fields.Many2one("res.users", readonly=True)
    closed_on = fields.Datetime(readonly=True)
    closure_notes = fields.Text()
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    related_control_instance_ids = fields.Many2many(
        "pm.qms.control.instance",
        "pm_qms_ncr_control_instance_rel",
        "nonconformity_id",
        "control_instance_id",
        string="Related Control Instances",
    )
    related_document_ids = fields.Many2many(
        "pm.qms.document",
        "pm_qms_ncr_document_rel",
        "nonconformity_id",
        "document_id",
        string="Related Documents",
    )
    related_evidence_ids = fields.Many2many(
        "pm.qms.evidence",
        "pm_qms_ncr_evidence_rel",
        "nonconformity_id",
        "evidence_id",
        string="Related Evidence",
    )
    related_risk_ids = fields.Many2many(
        "pm.qms.risk",
        "pm_qms_ncr_risk_rel",
        "nonconformity_id",
        "risk_id",
        string="Related Risks",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "pm_qms_ncr_attachment_rel",
        "nonconformity_id",
        "attachment_id",
        string="Attachments",
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "NCR code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.nonconformity") or "PM-NCR-00000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.depends("target_date", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for ncr in self:
            overdue = bool(ncr.target_date and ncr.state not in ("closed", "cancelled") and ncr.target_date < today)
            ncr.is_overdue = overdue
            ncr.days_overdue = (today - ncr.target_date).days if overdue else 0

    @api.constrains("organization_id", "process_id")
    def _check_process_alignment(self):
        for ncr in self:
            if ncr.process_id.company_id != ncr.company_id:
                raise ValidationError("NCR process must belong to the same company as the organization.")
            if ncr.process_id.organization_id and ncr.process_id.organization_id != ncr.organization_id:
                raise ValidationError("NCR process must belong to the selected organization.")

    @api.constrains(
        "related_control_instance_ids",
        "related_document_ids",
        "related_evidence_ids",
        "related_risk_ids",
    )
    def _check_related_records_alignment(self):
        for ncr in self:
            for instance in ncr.related_control_instance_ids:
                if instance.company_id != ncr.company_id or instance.organization_id != ncr.organization_id:
                    raise ValidationError("Related control instances must match the NCR company and organization.")
            for document in ncr.related_document_ids:
                if document.company_id != ncr.company_id or document.organization_id != ncr.organization_id:
                    raise ValidationError("Related documents must match the NCR company and organization.")
            for evidence in ncr.related_evidence_ids:
                if evidence.company_id != ncr.company_id or evidence.organization_id != ncr.organization_id:
                    raise ValidationError("Related evidence must match the NCR company and organization.")
            for risk in ncr.related_risk_ids:
                if risk.company_id != ncr.company_id or risk.organization_id != ncr.organization_id:
                    raise ValidationError("Related risks must match the NCR company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can perform NCR review and closure actions.")

    def _transition(self, state, decision, event_type="workflow", notes=None, extra_values=None, require_manager=True):
        if require_manager:
            self._check_manager_permission()
        for ncr in self:
            previous = ncr.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            ncr.with_context(pm_qms_ncr_workflow=True).write(values)
            ncr._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=state,
                reviewer=self.env.user if require_manager else None,
                approver=self.env.user if event_type == "closure" else None,
                decision=decision,
                notes=notes,
            )

    def action_open(self):
        self._transition(
            "open",
            "NCR opened",
            extra_values={"opened_by_id": self.env.user.id, "opened_on": fields.Datetime.now()},
            require_manager=False,
        )

    def action_start_containment(self):
        for ncr in self:
            if not ncr.containment_required:
                raise UserError("Containment must be required before moving the NCR to containment.")
        self._transition("containment", "NCR containment started")

    def action_start_investigation(self):
        for ncr in self:
            if ncr.containment_required and not ncr.containment_completed:
                raise UserError("Required containment must be completed before investigation.")
        self._transition(
            "investigation",
            "NCR investigation started",
            event_type="review",
            extra_values={"reviewed_by_id": self.env.user.id, "reviewed_on": fields.Datetime.now()},
        )

    def action_require_action(self):
        self._transition("action_required", "NCR requires corrective action")

    def action_start_verification(self):
        self._transition(
            "verification",
            "NCR moved to verification",
            event_type="review",
            extra_values={"reviewed_by_id": self.env.user.id, "reviewed_on": fields.Datetime.now()},
        )

    def action_close(self):
        self._check_manager_permission()
        for ncr in self:
            if not ncr.closure_notes:
                raise UserError("Closure notes are required before closing an NCR.")
            if ncr.containment_required and not ncr.containment_completed:
                raise UserError("Required containment must be complete before closing an NCR.")
        self._transition(
            "closed",
            "NCR closed",
            event_type="closure",
            notes="Closure notes retained on the record.",
            extra_values={"closed_by_id": self.env.user.id, "closed_on": fields.Datetime.now()},
        )

    def action_cancel(self):
        self._transition("cancelled", "NCR cancelled", event_type="closure")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_ncr_workflow"):
            raise AccessError("Use NCR workflow actions to change NCR status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(ncr.state != "draft" for ncr in self):
            raise UserError("Only draft NCR records can be deleted.")
        return super().unlink()
