from odoo import api, models

from .. import hooks


class PmQmsFrameworkPack(models.Model):
    _inherit = "pm.qms.framework.pack"

    @api.model
    def pm_qms_seed_quality_guided_readiness(self):
        hooks.seed_quality_guided_readiness(self.env)
        return True
