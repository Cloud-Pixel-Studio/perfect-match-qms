from odoo import fields, models


class PmQmsOrganization(models.Model):
    _name = "pm.qms.organization"
    _description = "Perfect Match QMS Organization"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False, tracking=True)
    description = fields.Text()
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    process_ids = fields.One2many("pm.qms.process", "organization_id", string="Processes")
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Organization code must be unique per company.",
    )
