from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


IS_IS_NOT_DIMENSIONS = {
    "what": "What",
    "where": "Where",
    "when": "When",
    "extent": "Extent",
}
IS_IS_NOT_PROMPTS = {
    "what": {
        "is": "What object, process, or characteristic is affected?",
        "is_not": "What comparable object, process, or characteristic could be affected but is not?",
        "distinction": "What is different between the affected and unaffected cases?",
        "change": "What changed that could explain the distinction?",
    },
    "where": {
        "is": "Where is the problem observed?",
        "is_not": "Where could the problem occur but does not?",
        "distinction": "What differs between those locations?",
        "change": "What changed between those conditions or locations?",
    },
    "when": {
        "is": "When is or was the problem observed?",
        "is_not": "When could the problem occur but does not?",
        "distinction": "What differs between those times or operating conditions?",
        "change": "What changed around the time the problem began?",
    },
    "extent": {
        "is": "How many, how much, or how frequently is affected?",
        "is_not": "What comparable population, quantity, or frequency is unaffected?",
        "distinction": "What pattern separates the affected and unaffected cases?",
        "change": "Has the magnitude, frequency, or pattern changed?",
    },
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
    is_prompt = fields.Text(compute="_compute_prompts", readonly=True)
    is_not_prompt = fields.Text(compute="_compute_prompts", readonly=True)
    distinction_prompt = fields.Text(compute="_compute_prompts", readonly=True)
    change_prompt = fields.Text(compute="_compute_prompts", readonly=True)

    @api.depends("dimension")
    def _compute_prompts(self):
        for row in self:
            prompts = IS_IS_NOT_PROMPTS.get(row.dimension, {})
            row.is_prompt = prompts.get("is", "")
            row.is_not_prompt = prompts.get("is_not", "")
            row.distinction_prompt = prompts.get("distinction", "")
            row.change_prompt = prompts.get("change", "")

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
