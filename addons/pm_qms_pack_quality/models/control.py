from odoo import fields, models


class PmQmsControl(models.Model):
    _inherit = "pm.qms.control"

    pm_control_domain = fields.Char(
        string="Perfect Match Domain",
        help="Perfect Match implementation domain. This is proprietary methodology metadata, not an external clause title.",
    )
    pm_supported_capability = fields.Char(
        string="Supported Capability",
        help="Lightweight pointer to the Perfect Match operational capability that supports this control.",
    )
