from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsOrganization(models.Model):
    _name = "pm.qms.organization"
    _description = "Perfect Match QMS Organization"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False, tracking=True)
    description = fields.Text()
    qms_scope = fields.Text(string="QMS Scope", tracking=True)
    organization_kind = fields.Selection(
        [
            ("operational", "Operational Customer Organization"),
            ("framework", "Framework / Internal Organization"),
        ],
        required=True,
        default="operational",
        tracking=True,
        help="Only operational customer organizations consume a commercial company entitlement.",
    )
    quality_contact_id = fields.Many2one(
        "res.users",
        string="Primary Quality Contact",
        domain="[('company_ids', 'in', company_id)]",
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    process_ids = fields.One2many("pm.qms.process", "organization_id", string="Processes")
    site_ids = fields.One2many("pm.qms.site", "organization_id", string="Sites")
    control_instance_ids = fields.One2many(
        "pm.qms.control.instance",
        "organization_id",
        string="Control Instances",
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Organization code must be unique per company.",
    )

    @api.constrains("company_id", "quality_contact_id")
    def _check_quality_contact_alignment(self):
        for organization in self:
            if (
                organization.quality_contact_id
                and organization.company_id not in organization.quality_contact_id.company_ids
            ):
                raise ValidationError("The primary quality contact must be allowed for the organization company.")
