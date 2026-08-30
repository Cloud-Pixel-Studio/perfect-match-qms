from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


WHY_PROMPTS = {
    1: "Why did the problem occur?",
    2: "Why did the condition identified in Why 1 occur?",
    3: "Why did the condition identified in Why 2 occur?",
    4: "Why did the condition identified in Why 3 occur?",
    5: "Why did the condition identified in Why 4 occur?",
}


class PmQmsCapaWhy(models.Model):
    _name = "pm.qms.capa.why"
    _description = "Perfect Match QMS CAPA 5 Why Entry"
    _order = "capa_id, sequence, id"

    capa_id = fields.Many2one("pm.qms.capa", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="capa_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="capa_id.organization_id", store=True, readonly=True, index=True)
    sequence = fields.Integer(default=1, required=True)
    question = fields.Char(required=True)
    answer = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("pm_qms_capa_initialize"):
            raise UserError("5 Why entries are fixed analysis slots and cannot be added manually.")
        for vals in vals_list:
            sequence = vals.get("sequence")
            if sequence not in WHY_PROMPTS:
                raise ValidationError("5 Why sequence must be between 1 and 5.")
            vals["question"] = WHY_PROMPTS[sequence]
        records = super().create(vals_list)
        records._check_integrity()
        return records

    def _check_integrity(self):
        for why in self:
            if why.sequence not in WHY_PROMPTS:
                raise ValidationError("5 Why sequence must be between 1 and 5.")
            siblings = self.search([("capa_id", "=", why.capa_id.id)])
            sequences = siblings.mapped("sequence")
            if len(siblings) > 5 or len(sequences) != len(set(sequences)):
                raise ValidationError("A CAPA may contain at most five unique 5 Why slots.")

    @api.constrains("capa_id", "sequence")
    def _check_sequence(self):
        self._check_integrity()

    def write(self, vals):
        if set(vals) - {"answer"}:
            raise UserError("5 Why sequence and prompts are fixed and cannot be changed.")
        if any(why.capa_id.state not in ("draft", "analysis", "action_planned") for why in self):
            raise UserError("5 Why answers cannot be changed after CAPA implementation starts.")
        return super().write(vals)

    def unlink(self):
        raise UserError("5 Why analysis uses fixed slots; entries cannot be deleted.")
