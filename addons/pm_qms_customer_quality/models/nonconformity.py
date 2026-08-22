from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsNonconformity(models.Model):
    _inherit = "pm.qms.nonconformity"

    customer_complaint_id = fields.Many2one("pm.qms.customer.complaint", string="Customer Complaint", ondelete="restrict")
    supplier_issue_id = fields.Many2one("pm.qms.supplier.issue", string="Supplier Issue", ondelete="restrict")
    eight_d_id = fields.Many2one("pm.qms.eight.d", string="8D Case", ondelete="restrict")
    scar_id = fields.Many2one("pm.qms.scar", string="SCAR", ondelete="restrict")

    @api.constrains("customer_complaint_id", "supplier_issue_id", "eight_d_id", "scar_id")
    def _check_customer_quality_alignment(self):
        for ncr in self:
            for sources in (ncr.customer_complaint_id, ncr.supplier_issue_id, ncr.eight_d_id, ncr.scar_id):
                for source in sources:
                    if source.company_id != ncr.company_id or source.organization_id != ncr.organization_id:
                        raise ValidationError("Customer/supplier quality source must match the NCR company and organization.")

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

    def action_create_eight_d(self):
        self.ensure_one()
        if self.eight_d_id:
            return self.eight_d_id.get_formview_action()
        case = self.env["pm.qms.eight.d"].create(
            {
                "name": f"8D for {self.code}: {self.name}",
                "organization_id": self.organization_id.id,
                "process_id": self.process_id.id,
                "source_type": "ncr",
                "ncr_id": self.id,
                "complaint_id": self.customer_complaint_id.id,
                "supplier_issue_id": self.supplier_issue_id.id,
                "scar_id": self.scar_id.id,
                "problem_statement": self.description,
                "owner_id": self.owner_id.id,
                "due_date": self.target_date,
            }
        )
        self.write({"eight_d_id": case.id})
        return case.get_formview_action()
