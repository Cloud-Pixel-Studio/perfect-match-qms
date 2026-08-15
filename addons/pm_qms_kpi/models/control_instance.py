from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    objective_ids = fields.Many2many(
        "pm.qms.objective",
        compute="_compute_performance_links",
        string="Objectives",
    )
    kpi_ids = fields.Many2many(
        "pm.qms.kpi",
        compute="_compute_performance_links",
        string="KPIs",
    )
    objective_count = fields.Integer(compute="_compute_performance_links")
    active_objective_count = fields.Integer(compute="_compute_performance_links")
    kpi_count = fields.Integer(compute="_compute_performance_links")
    active_kpi_count = fields.Integer(compute="_compute_performance_links")
    off_target_kpi_count = fields.Integer(compute="_compute_performance_links")
    overdue_kpi_count = fields.Integer(compute="_compute_performance_links")

    def _compute_performance_links(self):
        Objective = self.env["pm.qms.objective"]
        Kpi = self.env["pm.qms.kpi"]
        for instance in self:
            objectives = Objective.search([("related_control_instance_ids", "in", instance.id)])
            kpis = Kpi.search([("control_instance_ids", "in", instance.id)])
            instance.objective_ids = objectives
            instance.kpi_ids = kpis
            instance.objective_count = len(objectives)
            instance.active_objective_count = len(objectives.filtered(lambda objective: objective.status == "active"))
            instance.kpi_count = len(kpis)
            instance.active_kpi_count = len(kpis.filtered(lambda kpi: kpi.status == "active"))
            instance.off_target_kpi_count = len(kpis.filtered(lambda kpi: kpi.latest_status == "off_target"))
            instance.overdue_kpi_count = len(kpis.filtered(lambda kpi: kpi.measurement_overdue))
