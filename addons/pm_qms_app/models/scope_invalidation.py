from odoo import api, models


class PmQmsOrganizationScopeInvalidation(models.Model):
    _inherit = "pm.qms.organization"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.user.invalidate_recordset(
            ["qms_effective_organization_ids", "qms_effective_site_ids", "qms_effective_process_ids"]
        )
        return records


class PmQmsSiteScopeInvalidation(models.Model):
    _inherit = "pm.qms.site"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.user.invalidate_recordset(
            ["qms_effective_site_ids", "qms_effective_process_ids"]
        )
        return records


class PmQmsProcessScopeInvalidation(models.Model):
    _inherit = "pm.qms.process"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.user.invalidate_recordset(
            ["qms_effective_process_ids"]
        )
        return records
