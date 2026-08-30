from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


FISHBONE_CATEGORIES = {
    "people": "People",
    "machine_equipment": "Machine / Equipment",
    "method_process": "Method / Process",
    "material_inputs": "Material / Inputs",
    "measurement_data": "Measurement / Data",
    "environment": "Environment",
}
FISHBONE_GUIDANCE = {
    "people": "What people, competency, staffing, communication, supervision, or training factors could have contributed?",
    "machine_equipment": "What equipment, tooling, software, setup, maintenance, or infrastructure factors could have contributed?",
    "method_process": "What procedure, work instruction, workflow, sequence, or process-control factors could have contributed?",
    "material_inputs": "What material, component, supplier, information, or other input factors could have contributed?",
    "measurement_data": "What inspection, calibration, measurement, monitoring, sampling, or data factors could have contributed?",
    "environment": "What workplace, physical, environmental, or external conditions could have contributed?",
}
EDITABLE_STATES = ("analysis", "action_planned")


class PmQmsCapaFishbone(models.Model):
    _name = "pm.qms.capa.fishbone"
    _description = "Perfect Match QMS CAPA Fishbone Cause"
    _order = "capa_id, category, id"

    capa_id = fields.Many2one("pm.qms.capa", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="capa_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="capa_id.organization_id", store=True, readonly=True, index=True)
    category = fields.Selection([(key, label) for key, label in FISHBONE_CATEGORIES.items()], required=True)
    guidance = fields.Text(compute="_compute_guidance", readonly=True)
    potential_cause = fields.Text(required=True)
    evidence_basis = fields.Text()
    investigation_status = fields.Selection(
        [
            ("potential", "Potential"),
            ("investigating", "Investigating"),
            ("confirmed", "Confirmed"),
            ("rejected", "Rejected"),
        ],
        default="potential",
        required=True,
    )
    rationale_finding = fields.Text()

    @api.depends("category")
    def _compute_guidance(self):
        for cause in self:
            cause.guidance = FISHBONE_GUIDANCE.get(cause.category, "")

    def _check_editable(self):
        if any(cause.capa_id.state not in EDITABLE_STATES for cause in self):
            raise UserError("Fishbone causes can only be changed during CAPA analysis or action planning.")

    @api.constrains("investigation_status", "potential_cause", "evidence_basis", "rationale_finding")
    def _check_status_evidence(self):
        for cause in self:
            if cause.investigation_status == "confirmed" and not cause.evidence_basis:
                raise ValidationError("A confirmed Fishbone cause requires evidence basis.")
            if cause.investigation_status in ("confirmed", "rejected") and not cause.rationale_finding:
                raise ValidationError("A confirmed or rejected Fishbone cause requires rationale.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_editable()
        records._check_status_evidence()
        return records

    def write(self, vals):
        self._check_editable()
        result = super().write(vals)
        self._check_status_evidence()
        return result

    def unlink(self):
        self._check_editable()
        return super().unlink()
