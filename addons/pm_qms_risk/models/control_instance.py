from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    risk_ids = fields.Many2many(
        "pm.qms.risk",
        "pm_qms_risk_control_instance_rel",
        "control_instance_id",
        "risk_id",
        string="Risks and Opportunities",
    )
    risk_count = fields.Integer(compute="_compute_risk_count")

    def _compute_risk_count(self):
        for instance in self:
            instance.risk_count = len(instance.risk_ids)
