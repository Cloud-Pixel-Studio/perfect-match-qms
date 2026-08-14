from odoo import fields, models


class PmQmsRisk(models.Model):
    _inherit = "pm.qms.risk"

    capa_ids = fields.One2many("pm.qms.capa", "source_risk_id", string="CAPAs")
    capa_count = fields.Integer(compute="_compute_capa_count")

    def _compute_capa_count(self):
        for risk in self:
            risk.capa_count = len(risk.capa_ids)

    def action_create_capa(self):
        self.ensure_one()
        capa = self.env["pm.qms.capa"].create(
            {
                "name": f"CAPA for {self.code}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "owner_id": self.owner_id.id,
                "source_type": "risk",
                "source_risk_id": self.id,
                "problem_statement": self.description,
                "action_plan": self.mitigation_plan,
                "related_control_instance_ids": [(6, 0, self.related_control_instance_ids.ids)],
                "related_document_ids": [(6, 0, self.related_document_ids.ids)],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "CAPA",
            "res_model": "pm.qms.capa",
            "res_id": capa.id,
            "view_mode": "form",
        }
