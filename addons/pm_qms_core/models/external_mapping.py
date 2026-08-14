from odoo import fields, models


class PmQmsExternalMapping(models.Model):
    _name = "pm.qms.external.mapping"
    _description = "Perfect Match QMS External Reference Mapping"
    _order = "standard_name, edition, reference"

    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    standard_name = fields.Char(required=True)
    edition = fields.Char()
    reference = fields.Char(
        required=True,
        help="Reference identifier only. Do not copy copyrighted standard text.",
    )
    note = fields.Text(
        help="Perfect Match internal notes only. Do not copy copyrighted standard text.",
    )
    active = fields.Boolean(default=True)

    _control_standard_ref_uniq = models.Constraint(
        "UNIQUE(control_id, standard_name, edition, reference)",
        "External mapping references must be unique per control.",
    )
