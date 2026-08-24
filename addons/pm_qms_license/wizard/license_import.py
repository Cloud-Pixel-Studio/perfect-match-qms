import base64

from odoo import fields, models


class PmQmsLicenseImportWizard(models.TransientModel):
    _name = "pm.qms.license.import.wizard"
    _description = "Import Perfect Match QMS Offline License"

    license_file = fields.Binary(required=True, string="License File")
    filename = fields.Char(required=True)

    def action_import(self):
        self.ensure_one()
        license_record = self.env["pm.qms.license"].import_document(base64.b64decode(self.license_file))
        return {
            "type": "ir.actions.act_window",
            "name": "Commercial License",
            "res_model": "pm.qms.license",
            "view_mode": "form",
            "res_id": license_record.id,
            "target": "current",
        }
