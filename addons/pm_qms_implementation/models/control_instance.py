from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    implementation_control_ids = fields.One2many(
        "pm.qms.implementation.control",
        "control_instance_id",
        string="Implementation Projects",
    )

    _control_organization_uniq = models.Constraint(
        "UNIQUE(control_id, organization_id)",
        "An organization can have only one active operational instance per reusable control.",
    )
