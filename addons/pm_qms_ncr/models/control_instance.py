from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    nonconformity_ids = fields.Many2many(
        "pm.qms.nonconformity",
        "pm_qms_ncr_control_instance_rel",
        "control_instance_id",
        "nonconformity_id",
        string="Nonconformities",
    )
    nonconformity_count = fields.Integer(compute="_compute_nonconformity_count")

    def _compute_nonconformity_count(self):
        for instance in self:
            instance.nonconformity_count = len(instance.nonconformity_ids)
