from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsIso9001GapAssessment(models.Model):
    _inherit = "pm.qms.iso9001.gap.assessment"

    transition_action_ids = fields.One2many(
        "pm.qms.iso9001.transition.action",
        "assessment_id",
        string="Transition Actions",
        readonly=True,
        copy=False,
    )
    transition_action_count = fields.Integer(
        compute="_compute_transition_action_count"
    )

    @api.depends("transition_action_ids")
    def _compute_transition_action_count(self):
        for assessment in self:
            assessment.transition_action_count = len(assessment.transition_action_ids)

    def action_generate_transition_plan(self):
        self.ensure_one()
        self._check_manager_permission()
        if self.state != "completed":
            raise UserError("Complete the gap assessment before generating its transition plan.")
        actionable_lines = self.line_ids.filtered(
            lambda line: line.status in ("partial", "gap")
        )
        if not actionable_lines:
            raise UserError("This assessment has no partial or gap areas requiring transition actions.")
        self.env["pm.qms.iso9001.transition.action"]._generate_from_assessment(
            self, actionable_lines
        )
        return {
            "type": "ir.actions.act_window",
            "name": "ISO 9001 Transition Actions",
            "res_model": "pm.qms.iso9001.transition.action",
            "view_mode": "list,form",
            "domain": [("assessment_id", "=", self.id)],
            "context": {"default_assessment_id": self.id},
        }


class PmQmsIso9001TransitionAction(models.Model):
    _name = "pm.qms.iso9001.transition.action"
    _description = "PM-QMS ISO 9001 Transition Action"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, target_date, code"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, readonly=True, copy=False, index=True)
    assessment_id = fields.Many2one(
        "pm.qms.iso9001.gap.assessment",
        required=True,
        ondelete="restrict",
        readonly=True,
        index=True,
    )
    assessment_line_id = fields.Many2one(
        "pm.qms.iso9001.gap.assessment.line",
        required=True,
        ondelete="restrict",
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )
    implementation_project_id = fields.Many2one(
        "pm.qms.implementation.project",
        string="Implementation Project",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    focus_code_snapshot = fields.Char(required=True, readonly=True)
    focus_name_snapshot = fields.Char(required=True, readonly=True)
    gap_description_snapshot = fields.Text(required=True, readonly=True)
    action_plan_snapshot = fields.Text(required=True, readonly=True)
    source_status_snapshot = fields.Selection(
        [
            ("partial", "Partially Addressed"),
            ("gap", "Gap"),
        ],
        required=True,
        readonly=True,
    )
    owner_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    target_date = fields.Date(required=True, tracking=True)
    priority = fields.Selection(
        [
            ("0", "Normal"),
            ("1", "High"),
            ("2", "Urgent"),
        ],
        required=True,
        default="0",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_progress", "In Progress"),
            ("verification", "Verification"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        readonly=True,
        tracking=True,
    )
    progress_notes = fields.Text()
    completion_summary = fields.Text()
    verification_evidence = fields.Text()
    submitted_by_id = fields.Many2one("res.users", readonly=True)
    submitted_date = fields.Datetime(readonly=True)
    verified_by_id = fields.Many2one("res.users", readonly=True)
    verified_date = fields.Datetime(readonly=True)

    _assessment_line_action_uniq = models.Constraint(
        "UNIQUE(assessment_line_id)",
        "Each gap assessment area may generate only one transition action.",
    )

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError(
                "Only QMS Managers or Administrators can manage ISO 9001 transition actions."
            )

    def _write_workflow(self, vals):
        self.ensure_one()
        return super().write(vals)

    @api.model
    def _generate_from_assessment(self, assessment, lines):
        assessment.ensure_one()
        assessment._check_manager_permission()
        if assessment.state != "completed":
            raise AccessError("Transition actions can be generated only from a completed assessment.")
        if lines - assessment.line_ids:
            raise AccessError("Transition action lines must belong to the selected assessment.")
        invalid = lines.filtered(lambda line: line.status not in ("partial", "gap"))
        if invalid:
            raise AccessError("Only partial or gap areas can generate transition actions.")

        existing_by_line = {
            action.assessment_line_id.id: action
            for action in self.search([("assessment_id", "=", assessment.id)])
        }
        created = self.browse()
        for line in lines:
            if line.id in existing_by_line:
                continue
            created |= super().create(
                {
                    "name": line.focus_name_snapshot,
                    "code": self.env["ir.sequence"].next_by_code(
                        "pm.qms.iso9001.transition.action"
                    )
                    or "ISO-ACT-00000",
                    "assessment_id": assessment.id,
                    "assessment_line_id": line.id,
                    "company_id": assessment.company_id.id,
                    "focus_code_snapshot": line.focus_code,
                    "focus_name_snapshot": line.focus_name_snapshot,
                    "gap_description_snapshot": line.gap_description,
                    "action_plan_snapshot": line.action_plan,
                    "source_status_snapshot": line.status,
                    "owner_id": line.responsible_id.id,
                    "target_date": line.target_date,
                    "priority": "2" if line.status == "gap" else "1",
                }
            )
        return created

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(
            "Generate transition actions from a completed ISO 9001 gap assessment."
        )

    @api.constrains(
        "assessment_id",
        "assessment_line_id",
        "company_id",
        "implementation_project_id",
    )
    def _check_relationships(self):
        for action in self:
            if action.assessment_line_id.assessment_id != action.assessment_id:
                raise ValidationError(
                    "Transition action assessment area must belong to its assessment."
                )
            if action.assessment_id.company_id != action.company_id:
                raise ValidationError(
                    "Transition action company must match its assessment company."
                )
            project = action.implementation_project_id
            if project and project.company_id != action.company_id:
                raise ValidationError(
                    "Transition action implementation project must belong to the same company."
                )

    def action_start(self):
        self._check_manager_permission()
        for action in self:
            if action.state != "draft":
                raise UserError("Only draft transition actions can be started.")
            action._write_workflow({"state": "in_progress"})
        return True

    def action_submit_verification(self):
        self._check_manager_permission()
        for action in self:
            if action.state not in ("draft", "in_progress"):
                raise UserError(
                    "Only draft or in-progress transition actions can be submitted for verification."
                )
            if not action.completion_summary or not action.verification_evidence:
                raise UserError(
                    "Completion summary and verification evidence are required before verification."
                )
            action._write_workflow(
                {
                    "state": "verification",
                    "submitted_by_id": self.env.user.id,
                    "submitted_date": fields.Datetime.now(),
                }
            )
        return True

    def action_complete(self):
        self._check_manager_permission()
        for action in self:
            if action.state != "verification":
                raise UserError(
                    "Only transition actions awaiting verification can be completed."
                )
            action._write_workflow(
                {
                    "state": "completed",
                    "verified_by_id": self.env.user.id,
                    "verified_date": fields.Datetime.now(),
                }
            )
        return True

    def action_cancel(self):
        self._check_manager_permission()
        for action in self:
            if action.state == "completed":
                raise UserError("Completed transition actions are immutable.")
            action._write_workflow({"state": "cancelled"})
        return True

    def write(self, vals):
        if any(action.state == "completed" for action in self):
            raise AccessError("Completed ISO 9001 transition actions are immutable.")
        workflow_fields = {
            "state",
            "submitted_by_id",
            "submitted_date",
            "verified_by_id",
            "verified_date",
            "assessment_id",
            "assessment_line_id",
            "company_id",
            "focus_code_snapshot",
            "focus_name_snapshot",
            "gap_description_snapshot",
            "action_plan_snapshot",
            "source_status_snapshot",
            "code",
        }
        if workflow_fields.intersection(vals):
            raise AccessError("Workflow and snapshot fields cannot be changed directly.")
        self._check_manager_permission()
        return super().write(vals)

    def unlink(self):
        self._check_manager_permission()
        if any(action.state not in ("draft", "cancelled") for action in self):
            raise UserError("Only draft or cancelled transition actions can be deleted.")
        return super().unlink()

    def copy(self, default=None):
        raise UserError("Transition actions cannot be copied.")
