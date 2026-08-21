from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsPerson(models.Model):
    _name = "pm.qms.person"
    _description = "Perfect Match QMS Person"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name, id"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    partner_id = fields.Many2one("res.partner", string="Business Contact", ondelete="restrict", tracking=True)
    user_id = fields.Many2one("res.users", string="Odoo User", ondelete="restrict", tracking=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    role_assignment_ids = fields.One2many("pm.qms.person.role.assignment", "person_id", string="Role Assignments")
    active_role_ids = fields.Many2many(
        "pm.qms.role",
        compute="_compute_active_role_ids",
        string="Active QMS Roles",
    )
    competency_assessment_ids = fields.One2many("pm.qms.competency.assessment", "person_id")
    training_record_ids = fields.One2many("pm.qms.training.record", "person_id")
    qualification_record_ids = fields.One2many("pm.qms.qualification.record", "person_id")
    acknowledgment_ids = fields.One2many("pm.qms.document.acknowledgment", "person_id")

    competency_gap_count = fields.Integer(compute="_compute_attention_counts")
    overdue_training_count = fields.Integer(compute="_compute_attention_counts")
    expiring_qualification_count = fields.Integer(compute="_compute_attention_counts")
    pending_acknowledgment_count = fields.Integer(compute="_compute_attention_counts")

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "QMS person code must be unique per company.",
    )
    _user_company_uniq = models.Constraint(
        "UNIQUE(user_id, company_id)",
        "An Odoo user can be linked to only one QMS person per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.person") or "PM-PER-00000"
            if not vals.get("name"):
                partner = self.env["res.partner"].browse(vals.get("partner_id")).exists()
                user = self.env["res.users"].browse(vals.get("user_id")).exists()
                vals["name"] = partner.name or user.name
        return super().create(vals_list)

    @api.depends("role_assignment_ids.active", "role_assignment_ids.role_id")
    def _compute_active_role_ids(self):
        today = fields.Date.context_today(self)
        for person in self:
            assignments = person.role_assignment_ids.filtered(
                lambda item: item.active
                and item.role_id.active
                and (not item.effective_date or item.effective_date <= today)
                and (not item.end_date or item.end_date >= today)
            )
            person.active_role_ids = assignments.mapped("role_id")

    def _compute_attention_counts(self):
        Matrix = self.env["pm.qms.competency.matrix.line"]
        Training = self.env["pm.qms.training.record"]
        Qualification = self.env["pm.qms.qualification.record"]
        Acknowledgment = self.env["pm.qms.document.acknowledgment"]
        today = fields.Date.context_today(self)
        for person in self:
            person.competency_gap_count = Matrix.search_count(
                [("person_id", "=", person.id), ("status", "in", ("gap", "not_assessed", "expired"))]
            )
            person.overdue_training_count = Training.search_count(
                [("person_id", "=", person.id), ("state", "in", ("required", "scheduled")), ("due_date", "<", today)]
            )
            person.expiring_qualification_count = Qualification.search_count(
                [("person_id", "=", person.id), ("status", "in", ("expiring", "expired"))]
            )
            person.pending_acknowledgment_count = Acknowledgment.search_count(
                [("person_id", "=", person.id), ("state", "=", "pending")]
            )

    @api.constrains("organization_id", "partner_id", "user_id")
    def _check_identity_alignment(self):
        for person in self:
            if person.partner_id.company_id and person.partner_id.company_id != person.company_id:
                raise ValidationError("QMS person contact must belong to the same company as the organization.")
            if person.user_id and person.company_id not in person.user_id.company_ids:
                raise ValidationError("Linked Odoo user must be allowed for the person's company.")

    def action_sync_competency_matrix(self):
        return self.env["pm.qms.competency.matrix.line"].sync_for_people(self)

    def action_sync_acknowledgments(self):
        return self.env["pm.qms.document.acknowledgment"].sync_for_people(self)


class PmQmsPersonRoleAssignment(models.Model):
    _name = "pm.qms.person.role.assignment"
    _description = "Perfect Match QMS Person Role Assignment"
    _order = "person_id, effective_date desc, id desc"

    person_id = fields.Many2one("pm.qms.person", required=True, ondelete="cascade", index=True)
    role_id = fields.Many2one("pm.qms.role", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="person_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="person_id.organization_id", store=True, readonly=True, index=True)
    effective_date = fields.Date(default=fields.Date.context_today)
    end_date = fields.Date()
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _person_role_effective_uniq = models.Constraint(
        "UNIQUE(person_id, role_id, effective_date)",
        "A person can have only one assignment for the same QMS role and effective date.",
    )

    @api.constrains("person_id", "role_id", "effective_date", "end_date")
    def _check_assignment(self):
        for assignment in self:
            if assignment.role_id.company_id != assignment.company_id:
                raise ValidationError("QMS role must belong to the same company as the person.")
            if assignment.role_id.organization_id and assignment.role_id.organization_id != assignment.organization_id:
                raise ValidationError("Organization-specific QMS role must match the person's organization.")
            if assignment.end_date and assignment.effective_date and assignment.end_date < assignment.effective_date:
                raise ValidationError("Role assignment end date cannot be before the effective date.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.mapped("person_id").action_sync_competency_matrix()
        records.mapped("person_id").action_sync_acknowledgments()
        return records

    def write(self, vals):
        result = super().write(vals)
        self.mapped("person_id").action_sync_competency_matrix()
        self.mapped("person_id").action_sync_acknowledgments()
        return result
