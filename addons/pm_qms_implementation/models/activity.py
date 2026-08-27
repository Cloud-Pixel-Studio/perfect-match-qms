from odoo import models


class PmQmsImplementationActivity(models.Model):
    _inherit = "pm.qms.activity"

    def _sync_generated_task_required_flags(self):
        tasks = self.env["project.task"].search(
            [
                ("pm_generated", "=", True),
                ("pm_activity_id", "in", self.ids),
            ]
        )
        for task in tasks:
            task.pm_required = bool(
                task.pm_implementation_control_id.required
                and task.pm_activity_id.readiness_required
            )

    def write(self, vals):
        result = super().write(vals)
        if {"activity_kind", "readiness_required"}.intersection(vals):
            self._sync_generated_task_required_flags()
        return result
