from odoo import api, models


class PmQmsOrganizationLicense(models.Model):
    _inherit = "pm.qms.organization"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["pm.qms.entitlement.service"].enforce_organization(records)
        return records

    def write(self, vals):
        result = super().write(vals)
        if {"active", "organization_kind", "company_id"}.intersection(vals):
            self.env["pm.qms.entitlement.service"].enforce_organization(self)
        return result
