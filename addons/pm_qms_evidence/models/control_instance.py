from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    evidence_ids = fields.One2many("pm.qms.evidence", "control_instance_id", string="Evidence Records")
    required_evidence_count = fields.Integer(compute="_compute_evidence_completion")
    accepted_evidence_count = fields.Integer(compute="_compute_evidence_completion")
    missing_evidence_count = fields.Integer(compute="_compute_evidence_completion")

    def _compute_evidence_completion(self):
        for instance in self:
            required_requirements = instance.control_id.evidence_requirement_ids.filtered(
                lambda requirement: requirement.active and requirement.mandatory
            )
            accepted_requirements = instance.evidence_ids.filtered(
                lambda evidence: evidence.active and evidence.state == "accepted"
                and evidence.evidence_requirement_id in required_requirements
            ).mapped("evidence_requirement_id")
            instance.required_evidence_count = len(required_requirements)
            instance.accepted_evidence_count = len(set(accepted_requirements.ids))
            instance.missing_evidence_count = max(
                instance.required_evidence_count - instance.accepted_evidence_count,
                0,
            )
