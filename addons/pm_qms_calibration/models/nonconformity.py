from odoo import fields, models


class PmQmsNonconformity(models.Model):
    _inherit = "pm.qms.nonconformity"

    calibration_event_id = fields.Many2one("pm.qms.calibration.event", string="Calibration Event", ondelete="restrict")
    calibration_impact_assessment_id = fields.Many2one(
        "pm.qms.calibration.impact.assessment",
        string="OOT Impact Assessment",
        ondelete="restrict",
    )
    equipment_id = fields.Many2one(related="calibration_event_id.equipment_id", store=True, readonly=True)
