from odoo import models

from .framework_pack import ISO9001_2026_PACK_CODE, is_authorized_demo_2026_preview


class PmQmsIso9001ImplementationProject(models.Model):
    _inherit = "pm.qms.implementation.project"

    def _is_pack_usable_for_project(self, pack):
        if pack.code == ISO9001_2026_PACK_CODE and pack.state == "demo_preview":
            return is_authorized_demo_2026_preview(self.env)
        return super()._is_pack_usable_for_project(pack)
