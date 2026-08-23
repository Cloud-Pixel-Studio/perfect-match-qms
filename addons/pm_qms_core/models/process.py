from odoo import api, fields, models
from odoo.exceptions import ValidationError


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
    site_ids = fields.Many2many(
        "pm.qms.site",
        "pm_qms_process_site_rel",
        "process_id",
        "site_id",
        string="Applicable Sites",
        domain="[('organization_id', '=', organization_id)]",
    )
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

    @api.constrains("organization_id", "company_id", "site_ids")
    def _check_site_alignment(self):
        for process in self:
            if process.organization_id and process.organization_id.company_id != process.company_id:
                raise ValidationError("Process organization must belong to the same company.")
            if process.site_ids and not process.organization_id:
                raise ValidationError("Applicable sites require an organization.")
            for site in process.site_ids:
                if site.organization_id != process.organization_id or site.company_id != process.company_id:
                    raise ValidationError("Applicable sites must belong to the process organization and company.")
