from odoo import fields, models


class PmQmsDashboard(models.TransientModel):
    _inherit = "pm.qms.dashboard"

    unified_action_count = fields.Integer(compute="_compute_dashboard")
    my_action_count = fields.Integer(compute="_compute_dashboard")
    overdue_action_count = fields.Integer(compute="_compute_dashboard")
    due_soon_action_count = fields.Integer(compute="_compute_dashboard")

    def _metric_fields(self):
        return super()._metric_fields() + [
            "unified_action_count",
            "my_action_count",
            "overdue_action_count",
            "due_soon_action_count",
        ]

    def _compute_dashboard(self):
        super()._compute_dashboard()
        ActionLine = self.env["pm.qms.action.center.line"]
        for dashboard in self:
            if not dashboard.organization_id:
                continue
            values = ActionLine._collect_action_values(dashboard.organization_id)
            dashboard.unified_action_count = len(values)
            dashboard.my_action_count = len(
                [item for item in values if item.get("owner_user_id") == self.env.user.id]
            )
            dashboard.overdue_action_count = len(
                [item for item in values if item.get("due_bucket") == "overdue"]
            )
            dashboard.due_soon_action_count = len(
                [item for item in values if item.get("due_bucket") == "soon"]
            )

    def action_view_unified_actions(self):
        self.ensure_one()
        return self.env["pm.qms.action.center.line"].action_open_center()
