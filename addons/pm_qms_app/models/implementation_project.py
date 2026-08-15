from odoo import models


class PmQmsImplementationProject(models.Model):
    _inherit = "pm.qms.implementation.project"

    def _qms_action(self, xmlid, domain=None, context=None, name=None):
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        if domain is not None:
            action["domain"] = domain
        if context is not None:
            action["context"] = context
        if name:
            action["name"] = name
        return action

    def action_view_controls(self):
        self.ensure_one()
        return self._qms_action(
            "pm_qms_implementation.action_pm_qms_implementation_control",
            domain=[("implementation_project_id", "=", self.id)],
            context={"default_implementation_project_id": self.id},
            name="Controls",
        )

    def action_view_activities(self):
        self.ensure_one()
        return self._qms_action(
            "pm_qms_implementation.action_pm_qms_generated_task",
            domain=[("pm_implementation_project_id", "=", self.id), ("pm_generated", "=", True)],
            context={"default_pm_implementation_project_id": self.id, "default_project_id": self.odoo_project_id.id},
            name="Activities",
        )

    def action_view_evidence(self):
        self.ensure_one()
        control_instance_ids = self.implementation_control_ids.mapped("control_instance_id").ids
        return self._qms_action(
            "pm_qms_evidence.action_pm_qms_evidence",
            domain=[("control_instance_id", "in", control_instance_ids)] if control_instance_ids else [("id", "=", 0)],
            name="Evidence",
        )

    def action_view_readiness_assessments(self):
        self.ensure_one()
        return self._qms_action(
            "pm_qms_implementation.action_pm_qms_readiness_assessment",
            domain=[("implementation_project_id", "=", self.id)],
            context={"default_implementation_project_id": self.id},
            name="Readiness Assessments",
        )
