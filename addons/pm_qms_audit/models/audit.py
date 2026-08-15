from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsAudit(models.Model):
    _name = "pm.qms.audit"
    _description = "Perfect Match QMS Audit"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "planned_start desc, code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    program_id = fields.Many2one("pm.qms.audit.program", ondelete="restrict", index=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    planned_start = fields.Date(required=True, tracking=True)
    planned_end = fields.Date(required=True, tracking=True)
    actual_start = fields.Date(tracking=True)
    actual_end = fields.Date(tracking=True)
    audit_type = fields.Selection(
        [
            ("system", "System"),
            ("process", "Process"),
            ("department", "Department"),
            ("special", "Special"),
            ("follow_up", "Follow Up"),
        ],
        default="process",
        required=True,
        tracking=True,
    )
    objective = fields.Text(required=True)
    scope_summary = fields.Text()
    conclusion = fields.Text()
    lead_auditor_id = fields.Many2one("res.users", tracking=True)
    auditor_ids = fields.Many2many(
        "res.users",
        "pm_qms_audit_auditor_rel",
        "audit_id",
        "user_id",
        string="Auditors",
    )
    auditee_ids = fields.Many2many(
        "res.users",
        "pm_qms_audit_auditee_rel",
        "audit_id",
        "user_id",
        string="Auditees / Process Owners",
    )
    independence_required = fields.Boolean(default=True, tracking=True)
    independence_confirmed = fields.Boolean(default=False, tracking=True)
    independence_reviewed_by_id = fields.Many2one("res.users", readonly=True)
    independence_review_date = fields.Date(readonly=True)
    independence_notes = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("planned", "Planned"),
            ("ready", "Ready"),
            ("in_progress", "In Progress"),
            ("reporting", "Reporting"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    scope_ids = fields.One2many("pm.qms.audit.scope", "audit_id", string="Scope")
    criterion_ids = fields.One2many("pm.qms.audit.criterion", "audit_id", string="Criteria")
    plan_line_ids = fields.One2many("pm.qms.audit.plan.line", "audit_id", string="Plan Lines")
    audit_evidence_ids = fields.One2many("pm.qms.audit.evidence", "audit_id", string="Audit Evidence")
    finding_ids = fields.One2many("pm.qms.audit.finding", "audit_id", string="Findings")
    ncr_ids = fields.One2many("pm.qms.nonconformity", "source_audit_id", string="NCRs")
    total_finding_count = fields.Integer(compute="_compute_summary_counts")
    conformity_count = fields.Integer(compute="_compute_summary_counts")
    observation_count = fields.Integer(compute="_compute_summary_counts")
    ofi_count = fields.Integer(compute="_compute_summary_counts")
    nonconformity_count = fields.Integer(compute="_compute_summary_counts")
    open_finding_count = fields.Integer(compute="_compute_summary_counts")
    ncr_count = fields.Integer(compute="_compute_summary_counts")
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Audit code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("program_id") and not vals.get("organization_id"):
                program = self.env["pm.qms.audit.program"].browse(vals["program_id"])
                vals["organization_id"] = program.organization_id.id
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.audit") or "PM-AUD-00000"
            if vals.get("lead_auditor_id") and not vals.get("auditor_ids"):
                vals["auditor_ids"] = [(4, vals["lead_auditor_id"])]
        return super().create(vals_list)

    @api.depends("finding_ids.classification", "finding_ids.state", "ncr_ids")
    def _compute_summary_counts(self):
        for audit in self:
            findings = audit.finding_ids
            audit.total_finding_count = len(findings)
            audit.conformity_count = len(findings.filtered(lambda finding: finding.classification == "conformity"))
            audit.observation_count = len(findings.filtered(lambda finding: finding.classification == "observation"))
            audit.ofi_count = len(findings.filtered(lambda finding: finding.classification == "opportunity_for_improvement"))
            audit.nonconformity_count = len(findings.filtered(lambda finding: finding.classification == "nonconformity"))
            audit.open_finding_count = len(findings.filtered(lambda finding: finding.state not in ("closed", "cancelled")))
            audit.ncr_count = len(audit.ncr_ids)

    @api.depends("planned_start", "state")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for audit in self:
            overdue = bool(audit.planned_start and audit.state in ("planned", "ready") and audit.planned_start < today)
            audit.is_overdue = overdue
            audit.days_overdue = (today - audit.planned_start).days if overdue else 0

    @api.constrains("planned_start", "planned_end", "actual_start", "actual_end")
    def _check_dates(self):
        for audit in self:
            if audit.planned_start and audit.planned_end and audit.planned_end < audit.planned_start:
                raise ValidationError("Planned audit end date cannot be before the planned start date.")
            if audit.actual_start and audit.actual_end and audit.actual_end < audit.actual_start:
                raise ValidationError("Actual audit end date cannot be before the actual start date.")

    @api.constrains("program_id", "organization_id")
    def _check_program_alignment(self):
        for audit in self:
            if audit.program_id and audit.program_id.company_id != audit.company_id:
                raise ValidationError("Audit program must belong to the same company as the audit.")
            if audit.program_id and audit.program_id.organization_id != audit.organization_id:
                raise ValidationError("Audit program must belong to the same organization as the audit.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage audit workflow.")

    def action_record_independence(self):
        self._check_manager_permission()
        previous = {
            audit.id: "confirmed" if audit.independence_confirmed else "not_confirmed"
            for audit in self
        }
        self.write(
            {
                "independence_required": True,
                "independence_confirmed": True,
                "independence_reviewed_by_id": self.env.user.id,
                "independence_review_date": fields.Date.context_today(self),
            }
        )
        for audit in self:
            audit._log_qms_event(
                event_type="review",
                previous_state=previous[audit.id],
                new_state="confirmed",
                reviewer=self.env.user,
                decision="Auditor independence confirmed",
                notes=audit.independence_notes,
            )

    def action_record_independence_override(self):
        self._check_manager_permission()
        for audit in self:
            if not audit.independence_notes:
                raise UserError("Independence override notes are required.")
        previous = {
            audit.id: "confirmed" if audit.independence_confirmed else "not_confirmed"
            for audit in self
        }
        self.write(
            {
                "independence_required": False,
                "independence_confirmed": False,
                "independence_reviewed_by_id": self.env.user.id,
                "independence_review_date": fields.Date.context_today(self),
            }
        )
        for audit in self:
            audit._log_qms_event(
                event_type="review",
                previous_state=previous[audit.id],
                new_state="override",
                reviewer=self.env.user,
                decision="Auditor independence override documented",
                notes=audit.independence_notes,
            )

    def _check_ready_requirements(self):
        for audit in self:
            if not audit.lead_auditor_id:
                raise UserError("Lead auditor is required before an audit can be ready.")
            if not audit.scope_ids:
                raise UserError("At least one audit scope line is required before an audit can be ready.")
            if not audit.criterion_ids:
                raise UserError("At least one audit criterion is required before an audit can be ready.")
            if audit.independence_required and not audit.independence_confirmed:
                raise UserError("Auditor independence must be confirmed before an audit can be ready.")
            if not audit.independence_required and not audit.independence_notes:
                raise UserError("Independence override notes are required before an audit can be ready.")

    def _check_completion_requirements(self):
        for audit in self:
            if not audit.actual_start or not audit.actual_end:
                raise UserError("Actual audit start and end dates are required before completion.")
            if not audit.lead_auditor_id:
                raise UserError("Lead auditor is required before audit completion.")
            if not audit.scope_ids or not audit.criterion_ids:
                raise UserError("Audit scope and criteria are required before audit completion.")
            if not audit.conclusion:
                raise UserError("Audit conclusion is required before completion.")

    def _transition(self, state, decision, event_type="workflow", extra_values=None):
        self._check_manager_permission()
        allowed = {
            "planned": ("draft",),
            "ready": ("planned",),
            "in_progress": ("ready",),
            "reporting": ("in_progress",),
            "completed": ("reporting",),
            "cancelled": ("draft", "planned", "ready", "in_progress", "reporting"),
        }
        for audit in self:
            if audit.state not in allowed[state]:
                raise UserError(f"Audit cannot move from {audit.state} to {state}.")
            previous = audit.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            audit.with_context(pm_qms_audit_workflow=True).write(values)
            audit._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=state,
                reviewer=self.env.user,
                approver=self.env.user if event_type == "closure" else None,
                decision=decision,
            )

    def action_plan(self):
        self._transition("planned", "Audit planned")

    def action_mark_ready(self):
        self._check_ready_requirements()
        self._transition("ready", "Audit ready")

    def action_start(self):
        self._transition(
            "in_progress",
            "Audit started",
            extra_values={"actual_start": fields.Date.context_today(self)},
        )

    def action_start_reporting(self):
        for audit in self:
            extra_values = {}
            if not audit.actual_end:
                extra_values["actual_end"] = fields.Date.context_today(audit)
            audit._transition("reporting", "Audit fieldwork completed", event_type="review", extra_values=extra_values)

    def action_complete(self):
        self._check_completion_requirements()
        self._transition("completed", "Audit completed", event_type="closure")

    def action_cancel(self):
        self._transition("cancelled", "Audit cancelled", event_type="closure")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_audit_workflow"):
            raise AccessError("Use audit workflow actions to change audit status.")
        return super().write(vals)

    def unlink(self):
        if any(audit.state != "draft" for audit in self):
            raise UserError("Only draft audits can be deleted.")
        return super().unlink()
