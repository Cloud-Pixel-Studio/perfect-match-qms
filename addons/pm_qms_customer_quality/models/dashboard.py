from odoo import fields, models


class PmQmsDashboard(models.TransientModel):
    _inherit = "pm.qms.dashboard"

    open_customer_complaints = fields.Integer(compute="_compute_dashboard")
    overdue_customer_responses = fields.Integer(compute="_compute_dashboard")
    open_quality_alerts = fields.Integer(compute="_compute_dashboard")
    open_eight_d_cases = fields.Integer(compute="_compute_dashboard")
    overdue_eight_d_cases = fields.Integer(compute="_compute_dashboard")
    open_supplier_issues = fields.Integer(compute="_compute_dashboard")
    open_scar = fields.Integer(compute="_compute_dashboard")
    overdue_scar = fields.Integer(compute="_compute_dashboard")

    def _metric_fields(self):
        return super()._metric_fields() + [
            "open_customer_complaints",
            "overdue_customer_responses",
            "open_quality_alerts",
            "open_eight_d_cases",
            "overdue_eight_d_cases",
            "open_supplier_issues",
            "open_scar",
            "overdue_scar",
        ]

    def _compute_dashboard(self):
        result = super()._compute_dashboard()
        Complaint = self.env["pm.qms.customer.complaint"]
        Alert = self.env["pm.qms.quality.alert"]
        EightD = self.env["pm.qms.eight.d"]
        SupplierIssue = self.env["pm.qms.supplier.issue"]
        Scar = self.env["pm.qms.scar"]
        for dashboard in self:
            if not dashboard.organization_id:
                continue
            base_domain = dashboard._base_domain()
            open_complaint_domain = base_domain + [("state", "not in", ("closed", "cancelled"))]
            dashboard.open_customer_complaints = Complaint.search_count(open_complaint_domain)
            dashboard.overdue_customer_responses = Complaint.search_count(open_complaint_domain + [("is_response_overdue", "=", True)])
            dashboard.open_quality_alerts = Alert.search_count(base_domain + [("state", "=", "published")])
            open_8d_domain = base_domain + [("state", "not in", ("closed", "cancelled"))]
            dashboard.open_eight_d_cases = EightD.search_count(open_8d_domain)
            dashboard.overdue_eight_d_cases = EightD.search_count(open_8d_domain + [("is_overdue", "=", True)])
            open_supplier_domain = base_domain + [("state", "not in", ("closed", "cancelled"))]
            dashboard.open_supplier_issues = SupplierIssue.search_count(open_supplier_domain)
            open_scar_domain = base_domain + [("state", "not in", ("closed", "cancelled"))]
            dashboard.open_scar = Scar.search_count(open_scar_domain)
            dashboard.overdue_scar = Scar.search_count(open_scar_domain + [("is_overdue", "=", True)])

            attention = []
            if dashboard.overdue_customer_responses:
                attention.append(("Respond to overdue customer complaints", f"{dashboard.overdue_customer_responses} customer response deadline(s) overdue."))
            if dashboard.overdue_scar:
                attention.append(("Review overdue SCAR responses", f"{dashboard.overdue_scar} supplier response deadline(s) overdue."))
            if dashboard.open_eight_d_cases:
                attention.append(("Advance open 8D cases", f"{dashboard.open_eight_d_cases} structured problem-solving case(s) open."))
            for index, (name, reason) in enumerate(attention[:3], start=1):
                if not dashboard[f"next_action_{index}_name"]:
                    dashboard[f"next_action_{index}_name"] = name
                    dashboard[f"next_action_{index}_reason"] = reason
        return result
