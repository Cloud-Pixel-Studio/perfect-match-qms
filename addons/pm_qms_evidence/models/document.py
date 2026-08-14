from odoo import fields, models


class PmQmsDocument(models.Model):
    _inherit = "pm.qms.document"

    evidence_ids = fields.Many2many(
        "pm.qms.evidence",
        "pm_qms_evidence_document_rel",
        "document_id",
        "evidence_id",
        string="Evidence Records",
    )
