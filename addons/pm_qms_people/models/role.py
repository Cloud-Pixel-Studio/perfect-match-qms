from odoo import fields, models


class PmQmsRole(models.Model):
    _name = "pm.qms.role"
    _description = "Perfect Match QMS Role"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    description = fields.Text()
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    organization_id = fields.Many2one(
        "pm.qms.organization",
        help="Leave blank for a company-level role reusable across QMS organizations.",
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean(default=True)
    person_assignment_ids = fields.One2many("pm.qms.person.role.assignment", "role_id")
    competency_requirement_ids = fields.One2many("pm.qms.role.competency.requirement", "role_id")
    document_ack_requirement_ids = fields.One2many("pm.qms.role.document.requirement", "role_id")
    training_requirement_ids = fields.One2many("pm.qms.training.requirement", "role_id")

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "QMS role code must be unique per company.",
    )
