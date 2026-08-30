from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsScar(models.Model):
    _name = "pm.qms.scar"
    _description = "Perfect Match QMS Supplier Corrective Action Request"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one("res.company", related="organization_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True)
    supplier_id = fields.Many2one("res.partner", required=True, ondelete="restrict", index=True, tracking=True)
    supplier_issue_id = fields.Many2one("pm.qms.supplier.issue", ondelete="restrict")
    ncr_id = fields.Many2one("pm.qms.nonconformity", ondelete="restrict")
    capa_id = fields.Many2one("pm.qms.capa", ondelete="restrict")
    eight_d_id = fields.Many2one("pm.qms.eight.d", ondelete="restrict")
    issue_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    response_due_date = fields.Date(tracking=True)
    supplier_response_date = fields.Date(readonly=True)
    description = fields.Text(required=True)
    supplier_reference = fields.Char()
    owner_id = fields.Many2one("res.users", tracking=True)
    containment_required = fields.Boolean(default=True, tracking=True)
    supplier_containment = fields.Text()
    supplier_root_cause = fields.Text()
    supplier_corrective_action = fields.Text()
    internal_review_notes = fields.Text()
    effectiveness_review_date = fields.Date()
    effectiveness_result = fields.Selection(
        [("not_reviewed", "Not Reviewed"), ("effective", "Effective"), ("ineffective", "Ineffective")], default="not_reviewed", required=True, tracking=True
    )
    effectiveness_notes = fields.Text()
    response_line_ids = fields.One2many("pm.qms.scar.response", "scar_id", string="Supplier Response History")
    related_document_ids = fields.Many2many("pm.qms.document", "pm_qms_scar_document_rel", "scar_id", "document_id")
    related_evidence_ids = fields.Many2many("pm.qms.evidence", "pm_qms_scar_evidence_rel", "scar_id", "evidence_id")
    attachment_ids = fields.Many2many("ir.attachment", "pm_qms_scar_attachment_rel", "scar_id", "attachment_id")
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("response_received", "Response Received"),
            ("returned", "Returned for Revision"),
            ("accepted", "Accepted"),
            ("effectiveness_review", "Effectiveness Review"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "SCAR code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.scar") or "SCAR-0000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.depends("response_due_date", "supplier_response_date", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for scar in self:
            overdue = bool(
                scar.response_due_date
                and not scar.supplier_response_date
                and scar.state not in ("accepted", "closed", "cancelled")
                and scar.response_due_date < today
            )
            scar.is_overdue = overdue
            scar.days_overdue = (today - scar.response_due_date).days if overdue else 0

    @api.constrains("organization_id", "process_id", "supplier_id")
    def _check_alignment(self):
        for scar in self:
            if scar.process_id.company_id != scar.company_id:
                raise ValidationError("SCAR process must belong to the same company as the organization.")
            if scar.process_id.organization_id and scar.process_id.organization_id != scar.organization_id:
                raise ValidationError("SCAR process must belong to the selected organization.")
            if scar.supplier_id.company_id and scar.supplier_id.company_id != scar.company_id:
                raise ValidationError("SCAR supplier must belong to the same company or be shared.")

    @api.constrains("supplier_issue_id", "ncr_id", "capa_id", "eight_d_id", "related_document_ids", "related_evidence_ids")
    def _check_related_alignment(self):
        for scar in self:
            for sources in (scar.supplier_issue_id, scar.ncr_id, scar.capa_id, scar.eight_d_id, scar.related_document_ids, scar.related_evidence_ids):
                for source in sources:
                    if source.company_id != scar.company_id or source.organization_id != scar.organization_id:
                        raise ValidationError("SCAR related records must match the SCAR company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage SCAR workflow actions.")

    def _transition(self, state, decision, event_type="workflow", values=None):
        self._check_manager_permission()
        for scar in self:
            previous = scar.state
            payload = {"state": state}
            if values:
                payload.update(values)
            scar.with_context(pm_qms_scar_workflow=True).write(payload)
            scar._log_qms_event(event_type=event_type, previous_state=previous, new_state=state, reviewer=self.env.user, approver=self.env.user if event_type in ("closure", "effectiveness", "approval") else None, decision=decision)

    def action_issue(self):
        self._transition("issued", "SCAR issued")

    def action_record_response(self):
        for scar in self:
            if not (scar.supplier_containment or scar.supplier_root_cause or scar.supplier_corrective_action):
                raise UserError("Supplier response content is required before recording a SCAR response.")
            revision = len(scar.response_line_ids) + 1
            self.env["pm.qms.scar.response"].create(
                {
                    "scar_id": scar.id,
                    "revision": revision,
                    "response_date": fields.Date.context_today(scar),
                    "containment": scar.supplier_containment,
                    "root_cause": scar.supplier_root_cause,
                    "corrective_action": scar.supplier_corrective_action,
                    "submitted_by": scar.supplier_id.display_name,
                }
            )
            scar._transition(
                "response_received",
                "SCAR supplier response recorded",
                event_type="review",
                values={"supplier_response_date": fields.Date.context_today(scar)},
            )

    def action_return_for_revision(self):
        for scar in self:
            if not scar.internal_review_notes:
                raise UserError("Internal review notes are required before returning a SCAR.")
        self._transition("returned", "SCAR returned for supplier revision", event_type="review", values={"supplier_response_date": False})

    def action_accept_response(self):
        for scar in self:
            if not scar.internal_review_notes:
                raise UserError("Internal review notes are required before accepting a SCAR response.")
        self._transition("accepted", "SCAR response accepted", event_type="approval")

    def action_start_effectiveness(self):
        self._transition("effectiveness_review", "SCAR effectiveness review started", event_type="review")

    def action_mark_effective(self):
        for scar in self:
            if not scar.effectiveness_notes:
                raise UserError("Effectiveness notes are required before accepting SCAR effectiveness.")
        self._transition("effectiveness_review", "SCAR effectiveness accepted", event_type="effectiveness", values={"effectiveness_result": "effective"})

    def action_close(self):
        for scar in self:
            if scar.effectiveness_result != "effective":
                raise UserError("SCAR effectiveness must be accepted before closure.")
        self._transition("closed", "SCAR closed", event_type="closure")
        for scar in self.filtered("supplier_issue_id"):
            if scar.supplier_issue_id.state != "closed":
                scar.supplier_issue_id.with_context(pm_qms_supplier_issue_workflow=True).write({"state": "verification"})

    def action_cancel(self):
        self._transition("cancelled", "SCAR cancelled", event_type="closure")

    def action_create_capa(self):
        self.ensure_one()
        if self.capa_id:
            return self.capa_id.get_formview_action()
        capa = self.env["pm.qms.capa"].create(
            {
                "name": f"CAPA for {self.code}: {self.name}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "supplier_issue",
                "source_reference": self.code,
                "problem_statement": self.description,
                "root_cause": self.supplier_root_cause,
                "action_plan": self.supplier_corrective_action,
                "target_date": self.response_due_date,
                "scar_id": self.id,
            }
        )
        self.write({"capa_id": capa.id})
        if self.supplier_issue_id and not self.supplier_issue_id.capa_id:
            self.supplier_issue_id.write({"capa_id": capa.id})
        return capa.get_formview_action()

    def action_create_eight_d(self):
        self.ensure_one()
        if self.eight_d_id:
            return self.eight_d_id.get_formview_action()
        case = self.env["pm.qms.eight.d"].create(
            {
                "name": f"8D for {self.code}: {self.name}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "scar",
                "scar_id": self.id,
                "supplier_issue_id": self.supplier_issue_id.id,
                "ncr_id": self.ncr_id.id,
                "supplier_id": self.supplier_id.id,
                "owner_id": self.owner_id.id,
                "problem_statement": self.description,
                "due_date": self.response_due_date,
            }
        )
        self.write({"eight_d_id": case.id})
        return case.get_formview_action()

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_scar_workflow"):
            raise AccessError("Use SCAR workflow actions to change SCAR status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(scar.state != "draft" for scar in self):
            raise UserError("Only draft SCAR records can be deleted.")
        return super().unlink()


class PmQmsScarResponse(models.Model):
    _name = "pm.qms.scar.response"
    _description = "Perfect Match QMS SCAR Supplier Response"
    _order = "scar_id, revision desc, id desc"

    scar_id = fields.Many2one("pm.qms.scar", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="scar_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="scar_id.organization_id", store=True, readonly=True, index=True)
    revision = fields.Integer(required=True)
    response_date = fields.Date(required=True)
    submitted_by = fields.Char()
    containment = fields.Text()
    root_cause = fields.Text()
    corrective_action = fields.Text()
    review_result = fields.Selection([("pending", "Pending"), ("accepted", "Accepted"), ("returned", "Returned")], default="pending")
    review_notes = fields.Text()

    _scar_revision_uniq = models.Constraint("UNIQUE(scar_id, revision)", "SCAR response revision must be unique per SCAR.")

    def unlink(self):
        if any(response.scar_id.state not in ("draft", "issued", "returned") for response in self):
            raise UserError("SCAR response history is locked after internal acceptance starts.")
        return super().unlink()
