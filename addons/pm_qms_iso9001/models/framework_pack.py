from odoo import api, models

from ..hooks import seed_iso9001_initial_implementation


class PmQmsIso9001FrameworkPack(models.Model):
    _inherit = "pm.qms.framework.pack"

    @api.model
    def seed_iso9001_initial_implementation(self):
        seed_iso9001_initial_implementation(self.env)
        return True
