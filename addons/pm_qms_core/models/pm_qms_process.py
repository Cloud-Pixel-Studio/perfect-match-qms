from odoo import fields, models


class PmQmsProcess(models.Model):
    _name = "pm.qms.process"
    _description = "Perfect Match QMS Process"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False, tracking=True)
    description = fields.Text()
    owner_id = fields.Many2one("res.users", string="Process Owner", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    parent_id = fields.Many2one("pm.qms.process", string="Parent Process", index=True)
    child_ids = fields.One2many("pm.qms.process", "parent_id", string="Child Processes")
    control_ids = fields.One2many("pm.qms.control", "process_id", string="Controls")
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Process code must be unique per company.",
    )
