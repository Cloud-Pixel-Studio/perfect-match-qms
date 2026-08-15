from odoo import fields, models


class PmQmsProcess(models.Model):
    _inherit = "pm.qms.process"

    objective_ids = fields.One2many("pm.qms.objective", "process_id", string="Objectives")
    kpi_ids = fields.One2many("pm.qms.kpi", "process_id", string="KPIs")
    objective_count = fields.Integer(compute="_compute_performance_summary")
    active_objective_count = fields.Integer(compute="_compute_performance_summary")
    achieved_objective_count = fields.Integer(compute="_compute_performance_summary")
    not_achieved_objective_count = fields.Integer(compute="_compute_performance_summary")
    kpi_count = fields.Integer(compute="_compute_performance_summary")
    active_kpi_count = fields.Integer(compute="_compute_performance_summary")
    on_target_kpi_count = fields.Integer(compute="_compute_performance_summary")
    off_target_kpi_count = fields.Integer(compute="_compute_performance_summary")
    overdue_kpi_count = fields.Integer(compute="_compute_performance_summary")

    def _compute_performance_summary(self):
        for process in self:
            objectives = process.objective_ids
            kpis = process.kpi_ids
            process.objective_count = len(objectives)
            process.active_objective_count = len(objectives.filtered(lambda objective: objective.status == "active"))
            process.achieved_objective_count = len(objectives.filtered(lambda objective: objective.status == "achieved"))
            process.not_achieved_objective_count = len(
                objectives.filtered(lambda objective: objective.status == "not_achieved")
            )
            process.kpi_count = len(kpis)
            process.active_kpi_count = len(kpis.filtered(lambda kpi: kpi.status == "active"))
            process.on_target_kpi_count = len(kpis.filtered(lambda kpi: kpi.latest_status == "on_target"))
            process.off_target_kpi_count = len(kpis.filtered(lambda kpi: kpi.latest_status == "off_target"))
            process.overdue_kpi_count = len(kpis.filtered(lambda kpi: kpi.measurement_overdue))
