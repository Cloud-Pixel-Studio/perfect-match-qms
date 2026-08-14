from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsCapa(models.Model):
    _name = "pm.qms.capa"
    _description = "Perfect Match QMS CAPA"
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
    owner_id = fields.Many2one("res.users", tracking=True)
    source_type = fields.Selection(
        [
            ("ncr", "NCR"),
            ("risk", "Risk"),
            ("audit_finding", "Future Audit Finding"),
            ("customer_issue", "Customer Issue"),
            ("supplier_issue", "Supplier Issue"),
            ("management_decision", "Management Decision"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
        tracking=True,
    )
    source_reference = fields.Char()
    source_ncr_id = fields.Many2one("pm.qms.nonconformity", string="Originating NCR", ondelete="restrict", index=True)
    source_risk_id = fields.Many2one("pm.qms.risk", string="Originating Risk", ondelete="restrict", index=True)
    problem_statement = fields.Text(required=True)
    root_cause_method = fields.Selection(
        [
            ("5why", "5 Why"),
            ("fishbone", "Fishbone"),
            ("is_is_not", "Is / Is Not"),
            ("other", "Other"),
        ],
        default="5why",
        required=True,
    )
    root_cause_analysis = fields.Text()
    root_cause = fields.Text()
    action_plan = fields.Text()
    action_owner_id = fields.Many2one("res.users", string="Primary Action Owner")
    target_date = fields.Date()
    implementation_date = fields.Date(readonly=True)
    implementation_notes = fields.Text()
    effectiveness_required = fields.Boolean(default=True)
    effectiveness_review_date = fields.Date()
    effectiveness_reviewer_id = fields.Many2one("res.users", readonly=True)
    effectiveness_reviewed_on = fields.Datetime(readonly=True)
    effectiveness_result = fields.Selection(
        [
            ("not_reviewed", "Not Reviewed"),
            ("effective", "Effective"),
            ("ineffective", "Ineffective"),
        ],
        default="not_reviewed",
        required=True,
        tracking=True,
    )
    effectiveness_notes = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("analysis", "Analysis"),
            ("action_planned", "Action Planned"),
            ("implementation", "Implementation"),
            ("effectiveness_review", "Effectiveness Review"),
            ("effective", "Effective"),
            ("ineffective", "Ineffective"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    why_ids = fields.One2many("pm.qms.capa.why", "capa_id", string="5 Why Analysis")
    action_ids = fields.One2many("pm.qms.capa.action", "capa_id", string="CAPA Actions")
    action_count = fields.Integer(compute="_compute_action_counts")
    open_action_count = fields.Integer(compute="_compute_action_counts")
    related_control_instance_ids = fields.Many2many(
        "pm.qms.control.instance",
        "pm_qms_capa_control_instance_rel",
        "capa_id",
        "control_instance_id",
        string="Related Control Instances",
    )
    related_document_ids = fields.Many2many(
        "pm.qms.document",
        "pm_qms_capa_document_rel",
        "capa_id",
        "document_id",
        string="Related Documents",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "pm_qms_capa_attachment_rel",
        "capa_id",
        "attachment_id",
        string="Attachments",
    )
    is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    effectiveness_is_overdue = fields.Boolean(compute="_compute_overdue", store=True)
    effectiveness_days_overdue = fields.Integer(compute="_compute_overdue", store=True)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "CAPA code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.capa") or "PM-CAPA-00000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.depends("action_ids.status")
    def _compute_action_counts(self):
        for capa in self:
            capa.action_count = len(capa.action_ids)
            capa.open_action_count = len(capa.action_ids.filtered(lambda action: action.status not in ("verified", "cancelled")))

    @api.depends("target_date", "effectiveness_review_date", "state", "effectiveness_required")
    def _compute_overdue(self):
        today = fields.Date.context_today(self)
        for capa in self:
            overdue = bool(capa.target_date and capa.state not in ("effective", "closed", "cancelled") and capa.target_date < today)
            effectiveness_overdue = bool(
                capa.effectiveness_required
                and capa.effectiveness_review_date
                and capa.state not in ("effective", "closed", "cancelled")
                and capa.effectiveness_review_date < today
            )
            capa.is_overdue = overdue
            capa.days_overdue = (today - capa.target_date).days if overdue else 0
            capa.effectiveness_is_overdue = effectiveness_overdue
            capa.effectiveness_days_overdue = (today - capa.effectiveness_review_date).days if effectiveness_overdue else 0

    @api.constrains("organization_id", "process_id")
    def _check_process_alignment(self):
        for capa in self:
            if capa.process_id.company_id != capa.company_id:
                raise ValidationError("CAPA process must belong to the same company as the organization.")
            if capa.process_id.organization_id and capa.process_id.organization_id != capa.organization_id:
                raise ValidationError("CAPA process must belong to the selected organization.")

    @api.constrains("source_ncr_id", "source_risk_id")
    def _check_source_alignment(self):
        for capa in self:
            if capa.source_ncr_id and (
                capa.source_ncr_id.company_id != capa.company_id
                or capa.source_ncr_id.organization_id != capa.organization_id
            ):
                raise ValidationError("Originating NCR must match the CAPA company and organization.")
            if capa.source_risk_id and (
                capa.source_risk_id.company_id != capa.company_id
                or capa.source_risk_id.organization_id != capa.organization_id
            ):
                raise ValidationError("Originating risk must match the CAPA company and organization.")

    @api.constrains("related_control_instance_ids", "related_document_ids")
    def _check_related_records_alignment(self):
        for capa in self:
            for instance in capa.related_control_instance_ids:
                if instance.company_id != capa.company_id or instance.organization_id != capa.organization_id:
                    raise ValidationError("Related control instances must match the CAPA company and organization.")
            for document in capa.related_document_ids:
                if document.company_id != capa.company_id or document.organization_id != capa.organization_id:
                    raise ValidationError("Related documents must match the CAPA company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can perform CAPA workflow actions.")

    def _transition(self, state, decision, event_type="workflow", notes=None, extra_values=None):
        self._check_manager_permission()
        for capa in self:
            previous = capa.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            capa.with_context(pm_qms_capa_workflow=True).write(values)
            capa._log_qms_event(
                event_type=event_type,
                previous_state=previous,
                new_state=state,
                reviewer=self.env.user,
                approver=self.env.user if event_type in ("closure", "effectiveness") else None,
                decision=decision,
                notes=notes,
            )

    def action_start_analysis(self):
        self._transition("analysis", "CAPA analysis started")

    def action_plan_actions(self):
        for capa in self:
            if not capa.root_cause:
                raise UserError("Root cause is required before planning CAPA actions.")
        self._transition("action_planned", "CAPA actions planned")

    def action_start_implementation(self):
        for capa in self:
            if not capa.action_ids:
                raise UserError("At least one CAPA action is required before implementation.")
        self._transition("implementation", "CAPA implementation started")

    def action_complete_implementation(self):
        for capa in self:
            active_actions = capa.action_ids.filtered(lambda action: action.status != "cancelled")
            if not active_actions or any(action.status not in ("completed", "verified") for action in active_actions):
                raise UserError("All active CAPA actions must be completed or verified before implementation completion.")
        self._transition(
            "effectiveness_review",
            "CAPA implementation completed",
            event_type="review",
            extra_values={"implementation_date": fields.Date.context_today(self)},
        )

    def action_start_effectiveness_review(self):
        self._transition("effectiveness_review", "CAPA effectiveness review started", event_type="review")

    def action_mark_effective(self):
        for capa in self:
            if capa.effectiveness_required and not capa.effectiveness_notes:
                raise UserError("Effectiveness notes are required before marking a CAPA effective.")
        self._transition(
            "effective",
            "CAPA effectiveness accepted",
            event_type="effectiveness",
            notes="Effectiveness notes retained on the record.",
            extra_values={
                "effectiveness_result": "effective",
                "effectiveness_reviewer_id": self.env.user.id,
                "effectiveness_reviewed_on": fields.Datetime.now(),
            },
        )

    def action_mark_ineffective(self):
        for capa in self:
            if not capa.effectiveness_notes:
                raise UserError("Effectiveness notes are required before marking a CAPA ineffective.")
        self._transition(
            "ineffective",
            "CAPA effectiveness rejected",
            event_type="effectiveness",
            notes="Ineffective result retained; add actions or reopen the plan.",
            extra_values={
                "effectiveness_result": "ineffective",
                "effectiveness_reviewer_id": self.env.user.id,
                "effectiveness_reviewed_on": fields.Datetime.now(),
            },
        )

    def action_reopen_actions(self):
        self._transition("action_planned", "CAPA reopened for additional actions", event_type="workflow")

    def action_close(self):
        self._check_manager_permission()
        for capa in self:
            if capa.state != "effective":
                raise UserError("Only an effective CAPA can be closed.")
        self._transition("closed", "CAPA closed", event_type="closure")

    def action_cancel(self):
        self._transition("cancelled", "CAPA cancelled", event_type="closure")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_capa_workflow"):
            raise AccessError("Use CAPA workflow actions to change CAPA status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(capa.state != "draft" for capa in self):
            raise UserError("Only draft CAPA records can be deleted.")
        return super().unlink()
