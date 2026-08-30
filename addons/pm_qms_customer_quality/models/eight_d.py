from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsEightD(models.Model):
    _name = "pm.qms.eight.d"
    _description = "Perfect Match QMS 8D Case"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one("res.company", related="organization_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True)
    source_type = fields.Selection(
        [("complaint", "Customer Complaint"), ("ncr", "NCR"), ("supplier_issue", "Supplier Issue"), ("scar", "SCAR"), ("other", "Other")],
        default="other",
        required=True,
        tracking=True,
    )
    complaint_id = fields.Many2one("pm.qms.customer.complaint", ondelete="restrict")
    ncr_id = fields.Many2one("pm.qms.nonconformity", ondelete="restrict")
    supplier_issue_id = fields.Many2one("pm.qms.supplier.issue", ondelete="restrict")
    scar_id = fields.Many2one("pm.qms.scar", ondelete="restrict")
    customer_id = fields.Many2one("res.partner", ondelete="restrict")
    supplier_id = fields.Many2one("res.partner", ondelete="restrict")
    owner_id = fields.Many2one("res.users", tracking=True)
    due_date = fields.Date(tracking=True)
    closed_date = fields.Date(readonly=True)
    problem_statement = fields.Text(required=True)
    team_person_ids = fields.Many2many("pm.qms.person", "pm_qms_8d_person_rel", "eight_d_id", "person_id", string="8D Team")
    root_cause_analysis_id = fields.Many2one("pm.qms.root.cause.analysis", ondelete="restrict")
    capa_ids = fields.Many2many("pm.qms.capa", "pm_qms_8d_capa_rel", "eight_d_id", "capa_id", string="CAPA Records")
    related_document_ids = fields.Many2many("pm.qms.document", "pm_qms_8d_document_rel", "eight_d_id", "document_id")
    related_evidence_ids = fields.Many2many("pm.qms.evidence", "pm_qms_8d_evidence_rel", "eight_d_id", "evidence_id")
    attachment_ids = fields.Many2many("ir.attachment", "pm_qms_8d_attachment_rel", "eight_d_id", "attachment_id")
    d0_preparation = fields.Text(string="D0 Preparation / Emergency Response")
    d1_team = fields.Text(string="D1 Team")
    d2_problem_description = fields.Text(string="D2 Problem Description")
    d3_containment = fields.Text(string="D3 Interim Containment")
    d4_root_cause = fields.Text(string="D4 Root Cause")
    d5_corrective_action = fields.Text(string="D5 Corrective Action Selection")
    d6_implementation = fields.Text(string="D6 Implementation")
    d7_prevention = fields.Text(string="D7 Prevention / Systemic Actions")
    d8_closure = fields.Text(string="D8 Closure / Team Recognition")
    lessons_learned = fields.Text()
    effectiveness_review_date = fields.Date()
    effectiveness_result = fields.Selection(
        [("not_reviewed", "Not Reviewed"), ("effective", "Effective"), ("ineffective", "Ineffective")],
        default="not_reviewed",
        required=True,
        tracking=True,
    )
    effectiveness_notes = fields.Text()
    progress_percent = fields.Float(compute="_compute_progress", digits=(16, 2))
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("capa", "CAPA"), ("effectiveness_review", "Effectiveness Review"), ("closed", "Closed"), ("cancelled", "Cancelled")],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "8D code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.eight.d") or "8D-0000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.depends("due_date", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for case in self:
            overdue = bool(case.due_date and case.state not in ("closed", "cancelled") and case.due_date < today)
            case.is_overdue = overdue
            case.days_overdue = (today - case.due_date).days if overdue else 0

    @api.depends(
        "d0_preparation", "d1_team", "d2_problem_description", "d3_containment", "d4_root_cause",
        "d5_corrective_action", "d6_implementation", "d7_prevention", "d8_closure", "root_cause_analysis_id", "capa_ids",
    )
    def _compute_progress(self):
        fields_to_check = [
            "d0_preparation", "d1_team", "d2_problem_description", "d3_containment", "d4_root_cause",
            "d5_corrective_action", "d6_implementation", "d7_prevention", "d8_closure",
        ]
        for case in self:
            completed = sum(1 for name in fields_to_check if case[name])
            if case.root_cause_analysis_id:
                completed += 1
            if case.capa_ids:
                completed += 1
            case.progress_percent = completed / 11.0 * 100.0

    @api.constrains("organization_id", "process_id", "customer_id", "supplier_id")
    def _check_alignment(self):
        for case in self:
            if case.process_id.company_id != case.company_id:
                raise ValidationError("8D process must belong to the same company as the organization.")
            if case.process_id.organization_id and case.process_id.organization_id != case.organization_id:
                raise ValidationError("8D process must belong to the selected organization.")
            for partner in case.customer_id | case.supplier_id:
                if partner.company_id and partner.company_id != case.company_id:
                    raise ValidationError("8D partners must belong to the same company or be shared.")

    @api.constrains("complaint_id", "ncr_id", "supplier_issue_id", "scar_id", "capa_ids", "related_document_ids", "related_evidence_ids")
    def _check_related_alignment(self):
        for case in self:
            for sources in (case.complaint_id, case.ncr_id, case.supplier_issue_id, case.scar_id, case.capa_ids, case.related_document_ids, case.related_evidence_ids):
                for source in sources:
                    if source.company_id != case.company_id or source.organization_id != case.organization_id:
                        raise ValidationError("8D related records must match the case company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage 8D workflow actions.")

    def _transition(self, state, decision, event_type="workflow", values=None):
        self._check_manager_permission()
        for case in self:
            previous = case.state
            payload = {"state": state}
            if values:
                payload.update(values)
            case.with_context(pm_qms_8d_workflow=True).write(payload)
            case._log_qms_event(event_type=event_type, previous_state=previous, new_state=state, reviewer=self.env.user, approver=self.env.user if event_type in ("closure", "effectiveness") else None, decision=decision)

    def action_start(self):
        self._transition("active", "8D started")

    def action_move_to_capa(self):
        self._transition("capa", "8D moved to CAPA planning")

    def action_start_effectiveness(self):
        self._transition("effectiveness_review", "8D effectiveness review started", event_type="review")

    def action_mark_effective(self):
        for case in self:
            if not case.effectiveness_notes:
                raise UserError("Effectiveness notes are required before accepting an 8D.")
        self._transition("effectiveness_review", "8D effectiveness accepted", event_type="effectiveness", values={"effectiveness_result": "effective"})

    def action_close(self):
        for case in self:
            if case.effectiveness_result != "effective":
                raise UserError("8D effectiveness must be accepted before closure.")
            if not case.d8_closure:
                raise UserError("D8 closure notes are required before closing an 8D.")
        self._transition("closed", "8D closed", event_type="closure", values={"closed_date": fields.Date.context_today(self)})

    def action_cancel(self):
        self._transition("cancelled", "8D cancelled", event_type="closure")

    def action_create_root_cause(self):
        self.ensure_one()
        if self.root_cause_analysis_id:
            return self.root_cause_analysis_id.get_formview_action()
        analysis = self.env["pm.qms.root.cause.analysis"].create(
            {
                "name": f"Root cause for {self.code}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "problem_statement": self.problem_statement,
                "eight_d_id": self.id,
                "complaint_id": self.complaint_id.id,
                "ncr_id": self.ncr_id.id,
                "supplier_issue_id": self.supplier_issue_id.id,
                "scar_id": self.scar_id.id,
            }
        )
        self.write({"root_cause_analysis_id": analysis.id})
        return analysis.get_formview_action()

    def action_create_capa(self):
        self.ensure_one()
        existing = self.capa_ids[:1]
        if existing:
            return existing.get_formview_action()
        capa_source_values = self._get_capa_source_values()
        capa_values = {
            "name": f"CAPA for {self.code}: {self.name}",
            "organization_id": self.organization_id.id,
            "process_id": self.process_id.id,
            "source_reference": self.code,
            "problem_statement": self.problem_statement,
            "root_cause": self.root_cause_analysis_id.root_cause or self.d4_root_cause,
            "action_plan": self.d5_corrective_action,
            "target_date": self.due_date,
            "eight_d_id": self.id,
        }
        capa_values.update(capa_source_values)
        capa = self.env["pm.qms.capa"].create(
            capa_values
        )
        self.write({"capa_ids": [(4, capa.id)]})
        if self.complaint_id and not self.complaint_id.capa_id:
            self.complaint_id.write({"capa_id": capa.id})
        if self.supplier_issue_id and not self.supplier_issue_id.capa_id:
            self.supplier_issue_id.write({"capa_id": capa.id})
        return capa.get_formview_action()

    def _get_capa_source_values(self):
        self.ensure_one()
        if self.source_type == "ncr":
            if not self.ncr_id:
                raise UserError("Select the originating NCR before creating a CAPA from this NCR-based 8D.")
            return {"source_type": "ncr", "source_ncr_id": self.ncr_id.id}
        return {
            "source_type": {
                "complaint": "customer_issue",
                "supplier_issue": "supplier_issue",
                "scar": "supplier_issue",
                "other": "other",
            }[self.source_type],
            "source_ncr_id": False,
            "source_risk_id": False,
        }

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_8d_workflow"):
            raise AccessError("Use 8D workflow actions to change 8D status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(case.state != "draft" for case in self):
            raise UserError("Only draft 8D cases can be deleted.")
        return super().unlink()
