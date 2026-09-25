from odoo import api, models

from ..hooks import (
    seed_iso9001_initial_implementation,
    seed_iso9001_transition_scenarios,
)


class PmQmsIso9001FrameworkPack(models.Model):
    _inherit = "pm.qms.framework.pack"

    @api.model
    def seed_iso9001_initial_implementation(self):
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_transition_scenarios(self.env)
        return True
