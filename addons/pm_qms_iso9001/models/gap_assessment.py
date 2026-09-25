from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


GAP_FOCUS_DEFINITIONS = (
    (
        "transition_governance",
        "Transition scope and governance",
        "Confirm the approved source baseline, target edition, accountable owners, boundaries, and decision path.",
    ),
    (
        "context_and_stakeholders",
        "Context and stakeholder assumptions",
        "Review material internal, external, and stakeholder changes that can affect the QMS transition.",
    ),
    (
        "leadership_culture_ethics",
        "Leadership, quality culture, and ethical conduct",
        "Evaluate leadership practices, expected behaviours, communication, and evidence supporting the intended quality culture.",
    ),
    (
        "risks_and_opportunities",
        "Risks and opportunities",
        "Evaluate whether risks and opportunities are identified, treated, owned, monitored, and evidenced through distinct decisions.",
    ),
    (
        "controlled_change",
        "Controlled organizational change",
        "Evaluate how QMS changes are planned, authorized, resourced, implemented, and reviewed for unintended effects.",
    ),
    (
        "evidence_and_history",
        "Evidence migration and historical integrity",
        "Confirm that current evidence is traceable and that prior-edition records remain preserved without silent rewriting.",
    ),
)


class PmQmsIso9001GapAssessment(models.Model):
    _name = "pm.qms.iso9001.gap.assessment"
    _description = "PM-QMS ISO 9001 Edition Gap Assessment"
    _order = "assessment_date desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True)
    code = fields.Char(default="New", required=True, copy=False, readonly=True)
    scenario_id = fields.Many2one(
        "pm.qms.iso9001.transition.scenario",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        related="scenario_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    source_profile_id = fields.Many2one(
        "pm.qms.mapping.profile",
        ondelete="restrict",
        index=True,
    )
    target_profile_id = fields.Many2one(
        related="scenario_id.profile_id",
        store=True,
        readonly=True,
        index=True,
    )
    source_edition_snapshot = fields.Char(readonly=True)
    target_edition_snapshot = fields.Char(readonly=True)
    assessment_date = fields.Date(required=True, default=fields.Date.context_today)
    assessor_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        "pm.qms.iso9001.gap.assessment.line",
        "assessment_id",
        string="Assessment Areas",
        copy=False,
    )
    total_area_count = fields.Integer(compute="_compute_summary")
    conforming_area_count = fields.Integer(compute="_compute_summary")
    partial_area_count = fields.Integer(compute="_compute_summary")
    gap_area_count = fields.Integer(compute="_compute_summary")
    not_applicable_area_count = fields.Integer(compute="_compute_summary")
    readiness_percent = fields.Float(compute="_compute_summary")
    conclusion = fields.Text()
    completed_by_id = fields.Many2one("res.users", readonly=True)
    completed_date = fields.Datetime(readonly=True)

    @api.depends("line_ids.status")
    def _compute_summary(self):
        for assessment in self:
            lines = assessment.line_ids
            applicable = lines.filtered(lambda line: line.status != "not_applicable")
            weighted_ready = sum(
                1.0 if line.status == "conforming" else 0.5 if line.status == "partial" else 0.0
                for line in applicable
            )
            assessment.total_area_count = len(lines)
            assessment.conforming_area_count = len(lines.filtered(lambda line: line.status == "conforming"))
            assessment.partial_area_count = len(lines.filtered(lambda line: line.status == "partial"))
            assessment.gap_area_count = len(lines.filtered(lambda line: line.status == "gap"))
            assessment.not_applicable_area_count = len(
                lines.filtered(lambda line: line.status == "not_applicable")
            )
            assessment.readiness_percent = (
                weighted_ready / len(applicable) * 100.0 if applicable else 0.0
            )

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage ISO 9001 gap assessments.")

    @api.model_create_multi
    def create(self, vals_list):
        self._check_manager_permission()
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = (
                    self.env["ir.sequence"].next_by_code("pm.qms.iso9001.gap.assessment")
                    or "ISO-GAP-00000"
                )
        return super().create(vals_list)

    @api.constrains("scenario_id", "source_profile_id")
    def _check_profile_scope(self):
        for assessment in self:
            scenario = assessment.scenario_id
            source = assessment.source_profile_id
            if source:
                if source.company_id != assessment.company_id:
                    raise ValidationError("Source profile and assessment company must match.")
                if source.standard_name != "ISO 9001":
                    raise ValidationError("The source profile must be an ISO 9001 profile.")
                if scenario.source_edition not in (False, "legacy") and source.edition != scenario.source_edition:
                    raise ValidationError("Source profile edition must match the selected scenario.")
            elif scenario.scenario_type in ("transition", "recertification"):
                raise ValidationError("The selected transition scenario requires a source profile.")

    def action_start(self):
        self._check_manager_permission()
        for assessment in self:
            if assessment.state != "draft":
                raise UserError("Only draft gap assessments can be started.")
            if assessment.line_ids:
                raise UserError("Draft gap assessment areas already exist.")
            assessment.with_context(pm_qms_gap_workflow=True).write(
                {
                    "source_edition_snapshot": assessment.source_profile_id.edition
                    if assessment.source_profile_id
                    else assessment.scenario_id.source_edition,
                    "target_edition_snapshot": assessment.target_profile_id.edition,
                    "line_ids": [
                        Command.create(
                            {
                                "sequence": sequence,
                                "focus_code": code,
                                "focus_name_snapshot": name,
                                "purpose_snapshot": purpose,
                            }
                        )
                        for sequence, (code, name, purpose) in enumerate(
                            GAP_FOCUS_DEFINITIONS, start=10
                        )
                    ],
                    "state": "in_progress",
                }
            )
        return True

    def action_complete(self):
        self._check_manager_permission()
        for assessment in self:
            if assessment.state != "in_progress":
                raise UserError("Only in-progress gap assessments can be completed.")
            if len(assessment.line_ids) != len(GAP_FOCUS_DEFINITIONS):
                raise UserError("The complete controlled assessment area set is required.")
            pending = assessment.line_ids.filtered(lambda line: line.status == "not_assessed")
            if pending:
                raise UserError("Every assessment area must have a disposition before completion.")
            insufficient = assessment.line_ids.filtered(
                lambda line: line.status in ("partial", "gap")
                and (
                    not line.gap_description
                    or not line.action_plan
                    or not line.responsible_id
                    or not line.target_date
                )
            )
            if insufficient:
                raise UserError(
                    "Partial and gap areas require a gap description, action plan, owner, and target date."
                )
            unsupported_na = assessment.line_ids.filtered(
                lambda line: line.status == "not_applicable" and not line.disposition_rationale
            )
            if unsupported_na:
                raise UserError("Not-applicable areas require a documented rationale.")
            assessment.with_context(pm_qms_gap_workflow=True).write(
                {
                    "state": "completed",
                    "completed_by_id": self.env.user.id,
                    "completed_date": fields.Datetime.now(),
                }
            )
        return True

    def action_cancel(self):
        self._check_manager_permission()
        for assessment in self:
            if assessment.state == "completed":
                raise UserError("Completed gap assessments are immutable historical records.")
        self.with_context(pm_qms_gap_workflow=True).write({"state": "cancelled"})
        return True

    def write(self, vals):
        if any(record.state == "completed" for record in self):
            raise AccessError("Completed ISO 9001 gap assessments are immutable historical records.")
        if "state" in vals and not self.env.context.get("pm_qms_gap_workflow"):
            raise AccessError("Use the gap assessment workflow actions to change status.")
        protected = set(vals) - {"conclusion"}
        if protected and not self.env.context.get("pm_qms_gap_workflow"):
            self._check_manager_permission()
        return super().write(vals)

    def unlink(self):
        self._check_manager_permission()
        if any(record.state not in ("draft", "cancelled") for record in self):
            raise UserError("Only draft or cancelled gap assessments can be deleted.")
        return super().unlink()

    def copy(self, default=None):
        raise UserError("Gap assessments cannot be copied because they are controlled snapshots.")


class PmQmsIso9001GapAssessmentLine(models.Model):
    _name = "pm.qms.iso9001.gap.assessment.line"
    _description = "PM-QMS ISO 9001 Edition Gap Assessment Area"
    _order = "assessment_id, sequence, id"

    assessment_id = fields.Many2one(
        "pm.qms.iso9001.gap.assessment",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="assessment_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    sequence = fields.Integer(default=10, required=True)
    focus_code = fields.Char(required=True)
    focus_name_snapshot = fields.Char(required=True)
    purpose_snapshot = fields.Text(required=True)
    status = fields.Selection(
        [
            ("not_assessed", "Not Assessed"),
            ("conforming", "Conforming"),
            ("partial", "Partially Addressed"),
            ("gap", "Gap"),
            ("not_applicable", "Not Applicable"),
        ],
        default="not_assessed",
        required=True,
    )
    evidence_summary = fields.Text()
    gap_description = fields.Text()
    disposition_rationale = fields.Text()
    action_plan = fields.Text()
    responsible_id = fields.Many2one("res.users", ondelete="restrict")
    target_date = fields.Date()
    notes = fields.Text()

    _assessment_focus_uniq = models.Constraint(
        "UNIQUE(assessment_id, focus_code)",
        "Each controlled focus area may appear only once per assessment.",
    )

    def _check_editable(self):
        if any(line.assessment_id.state != "in_progress" for line in self):
            raise AccessError("Gap assessment areas can be edited only while the assessment is in progress.")
        self.assessment_id._check_manager_permission()

    @api.model_create_multi
    def create(self, vals_list):
        assessments = self.env["pm.qms.iso9001.gap.assessment"].browse(
            [vals.get("assessment_id") for vals in vals_list if vals.get("assessment_id")]
        )
        assessments._check_manager_permission()
        if any(assessment.state != "draft" for assessment in assessments):
            raise AccessError("Assessment areas can be initialized only from a draft assessment.")
        return super().create(vals_list)

    def write(self, vals):
        self._check_editable()
        protected = {"focus_code", "focus_name_snapshot", "purpose_snapshot", "assessment_id", "company_id"}
        if protected.intersection(vals):
            raise AccessError("Controlled assessment area identity cannot be changed.")
        return super().write(vals)

    def unlink(self):
        self._check_editable()
        raise AccessError("Controlled assessment areas cannot be deleted individually.")
