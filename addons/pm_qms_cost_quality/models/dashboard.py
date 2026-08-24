from odoo import fields, models
from odoo.exceptions import AccessError


class PmQmsDashboard(models.TransientModel):
    _inherit = "pm.qms.dashboard"

    currency_id = fields.Many2one("res.currency", compute="_compute_dashboard")
    quality_cost_event_count = fields.Integer(compute="_compute_dashboard")
    dashboard_quality_cost_total = fields.Monetary(
        string="Quality Cost", compute="_compute_dashboard", currency_field="currency_id"
    )
    dashboard_copq_amount = fields.Monetary(
        string="COPQ", compute="_compute_dashboard", currency_field="currency_id"
    )
    dashboard_recovery_total = fields.Monetary(
        string="Recoveries", compute="_compute_dashboard", currency_field="currency_id"
    )

    def _metric_fields(self):
        return super()._metric_fields() + ["quality_cost_event_count"]

    def _can_view_cost_quality(self):
        return any(
            self.env.user.has_group(group)
            for group in (
                "pm_qms_core.group_qms_quality_manager",
                "pm_qms_core.group_qms_management_user",
                "pm_qms_core.group_pm_qms_administrator",
                "base.group_system",
            )
        )

    def _compute_dashboard(self):
        super()._compute_dashboard()
        CostEvent = self.env["pm.qms.cost.event"]
        for dashboard in self:
            dashboard.currency_id = dashboard.organization_id.company_id.currency_id if dashboard.organization_id else self.env.company.currency_id
            dashboard.dashboard_quality_cost_total = 0.0
            dashboard.dashboard_copq_amount = 0.0
            dashboard.dashboard_recovery_total = 0.0
            if not dashboard.organization_id:
                continue
            if not dashboard._can_view_cost_quality():
                continue
            events = CostEvent.search(dashboard._base_domain() + [("state", "=", "confirmed")])
            dashboard.quality_cost_event_count = len(events)
            dashboard.dashboard_quality_cost_total = sum(events.mapped("quality_cost_total"))
            dashboard.dashboard_copq_amount = sum(events.mapped("copq_amount"))
            dashboard.dashboard_recovery_total = sum(events.mapped("recovery_total"))

    def action_view_cost_quality(self):
        self.ensure_one()
        if not self._can_view_cost_quality():
            raise AccessError("Cost of Quality is restricted to authorized QMS management users.")
        return self._action_for_xmlid(
            "pm_qms_cost_quality.action_pm_qms_cost_event_official",
            domain=self._base_domain() + [("state", "=", "confirmed")],
            context={"search_default_official": 1},
            name="Cost of Quality",
        )
