from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    capa_ids = fields.Many2many(
        "pm.qms.capa",
        "pm_qms_capa_control_instance_rel",
        "control_instance_id",
        "capa_id",
        string="CAPAs",
    )
    capa_count = fields.Integer(compute="_compute_capa_count")

    def _compute_capa_count(self):
        for instance in self:
            instance.capa_count = len(instance.capa_ids)
