from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsSupplierIssue(models.Model):
    _name = "pm.qms.supplier.issue"
    _description = "Perfect Match QMS Supplier Issue"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one("res.company", related="organization_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True)
    supplier_id = fields.Many2one("res.partner", required=True, ondelete="restrict", index=True, tracking=True)
    issue_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    description = fields.Text(required=True)
    supplier_reference = fields.Char()
    purchase_reference = fields.Char(string="Supplier PO / Order Reference")
    product_reference = fields.Char(string="Product / Part / Service Reference")
    lot_serial_reference = fields.Char(string="Lot / Serial / Shipment Reference")
    quantity_affected = fields.Float()
    severity = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="medium", required=True, tracking=True
    )
    owner_id = fields.Many2one("res.users", tracking=True)
    containment_required = fields.Boolean(default=False, tracking=True)
    containment_action = fields.Text()
    containment_owner_id = fields.Many2one("res.users")
    containment_due_date = fields.Date()
    containment_completed_date = fields.Date()
    scar_required = fields.Boolean(default=False, tracking=True)
    ncr_id = fields.Many2one("pm.qms.nonconformity", ondelete="restrict", tracking=True)
    capa_id = fields.Many2one("pm.qms.capa", ondelete="restrict", tracking=True)
    eight_d_id = fields.Many2one("pm.qms.eight.d", ondelete="restrict", tracking=True)
    scar_id = fields.Many2one("pm.qms.scar", ondelete="restrict", tracking=True)
    root_cause_analysis_id = fields.Many2one("pm.qms.root.cause.analysis", ondelete="restrict")
    related_document_ids = fields.Many2many("pm.qms.document", "pm_qms_supplier_issue_document_rel", "issue_id", "document_id")
    related_evidence_ids = fields.Many2many("pm.qms.evidence", "pm_qms_supplier_issue_evidence_rel", "issue_id", "evidence_id")
    attachment_ids = fields.Many2many("ir.attachment", "pm_qms_supplier_issue_attachment_rel", "issue_id", "attachment_id")
    state = fields.Selection(
        [("new", "New"), ("review", "Review"), ("containment", "Containment"), ("scar", "SCAR"), ("verification", "Verification"), ("closed", "Closed"), ("cancelled", "Cancelled")],
        default="new",
        required=True,
        tracking=True,
    )
    closure_notes = fields.Text()
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "Supplier issue code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.supplier.issue") or "SI-0000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.constrains("organization_id", "process_id", "supplier_id")
    def _check_alignment(self):
        for issue in self:
            if issue.process_id.company_id != issue.company_id:
                raise ValidationError("Supplier issue process must belong to the same company as the organization.")
            if issue.process_id.organization_id and issue.process_id.organization_id != issue.organization_id:
                raise ValidationError("Supplier issue process must belong to the selected organization.")
            if issue.supplier_id.company_id and issue.supplier_id.company_id != issue.company_id:
                raise ValidationError("Supplier partner must belong to the same company or be shared.")

    @api.constrains("related_document_ids", "related_evidence_ids", "ncr_id", "capa_id")
    def _check_related_alignment(self):
        for issue in self:
            for sources in (issue.related_document_ids, issue.related_evidence_ids, issue.ncr_id, issue.capa_id):
                for source in sources:
                    if source.company_id != issue.company_id or source.organization_id != issue.organization_id:
                        raise ValidationError("Supplier issue related records must match the issue company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage supplier issue workflow actions.")

    def _transition(self, state, decision, event_type="workflow", values=None):
        self._check_manager_permission()
        for issue in self:
            previous = issue.state
            payload = {"state": state}
            if values:
                payload.update(values)
            issue.with_context(pm_qms_supplier_issue_workflow=True).write(payload)
            issue._log_qms_event(event_type=event_type, previous_state=previous, new_state=state, reviewer=self.env.user, decision=decision)

    def action_review(self):
        self._transition("review", "Supplier issue review started")

    def action_start_containment(self):
        for issue in self:
            if not issue.containment_required:
                raise UserError("Containment must be required before starting containment.")
        self._transition("containment", "Supplier issue containment started")

    def action_complete_containment(self):
        self._transition("review", "Supplier containment completed", event_type="review", values={"containment_completed_date": fields.Date.context_today(self)})

    def action_move_to_scar(self):
        self._transition("scar", "Supplier issue moved to SCAR")

    def action_start_verification(self):
        self._transition("verification", "Supplier issue verification started", event_type="review")

    def action_close(self):
        for issue in self:
            if not issue.closure_notes:
                raise UserError("Closure notes are required before closing a supplier issue.")
        self._transition("closed", "Supplier issue closed", event_type="closure")

    def action_cancel(self):
        self._transition("cancelled", "Supplier issue cancelled", event_type="closure")

    def _ncr_severity(self):
        self.ensure_one()
        return {"low": "minor", "medium": "minor", "high": "major", "critical": "critical"}[self.severity]

    def action_create_ncr(self):
        self.ensure_one()
        if self.ncr_id:
            return self.ncr_id.get_formview_action()
        ncr = self.env["pm.qms.nonconformity"].create(
            {
                "name": f"Supplier issue {self.code}: {self.name}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "supplier",
                "severity": self._ncr_severity(),
                "description": self.description,
                "detected_date": self.issue_date,
                "owner_id": self.owner_id.id,
                "containment_required": self.containment_required,
                "containment_action": self.containment_action,
                "containment_owner_id": self.containment_owner_id.id,
                "supplier_issue_id": self.id,
                "related_document_ids": [(6, 0, self.related_document_ids.ids)],
                "related_evidence_ids": [(6, 0, self.related_evidence_ids.ids)],
            }
        )
        self.write({"ncr_id": ncr.id})
        return ncr.get_formview_action()

    def action_create_scar(self):
        self.ensure_one()
        if self.scar_id:
            return self.scar_id.get_formview_action()
        scar = self.env["pm.qms.scar"].create(
            {
                "name": f"SCAR for {self.code}: {self.name}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "supplier_id": self.supplier_id.id,
                "supplier_issue_id": self.id,
                "ncr_id": self.ncr_id.id,
                "issue_date": self.issue_date,
                "description": self.description,
                "supplier_reference": self.supplier_reference,
                "owner_id": self.owner_id.id,
                "containment_required": self.containment_required,
            }
        )
        self.write({"scar_required": True, "scar_id": scar.id})
        return scar.get_formview_action()

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_supplier_issue_workflow"):
            raise AccessError("Use supplier issue workflow actions to change status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(issue.state != "new" for issue in self):
            raise UserError("Only new supplier issues can be deleted.")
        return super().unlink()
