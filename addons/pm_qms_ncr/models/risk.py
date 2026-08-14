from odoo import fields, models


class PmQmsRisk(models.Model):
    _inherit = "pm.qms.risk"

    nonconformity_ids = fields.Many2many(
        "pm.qms.nonconformity",
        "pm_qms_ncr_risk_rel",
        "risk_id",
        "nonconformity_id",
        string="Related NCRs",
    )
