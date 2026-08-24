from odoo import api, models


class PmQmsSiteLicense(models.Model):
    _inherit = "pm.qms.site"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["pm.qms.entitlement.service"].enforce_sites(records)
        return records

    def write(self, vals):
        result = super().write(vals)
        if {"active", "organization_id", "company_id"}.intersection(vals):
            self.env["pm.qms.entitlement.service"].enforce_sites(self)
        return result
