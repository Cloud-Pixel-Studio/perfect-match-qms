from odoo import fields, models


class PmQmsProcess(models.Model):
    _name = "pm.qms.process"
    _description = "Perfect Match QMS Process"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, code, name"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False, tracking=True)
    description = fields.Text()
    process_owner_id = fields.Many2one("res.users", string="Process Owner", tracking=True)
    organization_id = fields.Many2one("pm.qms.organization", string="Organization", index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    parent_id = fields.Many2one("pm.qms.process", string="Parent Process", index=True)
    child_ids = fields.One2many("pm.qms.process", "parent_id", string="Child Processes")
    control_ids = fields.One2many("pm.qms.control", "process_id", string="Controls")
    control_instance_ids = fields.One2many(
        "pm.qms.control.instance",
        "process_id",
        string="Control Instances",
    )
    department = fields.Char()
    process_type = fields.Selection(
        [
            ("management", "Management"),
            ("core", "Core"),
            ("support", "Support"),
            ("other", "Other"),
        ],
        default="core",
    )
    inputs = fields.Text()
    outputs = fields.Text()
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Process code must be unique per company.",
    )
