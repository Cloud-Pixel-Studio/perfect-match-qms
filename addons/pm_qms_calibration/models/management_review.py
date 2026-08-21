from odoo import fields, models


class PmQmsManagementReview(models.Model):
    _inherit = "pm.qms.management.review"

    def _generate_snapshot_inputs(self, snapshot_date):
        result = super()._generate_snapshot_inputs(snapshot_date)
        for review in self:
            review._snapshot_calibration(snapshot_date)
        return result

    def _snapshot_calibration(self, snapshot_date):
        self.ensure_one()
        Equipment = self.env["pm.qms.equipment"]
        Assessment = self.env["pm.qms.calibration.impact.assessment"]
        base_domain = self._base_domain()
        equipment = Equipment.search(base_domain + [("calibration_required", "=", True)])
        overdue = equipment.filtered(lambda item: item.calibration_status == "overdue")
        due_soon = equipment.filtered(lambda item: item.calibration_status in ("due", "due_soon"))
        quarantined = equipment.filtered(lambda item: item.lifecycle_state == "quarantined")
        open_assessments = Assessment.search(base_domain + [("state", "not in", ("closed", "cancelled"))])
        if equipment or open_assessments:
            self._create_input(
                "resources",
                "Calibration and monitoring resource status",
                "resource",
                snapshot_date=snapshot_date,
                description="Monitoring and measuring resource calibration status snapshot.",
                status_snapshot="attention" if overdue or quarantined or open_assessments else "current",
                numeric_value=len(overdue) + len(quarantined) + len(open_assessments),
                unit_of_measure="records needing attention",
                text_value=(
                    f"Resources requiring calibration: {len(equipment)}; "
                    f"due soon: {len(due_soon)}; overdue: {len(overdue)}; "
                    f"quarantined: {len(quarantined)}; open OOT assessments: {len(open_assessments)}"
                ),
                source_identifier="PM-QMS-CALIBRATION",
            )
