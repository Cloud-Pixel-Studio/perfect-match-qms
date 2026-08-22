from odoo import models


class PmQmsManagementReview(models.Model):
    _inherit = "pm.qms.management.review"

    def _generate_snapshot_inputs(self, snapshot_date):
        result = super()._generate_snapshot_inputs(snapshot_date)
        for review in self:
            review._snapshot_customer_supplier_quality(snapshot_date)
        return result

    def _snapshot_customer_supplier_quality(self, snapshot_date):
        self.ensure_one()
        Complaint = self.env["pm.qms.customer.complaint"]
        EightD = self.env["pm.qms.eight.d"]
        SupplierIssue = self.env["pm.qms.supplier.issue"]
        Scar = self.env["pm.qms.scar"]
        base_domain = self._base_domain()
        complaints = Complaint.search(base_domain + self._period_overlap_domain_complaint())
        open_complaints = complaints.filtered(lambda item: item.state not in ("closed", "cancelled"))
        overdue_complaints = open_complaints.filtered("is_response_overdue")
        eight_d = EightD.search(base_domain + [("state", "not in", ("closed", "cancelled"))])
        if complaints or eight_d:
            self._create_input(
                "customer_performance",
                "Customer quality and 8D status",
                "other",
                snapshot_date=snapshot_date,
                status_snapshot="issues" if overdue_complaints or eight_d else "monitor",
                numeric_value=len(overdue_complaints) + len(eight_d),
                unit_of_measure="records needing attention",
                text_value=f"Complaints: {len(complaints)}; open: {len(open_complaints)}; overdue responses: {len(overdue_complaints)}; open 8D: {len(eight_d)}",
                source_identifier="PM-QMS-CUSTOMER-QUALITY",
            )
        supplier_issues = SupplierIssue.search(base_domain + [("state", "not in", ("closed", "cancelled"))])
        scar = Scar.search(base_domain + [("state", "not in", ("closed", "cancelled"))])
        overdue_scar = scar.filtered("is_overdue")
        if supplier_issues or scar:
            self._create_input(
                "supplier_performance",
                "Supplier quality and SCAR status",
                "other",
                snapshot_date=snapshot_date,
                status_snapshot="issues" if overdue_scar else "monitor",
                numeric_value=len(supplier_issues) + len(overdue_scar),
                unit_of_measure="records needing attention",
                text_value=f"Supplier issues: {len(supplier_issues)}; open SCAR: {len(scar)}; overdue SCAR: {len(overdue_scar)}",
                source_identifier="PM-QMS-SUPPLIER-QUALITY",
            )

    def _period_overlap_domain_complaint(self):
        self.ensure_one()
        return [("received_date", ">=", self.period_start), ("received_date", "<=", self.period_end)]
