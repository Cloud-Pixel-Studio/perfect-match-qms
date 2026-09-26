from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsIso9001GapAssessment(models.Model):
    _inherit = "pm.qms.iso9001.gap.assessment"

    readiness_review_id = fields.Many2one(
        "pm.qms.iso9001.transition.review",
        compute="_compute_readiness_review",
        string="Transition Readiness Review",
    )

    def _compute_readiness_review(self):
        Review = self.env["pm.qms.iso9001.transition.review"]
        for assessment in self:
            assessment.readiness_review_id = Review.search(
                [("assessment_id", "=", assessment.id)], limit=1
            )

    def action_prepare_readiness_review(self):
        self.ensure_one()
        self._check_manager_permission()
        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            self
        )
        return {
            "type": "ir.actions.act_window",
            "name": "ISO 9001 Transition Readiness Review",
            "res_model": "pm.qms.iso9001.transition.review",
            "res_id": review.id,
            "view_mode": "form",
        }


class PmQmsIso9001TransitionReview(models.Model):
    _name = "pm.qms.iso9001.transition.review"
    _description = "PM-QMS ISO 9001 Transition Readiness Review"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "review_date desc, code desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, readonly=True, copy=False, index=True)
    assessment_id = fields.Many2one(
        "pm.qms.iso9001.gap.assessment",
        required=True,
        readonly=True,
        ondelete="restrict",
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
        required=True,
        readonly=True,
        ondelete="restrict",
        index=True,
    )
    review_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    reviewer_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    decision = fields.Selection(
        [
            ("hold", "Hold Transition"),
            ("continue_actions", "Continue Controlled Actions"),
            ("internal_review", "Proceed to Internal Review"),
        ],
        required=True,
        default="hold",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("returned", "Returned"),
        ],
        required=True,
        default="draft",
        readonly=True,
        tracking=True,
    )
    review_basis = fields.Text(required=True)
    residual_risk_summary = fields.Text(required=True)
    decision_notes = fields.Text(required=True)
    source_edition_snapshot = fields.Char(required=True, readonly=True)
    target_edition_snapshot = fields.Char(required=True, readonly=True)
    total_action_count_snapshot = fields.Integer(readonly=True)
    completed_action_count_snapshot = fields.Integer(readonly=True)
    open_action_count_snapshot = fields.Integer(readonly=True)
    submitted_by_id = fields.Many2one("res.users", readonly=True)
    submitted_date = fields.Datetime(readonly=True)
    approved_by_id = fields.Many2one("res.users", readonly=True)
    approved_date = fields.Datetime(readonly=True)
    returned_by_id = fields.Many2one("res.users", readonly=True)
    returned_date = fields.Datetime(readonly=True)
    return_reason = fields.Text(readonly=True)

    _assessment_review_uniq = models.Constraint(
        "UNIQUE(assessment_id)",
        "Each gap assessment may have only one transition readiness review.",
    )

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError(
                "Only QMS Managers or Administrators can manage transition readiness reviews."
            )

    def _write_workflow(self, vals):
        self.ensure_one()
        return super().write(vals)

    @api.model
    def _prepare_from_assessment(self, assessment):
        assessment.ensure_one()
        assessment._check_manager_permission()
        if assessment.state != "completed":
            raise UserError("Complete the gap assessment before preparing a readiness review.")
        actions = assessment.transition_action_ids
        if not actions:
            raise UserError("Generate the controlled transition actions before preparing a readiness review.")
        projects = actions.mapped("implementation_project_id")
        if len(projects) != 1:
            raise UserError(
                "All transition actions must reference the same implementation project."
            )
        existing = self.search([("assessment_id", "=", assessment.id)], limit=1)
        if existing:
            return existing
        return super().create(
            {
                "name": f"{assessment.name} - transition readiness review",
                "code": self.env["ir.sequence"].next_by_code(
                    "pm.qms.iso9001.transition.review"
                )
                or "ISO-TRR-00000",
                "assessment_id": assessment.id,
                "company_id": assessment.company_id.id,
                "implementation_project_id": projects.id,
                "reviewer_id": self.env.user.id,
                "review_basis": "Summarize the reviewed transition evidence and action results.",
                "residual_risk_summary": "Document remaining transition risks and controls.",
                "decision_notes": "Record the rationale for the selected internal transition decision.",
                "source_edition_snapshot": assessment.source_edition_snapshot,
                "target_edition_snapshot": assessment.target_edition_snapshot,
            }
        )

    @api.model_create_multi
    def create(self, vals_list):
        raise AccessError(
            "Prepare transition readiness reviews from a completed gap assessment."
        )

    @api.constrains(
        "assessment_id", "company_id", "implementation_project_id", "reviewer_id"
    )
    def _check_relationships(self):
        for review in self:
            if review.assessment_id.company_id != review.company_id:
                raise ValidationError("Readiness review company must match its assessment.")
            if review.implementation_project_id.company_id != review.company_id:
                raise ValidationError(
                    "Readiness review implementation project must belong to the same company."
                )
            action_projects = review.assessment_id.transition_action_ids.mapped(
                "implementation_project_id"
            )
            if action_projects != review.implementation_project_id:
                raise ValidationError(
                    "Readiness review project must match every transition action."
                )
            if not review.reviewer_id.has_group(
                "pm_qms_core.group_pm_qms_manager"
            ):
                raise ValidationError("The assigned reviewer must be a QMS Manager or Administrator.")

    def _action_counts(self):
        self.ensure_one()
        actions = self.assessment_id.transition_action_ids
        completed = actions.filtered(lambda action: action.state == "completed")
        return len(actions), len(completed), len(actions - completed)

    def action_submit(self):
        self._check_manager_permission()
        for review in self:
            if review.state not in ("draft", "returned"):
                raise UserError("Only draft or returned reviews can be submitted.")
            if review.reviewer_id == self.env.user:
                raise UserError("The submitter and assigned reviewer must be different users.")
            total, completed, open_count = review._action_counts()
            if not total:
                raise UserError("At least one controlled transition action is required.")
            review._write_workflow(
                {
                    "state": "submitted",
                    "total_action_count_snapshot": total,
                    "completed_action_count_snapshot": completed,
                    "open_action_count_snapshot": open_count,
                    "submitted_by_id": self.env.user.id,
                    "submitted_date": fields.Datetime.now(),
                    "approved_by_id": False,
                    "approved_date": False,
                    "returned_by_id": False,
                    "returned_date": False,
                    "return_reason": False,
                }
            )
        return True

    def action_approve(self):
        self._check_manager_permission()
        for review in self:
            if review.state != "submitted":
                raise UserError("Only submitted readiness reviews can be approved.")
            if review.reviewer_id != self.env.user:
                raise AccessError("Only the assigned independent reviewer can approve this review.")
            if review.submitted_by_id == self.env.user:
                raise AccessError("The submitter cannot approve their own readiness review.")
            total, completed, open_count = review._action_counts()
            if (
                total != review.total_action_count_snapshot
                or completed != review.completed_action_count_snapshot
                or open_count != review.open_action_count_snapshot
            ):
                raise UserError(
                    "Transition action status changed after submission; return and resubmit the review."
                )
            if review.decision == "internal_review" and open_count:
                raise UserError(
                    "All controlled transition actions must be completed before proceeding to internal review."
                )
            if review.decision == "continue_actions" and not open_count:
                raise UserError(
                    "Use the internal-review decision when no transition actions remain open."
                )
            review._write_workflow(
                {
                    "state": "approved",
                    "approved_by_id": self.env.user.id,
                    "approved_date": fields.Datetime.now(),
                }
            )
        return True

    def action_return(self):
        self._check_manager_permission()
        for review in self:
            if review.state != "submitted":
                raise UserError("Only submitted readiness reviews can be returned.")
            if review.reviewer_id != self.env.user:
                raise AccessError("Only the assigned independent reviewer can return this review.")
            if not review.return_reason:
                raise UserError("Document a return reason before returning the review.")
            review._write_workflow(
                {
                    "state": "returned",
                    "returned_by_id": self.env.user.id,
                    "returned_date": fields.Datetime.now(),
                }
            )
        return True

    def write(self, vals):
        if any(review.state == "approved" for review in self):
            raise AccessError("Approved transition readiness reviews are immutable.")
        workflow_fields = {
            "state",
            "assessment_id",
            "company_id",
            "implementation_project_id",
            "code",
            "source_edition_snapshot",
            "target_edition_snapshot",
            "total_action_count_snapshot",
            "completed_action_count_snapshot",
            "open_action_count_snapshot",
            "submitted_by_id",
            "submitted_date",
            "approved_by_id",
            "approved_date",
            "returned_by_id",
            "returned_date",
        }
        if workflow_fields.intersection(vals):
            raise AccessError("Workflow and snapshot fields cannot be changed directly.")
        if any(review.state == "submitted" for review in self):
            allowed = {"return_reason"}
            if set(vals) - allowed:
                raise AccessError("Submitted readiness reviews are locked pending reviewer action.")
        self._check_manager_permission()
        return super().write(vals)

    def unlink(self):
        self._check_manager_permission()
        if any(review.state not in ("draft", "returned") for review in self):
            raise UserError("Only draft or returned readiness reviews can be deleted.")
        return super().unlink()

    def copy(self, default=None):
        raise UserError("Transition readiness reviews cannot be copied.")
