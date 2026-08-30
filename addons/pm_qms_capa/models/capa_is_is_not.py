from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


IS_IS_NOT_DIMENSIONS = {
    "what": "What",
    "where": "Where",
    "when": "When",
    "extent": "Extent",
}
IS_IS_NOT_GUIDANCE = {
    "what": "Describe what is occurring and what is not occurring.",
    "where": "Describe where the condition is and where it is not.",
    "when": "Describe when the condition occurs and when it does not.",
    "extent": "Describe the extent, scale, or boundary of the condition.",
}
IS_IS_NOT_SEQUENCE = {dimension: index for index, dimension in enumerate(IS_IS_NOT_DIMENSIONS, start=1)}


class PmQmsCapaIsIsNot(models.Model):
    _name = "pm.qms.capa.is.is.not"
    _description = "Perfect Match QMS CAPA Is Is Not Analysis"
    _order = "capa_id, sequence, id"

    capa_id = fields.Many2one("pm.qms.capa", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="capa_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="capa_id.organization_id", store=True, readonly=True, index=True)
    dimension = fields.Selection([(key, label) for key, label in IS_IS_NOT_DIMENSIONS.items()], required=True)
    sequence = fields.Integer(required=True)
    is_value = fields.Text(string="IS")
    is_not_value = fields.Text(string="IS NOT")
    distinction = fields.Text()
    change_value = fields.Text(string="Change")
    guidance = fields.Text(compute="_compute_guidance")

    @api.depends("dimension")
    def _compute_guidance(self):
        for row in self:
            row.guidance = IS_IS_NOT_GUIDANCE.get(row.dimension, "")

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("pm_qms_capa_initialize"):
            raise UserError("Is / Is Not analysis uses four fixed dimensions and cannot be added manually.")
        records = super().create(vals_list)
        records._check_integrity()
        return records

    def _check_integrity(self):
        for row in self:
            if row.dimension not in IS_IS_NOT_DIMENSIONS or row.sequence != IS_IS_NOT_SEQUENCE[row.dimension]:
                raise ValidationError("Is / Is Not rows must use the four fixed dimensions.")
            siblings = self.search([("capa_id", "=", row.capa_id.id)])
            dimensions = siblings.mapped("dimension")
            sequences = siblings.mapped("sequence")
            if (
                len(siblings) > 4
                or len(dimensions) != len(set(dimensions))
                or set(sequences) != set(IS_IS_NOT_SEQUENCE.values())
            ):
                raise ValidationError("A CAPA may contain exactly one Is / Is Not row per dimension.")

    @api.constrains("capa_id", "dimension", "sequence")
    def _check_fixed_structure(self):
        self._check_integrity()

    def write(self, vals):
        if set(vals) - {"is_value", "is_not_value", "distinction", "change_value"}:
            raise UserError("Is / Is Not dimensions are fixed and cannot be changed.")
        if any(row.capa_id.state not in ("draft", "analysis", "action_planned") for row in self):
            raise UserError("Is / Is Not analysis cannot be changed after CAPA implementation starts.")
        return super().write(vals)

    def unlink(self):
        raise UserError("Is / Is Not analysis uses fixed dimensions; rows cannot be deleted.")
