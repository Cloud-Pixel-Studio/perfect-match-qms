from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PmQmsSite(models.Model):
    _name = "pm.qms.site"
    _description = "Perfect Match QMS Site"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "organization_id, is_primary desc, code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, copy=False, tracking=True)
    organization_id = fields.Many2one(
        "pm.qms.organization",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    site_type = fields.Selection(
        [
            ("headquarters", "Headquarters"),
            ("manufacturing", "Manufacturing"),
            ("warehouse", "Warehouse"),
            ("laboratory", "Laboratory"),
            ("inspection", "Inspection"),
            ("distribution", "Distribution"),
            ("office", "Office"),
            ("other", "Other"),
        ],
        required=True,
        default="other",
        tracking=True,
    )
    partner_id = fields.Many2one("res.partner", string="Address / Contact", ondelete="restrict")
    timezone = fields.Char(string="Timezone")
    phone = fields.Char()
    email = fields.Char()
    manager_id = fields.Many2one("res.users", string="Site Manager", ondelete="restrict")
    is_primary = fields.Boolean(string="Primary / Headquarters", tracking=True)
    description = fields.Text()
    notes = fields.Text()
    active = fields.Boolean(default=True, tracking=True)

    _code_organization_uniq = models.Constraint(
        "UNIQUE(code, organization_id)",
        "Site code must be unique per organization.",
    )

    @api.constrains("organization_id", "partner_id", "manager_id")
    def _check_alignment(self):
        for site in self:
            if site.partner_id.company_id and site.partner_id.company_id != site.company_id:
                raise ValidationError("Site address / contact must belong to the same company as the organization.")
            if site.manager_id and site.company_id not in site.manager_id.company_ids:
                raise ValidationError("The site manager must be allowed for the site company.")

    @api.constrains("organization_id", "is_primary", "active")
    def _check_primary_site(self):
        for site in self.filtered(lambda item: item.active and item.is_primary):
            duplicate = self.search(
                [
                    ("organization_id", "=", site.organization_id.id),
                    ("is_primary", "=", True),
                    ("active", "=", True),
                    ("id", "!=", site.id),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError("An organization can have at most one active primary site.")

    def unlink(self):
        for site in self:
            if site.active:
                raise UserError("Archive a site before deleting it so operational history is preserved.")
            process_model = self.env.registry.get("pm.qms.process")
            if process_model and self.env["pm.qms.process"].search_count([("site_ids", "in", site.id)]):
                raise UserError("A site referenced by processes cannot be deleted.")
            equipment_model = self.env.registry.get("pm.qms.equipment")
            if equipment_model and self.env["pm.qms.equipment"].search_count([("site_id", "=", site.id)]):
                raise UserError("A site referenced by monitoring resources cannot be deleted.")
        return super().unlink()
