from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .capa_is_is_not import IS_IS_NOT_DIMENSIONS, IS_IS_NOT_SEQUENCE
from .capa_why import WHY_PROMPTS


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
        tracking=True,
    )
    root_cause_analysis = fields.Text(tracking=True)
    root_cause = fields.Text(tracking=True)
    other_method_name = fields.Char(string="Method / Tool Used", tracking=True)
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
    fishbone_ids = fields.One2many("pm.qms.capa.fishbone", "capa_id", string="Fishbone Causes")
    is_is_not_ids = fields.One2many("pm.qms.capa.is.is.not", "capa_id", string="Is / Is Not Analysis")
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
        self._check_manager_permission()
        for capa in self:
            capa._validate_analysis_start()
            capa._initialize_analysis_structure()
        self._transition("analysis", "CAPA analysis started")

    def action_plan_actions(self):
        for capa in self:
            capa._validate_root_cause_method()
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
        if "root_cause_method" in vals and any(capa.state != "draft" for capa in self):
            raise UserError("The root cause method is locked after CAPA analysis starts.")
        rca_fields = {"root_cause_analysis", "root_cause", "other_method_name"}
        if rca_fields.intersection(vals) and any(
            capa.state in ("implementation", "effectiveness_review", "effective", "ineffective", "closed")
            for capa in self
        ):
            raise UserError("Root cause methodology is locked after implementation starts.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(capa.state != "draft" for capa in self):
            raise UserError("Only draft CAPA records can be deleted.")
        return super().unlink()

    def _initialize_analysis_structure(self):
        self.ensure_one()
        if self.root_cause_method == "5why":
            existing = {why.sequence for why in self.why_ids if why.sequence in WHY_PROMPTS}
            missing = [sequence for sequence in WHY_PROMPTS if sequence not in existing]
            if missing:
                self.env["pm.qms.capa.why"].with_context(pm_qms_capa_initialize=True).create(
                    [{"capa_id": self.id, "sequence": sequence} for sequence in missing]
                )
        elif self.root_cause_method == "is_is_not":
            existing = {row.dimension for row in self.is_is_not_ids if row.dimension in IS_IS_NOT_DIMENSIONS}
            missing = [dimension for dimension in IS_IS_NOT_DIMENSIONS if dimension not in existing]
            if missing:
                self.env["pm.qms.capa.is.is.not"].with_context(pm_qms_capa_initialize=True).create(
                    [
                        {"capa_id": self.id, "dimension": dimension, "sequence": IS_IS_NOT_SEQUENCE[dimension]}
                        for dimension in missing
                    ]
                )

    def _validate_analysis_start(self):
        self.ensure_one()
        prerequisites = (
            (self.name, "CAPA name"),
            (self.organization_id, "organization"),
            (self.process_id, "process"),
            (self.problem_statement, "CAPA problem statement"),
            (self.root_cause_method, "root cause method"),
        )
        for value, label in prerequisites:
            if not value or (isinstance(value, str) and not value.strip()):
                raise UserError(f"Complete the {label} before starting root cause analysis.")

    def _validate_root_cause_method(self):
        self.ensure_one()
        if not self.root_cause_analysis or not self.root_cause:
            raise UserError("Root cause analysis summary and verified root cause are required before planning actions.")
        if self.root_cause_method == "5why":
            slots = self.why_ids
            sequences = slots.mapped("sequence")
            if len(slots) != 5 or set(sequences) != set(WHY_PROMPTS):
                raise UserError("5 Why analysis must contain exactly one valid slot for each sequence 1 through 5.")
            answers = {why.sequence: bool((why.answer or "").strip()) for why in slots}
            if not answers.get(1):
                raise UserError("Why 1 must be answered before planning CAPA actions.")
            highest = max(sequence for sequence, answered in answers.items() if answered)
            if any(not answers[sequence] for sequence in range(1, highest + 1)):
                raise UserError("5 Why answers must be contiguous; trailing blank slots are allowed.")
        elif self.root_cause_method == "fishbone":
            if not self.fishbone_ids:
                raise UserError("Fishbone analysis requires at least one potential cause.")
            confirmed = self.fishbone_ids.filtered(lambda cause: cause.investigation_status == "confirmed")
            if not confirmed:
                raise UserError("Fishbone analysis requires at least one confirmed cause.")
            if any(not cause.evidence_basis or not cause.rationale_finding for cause in confirmed):
                raise UserError("Confirmed Fishbone causes require evidence basis and rationale.")
        elif self.root_cause_method == "is_is_not":
            rows = self.is_is_not_ids
            if (
                len(rows) != 4
                or set(rows.mapped("dimension")) != set(IS_IS_NOT_DIMENSIONS)
                or set(rows.mapped("sequence")) != set(IS_IS_NOT_SEQUENCE.values())
            ):
                raise UserError("Is / Is Not analysis requires What, Where, When, and Extent rows.")
            if any(not all((row.is_value, row.is_not_value, row.distinction)) for row in rows):
                raise UserError("Is / Is Not requires IS, IS NOT, and Distinction for every dimension.")
        elif self.root_cause_method == "other":
            if not self.other_method_name:
                raise UserError("Other method requires the method/tool, analysis, and verified root cause.")
