from odoo import fields, models


class PmQmsEvidence(models.Model):
    _inherit = "pm.qms.evidence"

    calibration_event_ids = fields.Many2many(
        "pm.qms.calibration.event",
        "pm_qms_cal_event_evidence_rel",
        "evidence_id",
        "event_id",
        string="Calibration Events",
    )
    equipment_ids = fields.Many2many(
        "pm.qms.equipment",
        compute="_compute_calibration_equipment_ids",
        string="Monitoring Resources",
    )

    def _compute_calibration_equipment_ids(self):
        for evidence in self:
            evidence.equipment_ids = evidence.calibration_event_ids.mapped("equipment_id")
