from odoo import api, models
from odoo.exceptions import UserError

from ..hooks import (
    seed_iso9001_initial_implementation,
    seed_iso9001_transition_scenarios,
    seed_iso9001_2026_implementation_pack,
    ISO9001_2026_PACK_CODE,
)


class PmQmsIso9001FrameworkPack(models.Model):
    _inherit = "pm.qms.framework.pack"

    @api.model
    def seed_iso9001_initial_implementation(self):
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_transition_scenarios(self.env)
        seed_iso9001_2026_implementation_pack(self.env)
        return True

    def action_activate(self):
        if any(pack.code == ISO9001_2026_PACK_CODE for pack in self):
            raise UserError(
                "The ISO 9001:2026 pack is a review draft and cannot be activated "
                "until competent practitioner review and a separate approved release."
            )
        return super().action_activate()
