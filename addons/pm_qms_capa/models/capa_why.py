from odoo import fields, models
from odoo.exceptions import UserError


class PmQmsCapaWhy(models.Model):
    _name = "pm.qms.capa.why"
    _description = "Perfect Match QMS CAPA 5 Why Entry"
    _order = "capa_id, sequence, id"

    capa_id = fields.Many2one("pm.qms.capa", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="capa_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="capa_id.organization_id", store=True, readonly=True, index=True)
    sequence = fields.Integer(default=1)
    question = fields.Char(required=True)
    answer = fields.Text()

    def unlink(self):
        if any(why.capa_id.state != "draft" for why in self):
            raise UserError("CAPA root-cause entries cannot be deleted after CAPA workflow starts.")
        return super().unlink()
