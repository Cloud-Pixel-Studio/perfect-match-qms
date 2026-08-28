from odoo import api, fields, models


class PmQmsReadinessCenter(models.TransientModel):
    _name = "pm.qms.readiness.center"
    _description = "Perfect Match QMS Readiness Center"

    implementation_project_id = fields.Many2one(
        "pm.qms.implementation.project",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="implementation_project_id.company_id", readonly=True)
    organization_id = fields.Many2one(related="implementation_project_id.organization_id", readonly=True)
    dashboard_timestamp = fields.Datetime(default=fields.Datetime.now, readonly=True)
    assessment_goal_type = fields.Selection(related="implementation_project_id.assessment_goal_type", readonly=True)
    target_assessment_date = fields.Date(related="implementation_project_id.target_assessment_date", readonly=True)
    readiness_percent = fields.Float(related="implementation_project_id.readiness_percent", readonly=True)
    evidence_completion_percent = fields.Float(
        related="implementation_project_id.evidence_completion_percent",
        readonly=True,
    )
    activity_completion_percent = fields.Float(
        related="implementation_project_id.activity_completion_percent",
        readonly=True,
    )
    total_controls = fields.Integer(related="implementation_project_id.total_controls", readonly=True)
    ready_controls = fields.Integer(related="implementation_project_id.ready_controls", readonly=True)
    partial_controls = fields.Integer(related="implementation_project_id.partial_controls", readonly=True)
    gap_controls = fields.Integer(related="implementation_project_id.gap_controls", readonly=True)
    missing_evidence = fields.Integer(related="implementation_project_id.missing_evidence", readonly=True)
    open_tasks = fields.Integer(related="implementation_project_id.open_tasks", readonly=True)
    overdue_tasks = fields.Integer(related="implementation_project_id.overdue_tasks", readonly=True)
    area_line_ids = fields.One2many(
        "pm.qms.readiness.center.area",
        "center_id",
        string="Area Progress",
        readonly=True,
    )
    action_line_ids = fields.One2many(
        "pm.qms.readiness.center.action",
        "center_id",
        string="Recommended Next Actions",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if not values.get("implementation_project_id"):
            if self.env.context.get("active_model") == "pm.qms.implementation.project" and self.env.context.get("active_id"):
                values["implementation_project_id"] = self.env.context["active_id"]
            elif self.env.context.get("default_implementation_project_id"):
                values["implementation_project_id"] = self.env.context["default_implementation_project_id"]
        return values

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._rebuild_lines()
        return records

    def _rebuild_lines(self):
        AreaLine = self.env["pm.qms.readiness.center.area"]
        ActionLine = self.env["pm.qms.readiness.center.action"]
        for center in self:
            center.area_line_ids.unlink()
            center.action_line_ids.unlink()
            for values in center.implementation_project_id._area_progress_values():
                values["center_id"] = center.id
                AreaLine.create(values)
            for values in center.implementation_project_id._recommended_next_action_values():
                values["center_id"] = center.id
                ActionLine.create(values)

    def action_refresh(self):
        self.ensure_one()
        self.dashboard_timestamp = fields.Datetime.now()
        self._rebuild_lines()
        return {"type": "ir.actions.act_window", "res_model": self._name, "res_id": self.id, "view_mode": "form"}

    def action_create_readiness_assessment(self):
        self.ensure_one()
        return self.implementation_project_id.action_run_readiness_assessment()


class PmQmsReadinessCenterArea(models.TransientModel):
    _name = "pm.qms.readiness.center.area"
    _description = "Perfect Match QMS Readiness Center Area"
    _order = "sequence, name, id"

    center_id = fields.Many2one("pm.qms.readiness.center", required=True, ondelete="cascade")
    implementation_project_id = fields.Many2one(related="center_id.implementation_project_id", readonly=True)
    company_id = fields.Many2one(related="center_id.company_id", readonly=True)
    area_id = fields.Many2one("pm.qms.framework.area", readonly=True)
    sequence = fields.Integer(readonly=True)
    name = fields.Char(readonly=True)
    control_count = fields.Integer(readonly=True)
    ready_controls = fields.Integer(readonly=True)
    partial_controls = fields.Integer(readonly=True)
    gap_controls = fields.Integer(readonly=True)
    not_applicable_controls = fields.Integer(readonly=True)
    missing_evidence = fields.Integer(readonly=True)
    open_tasks = fields.Integer(readonly=True)
    overdue_tasks = fields.Integer(readonly=True)
    readiness_percent = fields.Float(readonly=True)

    def action_open_controls(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("pm_qms_implementation.action_pm_qms_implementation_control")
        action["domain"] = [
            ("implementation_project_id", "=", self.implementation_project_id.id),
            ("area_ids", "in", [self.area_id.id]),
        ]
        action["name"] = self.name
        return action


class PmQmsReadinessCenterAction(models.TransientModel):
    _name = "pm.qms.readiness.center.action"
    _description = "Perfect Match QMS Readiness Center Recommended Action"
    _order = "sequence, id"

    center_id = fields.Many2one("pm.qms.readiness.center", required=True, ondelete="cascade")
    implementation_project_id = fields.Many2one(related="center_id.implementation_project_id", readonly=True)
    company_id = fields.Many2one(related="center_id.company_id", readonly=True)
    sequence = fields.Integer(readonly=True)
    priority = fields.Selection(
        [("high", "High"), ("normal", "Normal"), ("low", "Low")],
        readonly=True,
    )
    action_type = fields.Selection(
        [
            ("start_control", "Start Control"),
            ("evidence", "Evidence"),
            ("review_evidence", "Review Evidence"),
            ("evidence_correction", "Correct Evidence"),
            ("evidence_renewal", "Renew Evidence"),
            ("activity", "Activity"),
            ("implementation", "Implementation"),
        ],
        readonly=True,
    )
    name = fields.Char(readonly=True)
    reason = fields.Char(readonly=True)
    blocker_summary = fields.Text(readonly=True)
    done_when = fields.Text(string="Done When", readonly=True)
    area_id = fields.Many2one("pm.qms.framework.area", readonly=True)
    implementation_control_id = fields.Many2one("pm.qms.implementation.control", readonly=True)
    task_id = fields.Many2one("project.task", readonly=True)
    evidence_requirement_id = fields.Many2one("pm.qms.evidence.requirement", readonly=True)
    evidence_id = fields.Many2one("pm.qms.evidence", readonly=True)
    res_model = fields.Char(readonly=True)
    res_id = fields.Integer(readonly=True)

    def action_open_record(self):
        self.ensure_one()
        if self.res_model == "pm.qms.evidence" and self.evidence_id:
            action = self.env["ir.actions.actions"]._for_xml_id(
                "pm_qms_evidence.action_pm_qms_evidence"
            )
            action.update({"view_mode": "form", "res_id": self.evidence_id.id})
            return action
        if self.res_model == "pm.qms.evidence":
            action = self.env["ir.actions.actions"]._for_xml_id(
                "pm_qms_evidence.action_pm_qms_evidence"
            )
            action["domain"] = [
                ("control_instance_id", "=", self.implementation_control_id.control_instance_id.id),
                ("evidence_requirement_id", "=", self.evidence_requirement_id.id),
            ]
            action["context"] = {
                "default_control_instance_id": self.implementation_control_id.control_instance_id.id,
                "default_evidence_requirement_id": self.evidence_requirement_id.id,
                "default_organization_id": self.implementation_control_id.organization_id.id,
            }
            action["name"] = "Evidence"
            return action
        if self.res_model == "project.task" and self.task_id:
            return self.task_id.action_open_pm_qms_activity()
        if self.implementation_control_id:
            return {
                "type": "ir.actions.act_window",
                "name": "Implementation Control",
                "res_model": "pm.qms.implementation.control",
                "view_mode": "form",
                "res_id": self.implementation_control_id.id,
            }
        return {"type": "ir.actions.act_window_close"}
