from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsAuditFinding(models.Model):
    _name = "pm.qms.audit.finding"
    _description = "Perfect Match QMS Audit Finding"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    audit_id = fields.Many2one("pm.qms.audit", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="audit_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="audit_id.organization_id", store=True, readonly=True, index=True)
    classification = fields.Selection(
        [
            ("conformity", "Conformity"),
            ("observation", "Observation"),
            ("opportunity_for_improvement", "Opportunity for Improvement"),
            ("nonconformity", "Internal Nonconformity"),
        ],
        default="observation",
        required=True,
        tracking=True,
    )
    severity = fields.Selection(
        [("minor", "Minor"), ("major", "Major"), ("critical", "Critical")],
        tracking=True,
    )
    title = fields.Char(required=True, tracking=True)
    description = fields.Text()
    objective_evidence = fields.Text(required=True)
    criterion_id = fields.Many2one("pm.qms.audit.criterion", ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", ondelete="restrict", index=True)
    control_instance_id = fields.Many2one("pm.qms.control.instance", ondelete="restrict", index=True)
    audit_evidence_ids = fields.Many2many(
        "pm.qms.audit.evidence",
        "pm_qms_audit_finding_evidence_rel",
        "finding_id",
        "audit_evidence_id",
        string="Audit Evidence",
    )
    owner_id = fields.Many2one("res.users", tracking=True)
    due_date = fields.Date()
    follow_up_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("accepted", "Accepted"),
            ("action_required", "Action Required"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    issued_by_id = fields.Many2one("res.users", readonly=True)
    issued_on = fields.Datetime(readonly=True)
    closed_by_id = fields.Many2one("res.users", readonly=True)
    closed_on = fields.Datetime(readonly=True)
    closure_notes = fields.Text()
    ncr_ids = fields.One2many("pm.qms.nonconformity", "source_audit_finding_id", string="Related NCRs")
    ncr_count = fields.Integer(compute="_compute_ncr_count")
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    follow_up_is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    follow_up_days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Audit finding code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") and vals.get("title"):
                vals["name"] = vals["title"]
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.audit.finding") or "PM-AUDF-00000"
        return super().create(vals_list)

    @api.depends("ncr_ids")
    def _compute_ncr_count(self):
        for finding in self:
            finding.ncr_count = len(finding.ncr_ids)

    @api.depends("due_date", "follow_up_date", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for finding in self:
            overdue = bool(finding.due_date and finding.state not in ("closed", "cancelled") and finding.due_date < today)
            follow_up_overdue = bool(
                finding.follow_up_date and finding.state not in ("closed", "cancelled") and finding.follow_up_date < today
            )
            finding.is_overdue = overdue
            finding.days_overdue = (today - finding.due_date).days if overdue else 0
            finding.follow_up_is_overdue = follow_up_overdue
            finding.follow_up_days_overdue = (today - finding.follow_up_date).days if follow_up_overdue else 0

    @api.constrains("classification", "severity")
    def _check_severity_scope(self):
        for finding in self:
            if finding.classification != "nonconformity" and finding.severity:
                raise ValidationError("Finding severity is only used for internal nonconformities.")

    @api.constrains("audit_id", "criterion_id", "process_id", "control_instance_id", "audit_evidence_ids")
    def _check_finding_alignment(self):
        for finding in self:
            if finding.criterion_id and finding.criterion_id.audit_id != finding.audit_id:
                raise ValidationError("Finding criterion must belong to the same audit.")
            if finding.process_id:
                if finding.process_id.company_id != finding.company_id:
                    raise ValidationError("Finding process must belong to the audit company.")
                if finding.process_id.organization_id and finding.process_id.organization_id != finding.organization_id:
                    raise ValidationError("Finding process must belong to the audit organization.")
            if finding.control_instance_id:
                if finding.control_instance_id.company_id != finding.company_id:
                    raise ValidationError("Finding control instance must belong to the audit company.")
                if finding.control_instance_id.organization_id != finding.organization_id:
                    raise ValidationError("Finding control instance must belong to the audit organization.")
                if finding.process_id and finding.control_instance_id.process_id != finding.process_id:
                    raise ValidationError("Finding control instance must belong to the selected process.")
            for evidence in finding.audit_evidence_ids:
                if evidence.audit_id != finding.audit_id:
                    raise ValidationError("Finding audit evidence must belong to the same audit.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage audit finding workflow.")

    def _transition(self, state, decision, event_type="workflow", extra_values=None):
        self._check_manager_permission()
        allowed = {
            "issued": ("draft",),
            "accepted": ("issued", "action_required"),
            "action_required": ("issued", "accepted"),
            "closed": ("issued", "accepted", "action_required"),
            "cancelled": ("draft", "issued", "accepted", "action_required"),
        }
        for finding in self:
            if finding.state not in allowed[state]:
                raise UserError(f"Finding cannot move from {finding.state} to {state}.")
            previous = finding.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            finding.with_context(pm_qms_audit_finding_workflow=True).write(values)
            finding._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=state,
                reviewer=self.env.user,
                approver=self.env.user if event_type == "closure" else None,
                decision=decision,
            )

    def action_issue(self):
        self._transition(
            "issued",
            "Finding issued",
            extra_values={"issued_by_id": self.env.user.id, "issued_on": fields.Datetime.now()},
        )

    def action_accept(self):
        self._transition("accepted", "Finding accepted", event_type="review")

    def action_require_action(self):
        self._transition("action_required", "Finding requires action", event_type="review")

    def action_close(self):
        for finding in self:
            if not finding.closure_notes:
                raise UserError("Closure notes are required before closing a finding.")
        self._transition(
            "closed",
            "Finding closed",
            event_type="closure",
            extra_values={"closed_by_id": self.env.user.id, "closed_on": fields.Datetime.now()},
        )

    def action_cancel(self):
        self._transition("cancelled", "Finding cancelled", event_type="closure")

    def action_create_ncr(self):
        self.ensure_one()
        self._check_manager_permission()
        if self.classification != "nonconformity":
            raise UserError("Only an internal nonconformity finding can create an NCR.")
        if self.state == "draft":
            raise UserError("Finding must be issued before creating an NCR.")
        if self.ncr_ids:
            raise UserError("This finding already has a related NCR.")
        if not self.process_id:
            raise UserError("A process is required before creating an NCR from an audit finding.")
        documents = self.audit_evidence_ids.mapped("document_id")
        ncr = self.env["pm.qms.nonconformity"].create(
            {
                "name": f"NCR for {self.code}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "audit",
                "severity": self.severity or "minor",
                "description": self.description or self.objective_evidence,
                "owner_id": self.owner_id.id,
                "source_audit_id": self.audit_id.id,
                "source_audit_finding_id": self.id,
                "source_audit_evidence_ids": [(6, 0, self.audit_evidence_ids.ids)],
                "related_control_instance_ids": [(6, 0, self.control_instance_id.ids)],
                "related_document_ids": [(6, 0, documents.ids)],
            }
        )
        previous = self.state
        if self.state != "action_required":
            self.with_context(pm_qms_audit_finding_workflow=True).write({"state": "action_required"})
        self._log_qms_event(
            event_type="workflow",
            previous_state=previous,
            new_state="action_required",
            reviewer=self.env.user,
            decision="NCR created from audit finding",
            notes=ncr.code,
        )
        return {
            "type": "ir.actions.act_window",
            "name": "NCR",
            "res_model": "pm.qms.nonconformity",
            "res_id": ncr.id,
            "view_mode": "form",
        }

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_audit_finding_workflow"):
            raise AccessError("Use audit finding workflow actions to change finding status.")
        previous_classification = {finding.id: finding.classification for finding in self}
        result = super().write(vals)
        if "classification" in vals:
            for finding in self:
                if previous_classification.get(finding.id) != finding.classification:
                    finding._log_qms_event(
                        event_type="review",
                        previous_state=previous_classification.get(finding.id),
                        new_state=finding.classification,
                        reviewer=self.env.user,
                        decision="Finding classification changed",
                    )
        return result

    def unlink(self):
        if any(finding.state != "draft" for finding in self):
            raise UserError("Only draft audit findings can be deleted.")
        return super().unlink()
