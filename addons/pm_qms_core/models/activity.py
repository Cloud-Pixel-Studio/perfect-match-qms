from odoo import fields, models


class PmQmsActivity(models.Model):
    _name = "pm.qms.activity"
    _description = "Perfect Match QMS Implementation Activity"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    description = fields.Text()
    responsible_role = fields.Char()
    responsible_user_id = fields.Many2one("res.users", string="Responsible User")
    expected_output = fields.Text()
    active = fields.Boolean(default=True)
