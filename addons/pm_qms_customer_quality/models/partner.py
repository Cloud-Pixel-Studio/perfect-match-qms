from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    qms_customer_complaint_ids = fields.One2many("pm.qms.customer.complaint", "customer_id", string="QMS Complaints")
    qms_supplier_issue_ids = fields.One2many("pm.qms.supplier.issue", "supplier_id", string="QMS Supplier Issues")
    qms_scar_ids = fields.One2many("pm.qms.scar", "supplier_id", string="QMS SCARs")
