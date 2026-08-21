from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsTrainingCourse(models.Model):
    _name = "pm.qms.training.course"
    _description = "Perfect Match QMS Training Definition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    description = fields.Text()
    training_type = fields.Selection(
        [
            ("awareness", "Awareness"),
            ("skill", "Skill"),
            ("qualification", "Qualification Support"),
            ("refresher", "Refresher"),
            ("other", "Other"),
        ],
        default="skill",
        required=True,
    )
    delivery_source = fields.Selection([("internal", "Internal"), ("external", "External")], default="internal")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    competency_ids = fields.Many2many(
        "pm.qms.competency",
        "pm_qms_training_course_competency_rel",
        "course_id",
        "competency_id",
        string="Related Competencies",
    )
    validity_months = fields.Integer()
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Training course code must be unique per company.",
    )

    @api.constrains("validity_months", "competency_ids")
    def _check_course(self):
        for course in self:
            if course.validity_months < 0:
                raise ValidationError("Training validity cannot be negative.")
            if any(competency.company_id != course.company_id for competency in course.competency_ids):
                raise ValidationError("Training competencies must belong to the same company as the course.")


class PmQmsTrainingEvent(models.Model):
    _name = "pm.qms.training.event"
    _description = "Perfect Match QMS Training Event"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "event_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    course_id = fields.Many2one("pm.qms.training.course", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="course_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", ondelete="restrict", index=True)
    event_date = fields.Date(default=fields.Date.context_today, required=True)
    instructor = fields.Char()
    provider = fields.Char()
    delivery_method = fields.Selection(
        [("classroom", "Classroom"), ("online", "Online"), ("on_the_job", "On the Job"), ("external", "External")],
        default="classroom",
    )
    location = fields.Char()
    state = fields.Selection(
        [("planned", "Planned"), ("completed", "Completed"), ("cancelled", "Cancelled")],
        default="planned",
        required=True,
        tracking=True,
    )
    participant_record_ids = fields.One2many("pm.qms.training.record", "event_id")
    notes = fields.Text()

    @api.constrains("organization_id", "course_id")
    def _check_event(self):
        for event in self:
            if event.organization_id and event.organization_id.company_id != event.company_id:
                raise ValidationError("Training event organization must belong to the course company.")


class PmQmsTrainingRequirement(models.Model):
    _name = "pm.qms.training.requirement"
    _description = "Perfect Match QMS Training Requirement"
    _order = "role_id, competency_id, course_id"

    role_id = fields.Many2one("pm.qms.role", ondelete="cascade", index=True)
    competency_id = fields.Many2one("pm.qms.competency", ondelete="cascade", index=True)
    course_id = fields.Many2one("pm.qms.training.course", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="course_id.company_id", store=True, readonly=True, index=True)
    required = fields.Boolean(default=True)
    due_within_days = fields.Integer(default=30)
    notes = fields.Text()

    @api.constrains("role_id", "competency_id", "course_id", "due_within_days")
    def _check_requirement(self):
        for requirement in self:
            if not requirement.role_id and not requirement.competency_id:
                raise ValidationError("Training requirement must be linked to a role or competency.")
            if requirement.role_id and requirement.role_id.company_id != requirement.company_id:
                raise ValidationError("Training role requirement must belong to the same company as the course.")
            if requirement.competency_id and requirement.competency_id.company_id != requirement.company_id:
                raise ValidationError("Training competency requirement must belong to the same company as the course.")
            if requirement.due_within_days < 0:
                raise ValidationError("Training due window cannot be negative.")


class PmQmsTrainingRecord(models.Model):
    _name = "pm.qms.training.record"
    _description = "Perfect Match QMS Person Training Record"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "completion_date desc, id desc"

    person_id = fields.Many2one("pm.qms.person", required=True, ondelete="restrict", index=True)
    course_id = fields.Many2one("pm.qms.training.course", required=True, ondelete="restrict", index=True)
    event_id = fields.Many2one("pm.qms.training.event", ondelete="restrict")
    requirement_id = fields.Many2one("pm.qms.training.requirement", ondelete="set null")
    company_id = fields.Many2one(related="person_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="person_id.organization_id", store=True, readonly=True, index=True)
    due_date = fields.Date()
    completion_date = fields.Date()
    result = fields.Selection(
        [
            ("satisfactory", "Satisfactory"),
            ("not_satisfactory", "Not Satisfactory"),
            ("not_completed", "Not Completed"),
        ],
        default="not_completed",
        required=True,
    )
    provider = fields.Char()
    certificate_attachment_id = fields.Many2one("ir.attachment", string="Training Record")
    valid_until = fields.Date(compute="_compute_valid_until", store=True)
    state = fields.Selection(
        [
            ("required", "Required"),
            ("scheduled", "Scheduled"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("expired", "Expired"),
            ("overdue", "Overdue"),
        ],
        compute="_compute_state",
        store=True,
    )
    effectiveness_review_required = fields.Boolean()
    effectiveness_reviewer_id = fields.Many2one("res.users")
    effectiveness_review_date = fields.Date()
    effectiveness_result = fields.Selection([("effective", "Effective"), ("not_effective", "Not Effective")])
    effectiveness_notes = fields.Text()
    notes = fields.Text()

    @api.depends("completion_date", "course_id.validity_months")
    def _compute_valid_until(self):
        for record in self:
            if record.completion_date and record.course_id.validity_months:
                record.valid_until = record.completion_date + relativedelta(months=record.course_id.validity_months)
            else:
                record.valid_until = False

    @api.depends("event_id.state", "completion_date", "result", "due_date", "valid_until")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.completion_date:
                if record.result == "not_satisfactory":
                    record.state = "failed"
                elif record.valid_until and record.valid_until < today:
                    record.state = "expired"
                else:
                    record.state = "completed"
            elif record.due_date and record.due_date < today:
                record.state = "overdue"
            elif record.event_id:
                record.state = "scheduled"
            else:
                record.state = "required"

    @api.constrains("person_id", "course_id", "event_id", "completion_date", "due_date")
    def _check_record(self):
        for record in self:
            if record.course_id.company_id != record.company_id:
                raise ValidationError("Training course must belong to the person's company.")
            if record.event_id and record.event_id.course_id != record.course_id:
                raise ValidationError("Training event must use the same course as the training record.")
            if record.completion_date and record.due_date and record.completion_date < record.due_date:
                continue
