from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsCapa(models.Model):
    _inherit = "pm.qms.capa"

    customer_complaint_id = fields.Many2one("pm.qms.customer.complaint", string="Customer Complaint", ondelete="restrict")
    supplier_issue_id = fields.Many2one("pm.qms.supplier.issue", string="Supplier Issue", ondelete="restrict")
    eight_d_id = fields.Many2one("pm.qms.eight.d", string="8D Case", ondelete="restrict")
    scar_id = fields.Many2one("pm.qms.scar", string="SCAR", ondelete="restrict")

    @api.constrains("customer_complaint_id", "supplier_issue_id", "eight_d_id", "scar_id")
    def _check_customer_quality_alignment(self):
        for capa in self:
            for sources in (capa.customer_complaint_id, capa.supplier_issue_id, capa.eight_d_id, capa.scar_id):
                for source in sources:
                    if source.company_id != capa.company_id or source.organization_id != capa.organization_id:
                        raise ValidationError("Customer/supplier quality source must match the CAPA company and organization.")

    def action_view_customer_complaint(self):
        self.ensure_one()
        return self.customer_complaint_id.get_formview_action()

    def action_view_supplier_issue(self):
        self.ensure_one()
        return self.supplier_issue_id.get_formview_action()

    def action_view_eight_d(self):
        self.ensure_one()
        return self.eight_d_id.get_formview_action()

    def action_view_scar(self):
        self.ensure_one()
        return self.scar_id.get_formview_action()
