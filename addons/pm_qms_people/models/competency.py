from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsCompetency(models.Model):
    _name = "pm.qms.competency"
    _description = "Perfect Match QMS Competency"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    description = fields.Text()
    category = fields.Char()
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Competency code must be unique per company.",
    )


class PmQmsRoleCompetencyRequirement(models.Model):
    _name = "pm.qms.role.competency.requirement"
    _description = "Perfect Match QMS Role Competency Requirement"
    _order = "role_id, competency_id"

    role_id = fields.Many2one("pm.qms.role", required=True, ondelete="cascade", index=True)
    competency_id = fields.Many2one("pm.qms.competency", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="role_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="role_id.organization_id", store=True, readonly=True, index=True)
    required = fields.Boolean(default=True)
    valid_months = fields.Integer(string="Assessment Validity (Months)")
    notes = fields.Text()

    _role_competency_uniq = models.Constraint(
        "UNIQUE(role_id, competency_id)",
        "A competency can be required only once per QMS role.",
    )

    @api.constrains("role_id", "competency_id", "valid_months")
    def _check_requirement(self):
        for requirement in self:
            if requirement.competency_id.company_id != requirement.company_id:
                raise ValidationError("Competency must belong to the same company as the QMS role.")
            if requirement.valid_months < 0:
                raise ValidationError("Assessment validity cannot be negative.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["pm.qms.competency.matrix.line"].sync_for_requirements(records)
        return records

    def write(self, vals):
        result = super().write(vals)
        self.env["pm.qms.competency.matrix.line"].sync_for_requirements(self)
        return result


class PmQmsCompetencyAssessment(models.Model):
    _name = "pm.qms.competency.assessment"
    _description = "Perfect Match QMS Competency Assessment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "assessment_date desc, id desc"

    person_id = fields.Many2one("pm.qms.person", required=True, ondelete="restrict", index=True)
    competency_id = fields.Many2one("pm.qms.competency", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="person_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="person_id.organization_id", store=True, readonly=True, index=True)
    assessment_date = fields.Date(default=fields.Date.context_today, required=True)
    assessor_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    result = fields.Selection(
        [
            ("competent", "Competent"),
            ("gap", "Gap"),
            ("not_assessed", "Not Assessed"),
        ],
        required=True,
        default="not_assessed",
        tracking=True,
    )
    level = fields.Char()
    valid_until = fields.Date()
    evidence_id = fields.Many2one("pm.qms.evidence")
    notes = fields.Text()

    @api.constrains("person_id", "competency_id", "assessment_date", "valid_until")
    def _check_assessment(self):
        for assessment in self:
            if assessment.competency_id.company_id != assessment.company_id:
                raise ValidationError("Competency assessment must use a competency from the person's company.")
            if assessment.valid_until and assessment.valid_until < assessment.assessment_date:
                raise ValidationError("Competency assessment valid-until date cannot be before assessment date.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["pm.qms.competency.matrix.line"].sync_for_people(records.mapped("person_id"))
        return records

    def write(self, vals):
        result = super().write(vals)
        self.env["pm.qms.competency.matrix.line"].sync_for_people(self.mapped("person_id"))
        return result


class PmQmsCompetencyMatrixLine(models.Model):
    _name = "pm.qms.competency.matrix.line"
    _description = "Perfect Match QMS Competency Matrix Line"
    _order = "person_id, competency_id, role_id"

    person_id = fields.Many2one("pm.qms.person", required=True, ondelete="cascade", index=True)
    role_id = fields.Many2one("pm.qms.role", required=True, ondelete="cascade", index=True)
    requirement_id = fields.Many2one("pm.qms.role.competency.requirement", required=True, ondelete="cascade", index=True)
    competency_id = fields.Many2one(related="requirement_id.competency_id", store=True, readonly=True, index=True)
    company_id = fields.Many2one(related="person_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="person_id.organization_id", store=True, readonly=True, index=True)
    latest_assessment_id = fields.Many2one("pm.qms.competency.assessment", compute="_compute_current_status", store=True)
    status = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("not_assessed", "Not Assessed"),
            ("competent", "Competent"),
            ("gap", "Gap"),
            ("expired", "Expired"),
        ],
        compute="_compute_current_status",
        store=True,
    )
    assessment_valid_until = fields.Date(compute="_compute_current_status", store=True)

    _person_requirement_uniq = models.Constraint(
        "UNIQUE(person_id, requirement_id)",
        "A competency matrix line can exist only once for a person and role requirement.",
    )

    @api.depends(
        "person_id.competency_assessment_ids.result",
        "person_id.competency_assessment_ids.assessment_date",
        "person_id.competency_assessment_ids.valid_until",
        "requirement_id.required",
    )
    def _compute_current_status(self):
        today = fields.Date.context_today(self)
        Assessment = self.env["pm.qms.competency.assessment"]
        for line in self:
            line.latest_assessment_id = False
            line.assessment_valid_until = False
            if not line.requirement_id.required:
                line.status = "not_required"
                continue
            assessment = Assessment.search(
                [
                    ("person_id", "=", line.person_id.id),
                    ("competency_id", "=", line.competency_id.id),
                ],
                order="assessment_date desc, id desc",
                limit=1,
            )
            line.latest_assessment_id = assessment
            line.assessment_valid_until = assessment.valid_until
            if not assessment or assessment.result == "not_assessed":
                line.status = "not_assessed"
            elif assessment.result == "gap":
                line.status = "gap"
            elif assessment.valid_until and assessment.valid_until < today:
                line.status = "expired"
            else:
                line.status = "competent"

    @api.model
    def sync_for_people(self, people):
        people = people.exists()
        Requirement = self.env["pm.qms.role.competency.requirement"]
        for person in people:
            active_roles = person.active_role_ids
            requirements = Requirement.search([("role_id", "in", active_roles.ids)])
            expected_requirement_ids = set(requirements.ids)
            existing = self.search([("person_id", "=", person.id)])
            for requirement in requirements:
                if not existing.filtered(lambda line, requirement=requirement: line.requirement_id == requirement):
                    self.create(
                        {
                            "person_id": person.id,
                            "role_id": requirement.role_id.id,
                            "requirement_id": requirement.id,
                        }
                    )
            stale = existing.filtered(lambda line: line.requirement_id.id not in expected_requirement_ids)
            stale.unlink()
        return True

    @api.model
    def sync_for_requirements(self, requirements):
        people = self.env["pm.qms.person"].search([("role_assignment_ids.role_id", "in", requirements.mapped("role_id").ids)])
        return self.sync_for_people(people)
