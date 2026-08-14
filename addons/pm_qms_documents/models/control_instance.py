from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    document_ids = fields.Many2many(
        "pm.qms.document",
        "pm_qms_doc_instance_rel",
        "control_instance_id",
        "document_id",
        string="Related Controlled Documents",
    )
    document_count = fields.Integer(compute="_compute_document_count")

    def _compute_document_count(self):
        for instance in self:
            instance.document_count = len(instance.document_ids)
