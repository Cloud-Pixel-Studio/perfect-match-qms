from datetime import datetime, time

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsImplementationProject(models.Model):
    _name = "pm.qms.implementation.project"
    _description = "Perfect Match QMS Implementation Project"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True, tracking=True)
    project_manager_id = fields.Many2one("res.users", string="Project Manager", tracking=True)
    date_start = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    target_date = fields.Date(required=True, tracking=True)
    assessment_goal_type = fields.Selection(
        [
            ("internal_readiness", "Internal Readiness"),
            ("certification", "Certification"),
            ("surveillance", "Surveillance"),
            ("customer_audit", "Customer Audit"),
            ("regulatory_assessment", "Regulatory Assessment"),
            ("other", "Other"),
        ],
        default="internal_readiness",
        required=True,
        tracking=True,
    )
    target_assessment_date = fields.Date(tracking=True)
    actual_completion_date = fields.Date(tracking=True)
    completion_justification = fields.Text()
    implementation_type = fields.Selection(
        [
            ("new_implementation", "New Implementation"),
            ("migration", "Migration"),
            ("optimization", "Optimization"),
            ("gap_assessment", "Gap Assessment"),
            ("upgrade", "Upgrade"),
            ("custom", "Custom"),
        ],
        default="new_implementation",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("generated", "Generated"),
            ("in_progress", "In Progress"),
            ("readiness_review", "Readiness Review"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    pack_ids = fields.Many2many(
        "pm.qms.framework.pack",
        "pm_qms_implementation_project_pack_rel",
        "implementation_project_id",
        "pack_id",
        string="Framework Packs",
        tracking=True,
    )
    odoo_project_id = fields.Many2one("project.project", string="Odoo Project", ondelete="set null", copy=False)
    generation_date = fields.Datetime(copy=False)
    last_sync_date = fields.Datetime(copy=False)
    notes = fields.Text()
    active = fields.Boolean(default=True)

    implementation_control_ids = fields.One2many(
        "pm.qms.implementation.control",
        "implementation_project_id",
        string="Implementation Controls",
        copy=False,
    )
    generated_task_ids = fields.One2many(
        "project.task",
        "pm_implementation_project_id",
        string="Generated Tasks",
        copy=False,
    )
    assessment_ids = fields.One2many(
        "pm.qms.readiness.assessment",
        "implementation_project_id",
        string="Readiness Assessments",
        copy=False,
    )
    latest_assessment_id = fields.Many2one("pm.qms.readiness.assessment", compute="_compute_latest_assessment")

    total_controls = fields.Integer(compute="_compute_metrics")
    applicable_controls = fields.Integer(compute="_compute_metrics")
    not_applicable_controls = fields.Integer(compute="_compute_metrics")
    implemented_controls = fields.Integer(compute="_compute_metrics")
    in_progress_controls = fields.Integer(compute="_compute_metrics")
    not_started_controls = fields.Integer(compute="_compute_metrics")
    under_review_controls = fields.Integer(compute="_compute_metrics")
    ready_controls = fields.Integer(compute="_compute_metrics")
    partial_controls = fields.Integer(compute="_compute_metrics")
    gap_controls = fields.Integer(compute="_compute_metrics")
    required_evidence = fields.Integer(compute="_compute_metrics")
    accepted_evidence = fields.Integer(compute="_compute_metrics")
    missing_evidence = fields.Integer(compute="_compute_metrics")
    total_generated_tasks = fields.Integer(compute="_compute_metrics")
    completed_tasks = fields.Integer(compute="_compute_metrics")
    open_tasks = fields.Integer(compute="_compute_metrics")
    overdue_tasks = fields.Integer(compute="_compute_metrics")
    readiness_percent = fields.Float(compute="_compute_metrics")
    evidence_completion_percent = fields.Float(compute="_compute_metrics")
    activity_completion_percent = fields.Float(compute="_compute_metrics")

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Implementation project code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.implementation.project") or "PM-IMP-00000"
        return super().create(vals_list)

    @api.constrains("company_id", "organization_id", "pack_ids", "date_start", "target_date", "target_assessment_date", "actual_completion_date")
    def _check_project_constraints(self):
        for project in self:
            if project.organization_id.company_id != project.company_id:
                raise ValidationError("Implementation project organization must belong to the selected company.")
            if any(pack.company_id != project.company_id for pack in project.pack_ids):
                raise ValidationError("All framework packs must belong to the implementation project company.")
            if project.date_start and project.target_date and project.target_date < project.date_start:
                raise ValidationError("Target date cannot be before the implementation start date.")
            if project.target_assessment_date and project.date_start and project.target_assessment_date < project.date_start:
                raise ValidationError("Target assessment date cannot be before the implementation start date.")
            if project.actual_completion_date and project.date_start and project.actual_completion_date < project.date_start:
                raise ValidationError("Completion date cannot be before the implementation start date.")

    @api.depends("assessment_ids.assessment_date", "assessment_ids.state")
    def _compute_latest_assessment(self):
        for project in self:
            completed = project.assessment_ids.filtered(lambda assessment: assessment.state == "completed")
            project.latest_assessment_id = completed[:1] if completed else False

    @api.depends(
        "implementation_control_ids.active",
        "implementation_control_ids.readiness_state",
        "implementation_control_ids.gap_reason",
        "implementation_control_ids.implementation_status",
        "implementation_control_ids.required_evidence_count",
        "implementation_control_ids.accepted_evidence_count",
        "implementation_control_ids.missing_evidence_count",
        "implementation_control_ids.required_activity_count",
        "implementation_control_ids.completed_activity_count",
        "implementation_control_ids.open_activity_count",
        "generated_task_ids.state",
        "generated_task_ids.date_deadline",
    )
    def _compute_metrics(self):
        now = fields.Datetime.now()
        for project in self:
            controls = project.implementation_control_ids.filtered("active")
            not_applicable = controls.filtered(lambda line: line.readiness_state == "not_applicable")
            applicable = controls - not_applicable
            ready = applicable.filtered(lambda line: line.readiness_state == "ready")
            partial = applicable.filtered(lambda line: line.readiness_state == "partial")
            gap = applicable.filtered(lambda line: line.readiness_state == "gap")
            tasks = project.generated_task_ids.filtered(lambda task: task.pm_generated)
            completed_tasks = tasks.filtered("is_closed")
            open_tasks = tasks - completed_tasks
            required_activity_count = sum(controls.mapped("required_activity_count"))
            completed_activity_count = sum(controls.mapped("completed_activity_count"))

            project.total_controls = len(controls)
            project.applicable_controls = len(applicable)
            project.not_applicable_controls = len(not_applicable)
            project.ready_controls = len(ready)
            project.partial_controls = len(partial)
            project.gap_controls = len(gap)
            project.implemented_controls = len(controls.filtered(lambda line: line.implementation_status == "implemented"))
            project.in_progress_controls = len(
                controls.filtered(lambda line: line.implementation_status in {"in_progress", "evidence_required"})
            )
            project.not_started_controls = len(controls.filtered(lambda line: line.implementation_status == "not_started"))
            project.under_review_controls = len(controls.filtered(lambda line: line.implementation_status == "under_review"))
            project.required_evidence = sum(controls.mapped("required_evidence_count"))
            project.accepted_evidence = sum(controls.mapped("accepted_evidence_count"))
            project.missing_evidence = sum(controls.mapped("missing_evidence_count"))
            project.total_generated_tasks = len(tasks)
            project.completed_tasks = len(completed_tasks)
            project.open_tasks = len(open_tasks)
            project.overdue_tasks = len(open_tasks.filtered(lambda task: task.date_deadline and task.date_deadline < now))
            project.readiness_percent = (len(ready) / len(applicable) * 100.0) if applicable else 0.0
            project.evidence_completion_percent = (
                project.accepted_evidence / project.required_evidence * 100.0 if project.required_evidence else 100.0
            )
            project.activity_completion_percent = (
                completed_activity_count / required_activity_count * 100.0 if required_activity_count else 100.0
            )

    def _check_manager_permission(self):
        if self.env.context.get("install_mode") or self.env.context.get("module"):
            return
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can manage implementation projects.")

    def _validate_active_packs(self):
        for project in self:
            if not project.pack_ids:
                raise UserError("Select at least one framework pack.")
            inactive = project.pack_ids.filtered(lambda pack: pack.state != "active")
            if inactive:
                raise UserError("Only active framework pack versions can be deployed.")
            wrong_company = project.pack_ids.filtered(lambda pack: pack.company_id != project.company_id)
            if wrong_company:
                raise ValidationError("Framework packs must belong to the same company as the implementation project.")

    def _ensure_odoo_project(self):
        Stage = self.env["project.task.type"]
        for project in self:
            if project.odoo_project_id:
                continue
            odoo_project = self.env["project.project"].create(
                {
                    "name": f"{project.code} {project.name}",
                    "company_id": project.company_id.id,
                    "user_id": project.project_manager_id.id or self.env.user.id,
                    "date_start": project.date_start,
                    "date": project.target_date,
                    "privacy_visibility": "employees",
                    "pm_implementation_project_id": project.id,
                }
            )
            for sequence, name, fold in [
                (10, "Backlog", False),
                (20, "Ready", False),
                (30, "In Progress", False),
                (40, "Evidence / Review", False),
                (50, "Done", True),
            ]:
                stage = Stage.search(
                    [
                        ("name", "=", name),
                        ("project_ids", "in", [odoo_project.id]),
                    ],
                    limit=1,
                )
                if not stage:
                    Stage.create(
                        {
                            "name": name,
                            "sequence": sequence,
                            "fold": fold,
                            "project_ids": [Command.link(odoo_project.id)],
                        }
                    )
            project.odoo_project_id = odoo_project

    def _resolve_pack_controls(self):
        self.ensure_one()
        resolved = {}
        lines = self.pack_ids.mapped("control_line_ids").filtered("active")
        for line in lines:
            control_id = line.control_id.id
            if control_id not in resolved:
                resolved[control_id] = {
                    "control": line.control_id,
                    "sequence": line.sequence,
                    "required": line.required,
                    "pack_ids": set(),
                    "area_ids": set(),
                }
            resolved[control_id]["sequence"] = min(resolved[control_id]["sequence"], line.sequence)
            resolved[control_id]["required"] = bool(resolved[control_id]["required"] or line.required)
            resolved[control_id]["pack_ids"].add(line.pack_id.id)
            if line.area_id:
                resolved[control_id]["area_ids"].add(line.area_id.id)
        return resolved

    def _find_or_create_control_instance(self, control):
        self.ensure_one()
        ControlInstance = self.env["pm.qms.control.instance"]
        existing = ControlInstance.search(
            [
                ("organization_id", "=", self.organization_id.id),
                ("control_id", "=", control.id),
                ("company_id", "=", self.company_id.id),
                ("active", "=", True),
            ],
            limit=2,
        )
        if len(existing) > 1:
            raise UserError("Duplicate control instances exist for the same organization and control.")
        if existing:
            return existing[0]
        return ControlInstance.create(
            {
                "name": control.name,
                "control_id": control.id,
                "organization_id": self.organization_id.id,
                "process_id": self._target_process_for_control(control).id,
                "owner_id": self.project_manager_id.id or False,
                "target_date": self.target_date,
            }
        )

    def _target_process_for_control(self, control):
        self.ensure_one()
        source_process = control.process_id
        if not source_process.organization_id or source_process.organization_id == self.organization_id:
            return source_process
        target_code = f"{self.organization_id.code}-{source_process.code}"
        process = self.env["pm.qms.process"].search(
            [
                ("code", "=", target_code),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        if process:
            return process
        return self.env["pm.qms.process"].create(
            {
                "name": source_process.name,
                "code": target_code,
                "description": source_process.description,
                "organization_id": self.organization_id.id,
                "company_id": self.company_id.id,
                "process_type": source_process.process_type,
                "department": source_process.department,
                "inputs": source_process.inputs,
                "outputs": source_process.outputs,
            }
        )

    def _task_deadline(self):
        self.ensure_one()
        if not self.target_date:
            return False
        return fields.Datetime.to_string(datetime.combine(self.target_date, time(hour=17)))

    def _ensure_tasks_for_lines(self, lines):
        Task = self.env["project.task"]
        for project in self:
            if not project.odoo_project_id:
                continue
            ready_stage = self.env["project.task.type"].search(
                [
                    ("name", "=", "Ready"),
                    ("project_ids", "in", [project.odoo_project_id.id]),
                ],
                limit=1,
            )
            for line in lines.filtered(lambda item: item.implementation_project_id == project):
                activities = line.control_id.implementation_activity_ids.filtered("active")
                for activity in activities:
                    if activity.applicable_pack_ids and not (
                        activity.applicable_pack_ids & line.pack_ids
                    ):
                        continue
                    existing = Task.search(
                        [
                            ("pm_implementation_project_id", "=", project.id),
                            ("pm_implementation_control_id", "=", line.id),
                            ("pm_activity_id", "=", activity.id),
                        ],
                        limit=1,
                    )
                    if existing:
                        continue
                    user_ids = activity.responsible_user_id or project.project_manager_id
                    Task.create(
                        {
                            "name": activity.name,
                            "description": activity.description or activity.expected_output or False,
                            "project_id": project.odoo_project_id.id,
                            "stage_id": ready_stage.id if ready_stage else False,
                            "date_deadline": project._task_deadline(),
                            "user_ids": [Command.set(user_ids.ids)] if user_ids else False,
                            "pm_implementation_project_id": project.id,
                            "pm_implementation_control_id": line.id,
                            "pm_control_instance_id": line.control_instance_id.id,
                            "pm_activity_id": activity.id,
                            "pm_generated": True,
                            "pm_required": bool(line.required and activity.readiness_required),
                        }
                    )

    def _sync_framework(self, create_odoo_project=True):
        self._check_manager_permission()
        self._validate_active_packs()
        if create_odoo_project:
            self._ensure_odoo_project()
        created_or_updated = self.env["pm.qms.implementation.control"]
        for project in self:
            resolved = project._resolve_pack_controls()
            for info in resolved.values():
                control = info["control"]
                instance = project._find_or_create_control_instance(control)
                line = self.env["pm.qms.implementation.control"].search(
                    [
                        ("implementation_project_id", "=", project.id),
                        ("control_id", "=", control.id),
                    ],
                    limit=1,
                )
                pack_ids = list(info["pack_ids"])
                area_ids = list(info["area_ids"])
                if line:
                    line.write(
                        {
                            "control_instance_id": instance.id,
                            "pack_ids": [Command.set(sorted(set(line.pack_ids.ids + pack_ids)))],
                            "area_ids": [Command.set(sorted(set(line.area_ids.ids + area_ids)))],
                            "required": bool(line.required or info["required"]),
                            "sequence": min(line.sequence, info["sequence"]),
                            "active": True,
                        }
                    )
                else:
                    line = self.env["pm.qms.implementation.control"].create(
                        {
                            "implementation_project_id": project.id,
                            "control_id": control.id,
                            "control_instance_id": instance.id,
                            "pack_ids": [Command.set(pack_ids)],
                            "area_ids": [Command.set(area_ids)],
                            "required": info["required"],
                            "sequence": info["sequence"],
                        }
                    )
                created_or_updated |= line
            project._ensure_tasks_for_lines(created_or_updated)
            previous = project.state
            values = {
                "last_sync_date": fields.Datetime.now(),
            }
            if not project.generation_date:
                values["generation_date"] = fields.Datetime.now()
            if project.state == "draft":
                values["state"] = "generated"
            project.with_context(pm_qms_implementation_workflow=True).write(values)
            project._log_qms_event(
                event_type="system",
                previous_state=previous,
                new_state=project.state,
                decision="Framework synchronized",
            )
        return created_or_updated

    @api.model
    def generate_from_wizard(self, values):
        project = self.create(
            {
                "name": values["name"],
                "company_id": values["company_id"],
                "organization_id": values["organization_id"],
                "project_manager_id": values.get("project_manager_id") or False,
                "date_start": values["date_start"],
                "target_date": values["target_date"],
                "assessment_goal_type": values.get("assessment_goal_type") or "internal_readiness",
                "target_assessment_date": values.get("target_assessment_date") or False,
                "implementation_type": values["implementation_type"],
                "pack_ids": [Command.set(values["pack_ids"])],
                "notes": values.get("notes") or False,
            }
        )
        project._sync_framework(create_odoo_project=values.get("create_odoo_project", True))
        project._log_qms_event(event_type="system", decision="Implementation project generated")
        return project

    def action_sync_framework(self):
        self._sync_framework(create_odoo_project=True)
        return True

    def _write_state(self, state, decision, extra_values=None):
        self._check_manager_permission()
        for project in self:
            previous = project.state
            values = {"state": state}
            if extra_values:
                values.update(extra_values)
            project.with_context(pm_qms_implementation_workflow=True).write(values)
            project._log_qms_event(
                event_type="workflow",
                previous_state=previous,
                new_state=state,
                decision=decision,
            )

    def action_start_implementation(self):
        for project in self:
            if project.state not in {"generated", "readiness_review"}:
                raise UserError("Only generated or readiness-review projects can move to implementation.")
        self._write_state("in_progress", "Implementation started")

    def action_move_readiness_review(self):
        for project in self:
            if project.state not in {"generated", "in_progress"}:
                raise UserError("Only generated or in-progress projects can move to readiness review.")
        self._write_state("readiness_review", "Implementation moved to readiness review")

    def action_complete(self):
        for project in self:
            if project.state not in {"in_progress", "readiness_review", "generated"}:
                raise UserError("Only active implementation projects can be completed.")
            if project.readiness_percent < 100.0 and not project.completion_justification:
                raise UserError("Completion below 100% readiness requires a completion justification.")
        self._write_state(
            "completed",
            "Implementation project completed",
            {"actual_completion_date": fields.Date.context_today(self)},
        )

    def action_cancel(self):
        for project in self:
            if project.state == "completed":
                raise UserError("Completed implementation projects cannot be cancelled.")
        self._write_state("cancelled", "Implementation project cancelled")

    def _area_progress_values(self):
        self.ensure_one()
        controls = self.implementation_control_ids.filtered("active")
        values = []
        areas = controls.mapped("area_ids").sorted(lambda area: (area.sequence, area.code or "", area.id))
        for area in areas:
            lines = controls.filtered(lambda line, current=area: current in line.area_ids)
            not_applicable = lines.filtered(lambda line: line.readiness_state == "not_applicable")
            applicable = lines - not_applicable
            ready = applicable.filtered(lambda line: line.readiness_state == "ready")
            values.append(
                {
                    "area_id": area.id,
                    "sequence": area.sequence,
                    "name": area.name,
                    "control_count": len(lines),
                    "ready_controls": len(ready),
                    "partial_controls": len(applicable.filtered(lambda line: line.readiness_state == "partial")),
                    "gap_controls": len(applicable.filtered(lambda line: line.readiness_state == "gap")),
                    "not_applicable_controls": len(not_applicable),
                    "missing_evidence": sum(lines.mapped("missing_evidence_count")),
                    "open_tasks": sum(lines.mapped("open_activity_count")),
                    "overdue_tasks": sum(lines.mapped("overdue_activity_count")),
                    "readiness_percent": (len(ready) / len(applicable) * 100.0) if applicable else 0.0,
                }
            )
        return values

    def _recommended_next_action_values(self, limit=12):
        self.ensure_one()
        actions = []
        controls = self.implementation_control_ids.filtered(
            lambda line: line.active and line.readiness_state in {"gap", "partial"}
        ).sorted(lambda line: (0 if line.readiness_state == "gap" else 1, line.sequence, line.id))
        for line in controls:
            area = line.area_ids.sorted(lambda item: (item.sequence, item.code or "", item.id))[:1]
            values = {
                "sequence": len(actions) + 1,
                "priority": "high" if line.readiness_state == "gap" else "normal",
                "area_id": area.id if area else False,
                "implementation_control_id": line.id,
                "res_model": "pm.qms.implementation.control",
                "res_id": line.id,
            }
            if line.gap_reason == "implementation_not_started":
                values.update({"action_type": "start_control", "name": f"Start {line.control_code}", "reason": "Implementation has not started."})
            elif line.gap_reason == "missing_evidence":
                values.update({"action_type": "evidence", "name": f"Add evidence for {line.control_code}", "reason": f"{line.missing_evidence_count} mandatory evidence item(s) missing."})
            elif line.gap_reason == "evidence_under_review":
                values.update({"action_type": "review_evidence", "name": f"Review evidence for {line.control_code}", "reason": f"{line.evidence_under_review_count} evidence item(s) under review."})
            elif line.gap_reason in {"open_required_activities", "overdue_activities"}:
                task = line.task_ids.filtered(lambda task: task.pm_generated and task.pm_required and not task.is_closed).sorted(lambda task: (task.date_deadline or fields.Datetime.now(), task.id))[:1]
                values.update({"action_type": "activity", "name": f"Complete activity for {line.control_code}", "reason": f"{line.open_activity_count} required activity item(s) open.", "task_id": task.id if task else False, "res_model": "project.task" if task else "pm.qms.implementation.control", "res_id": task.id if task else line.id})
            else:
                values.update({"action_type": "implementation", "name": f"Review {line.control_code}", "reason": "Implementation status needs review."})
            actions.append(values)
            if len(actions) >= limit:
                break
        return actions

    def action_open_readiness_center(self):
        self.ensure_one()
        center = self.env["pm.qms.readiness.center"].create({"implementation_project_id": self.id})
        return {
            "type": "ir.actions.act_window",
            "name": "Readiness Center",
            "res_model": "pm.qms.readiness.center",
            "view_mode": "form",
            "res_id": center.id,
            "target": "current",
        }

    def action_run_readiness_assessment(self):
        self._check_manager_permission()
        assessments = self.env["pm.qms.readiness.assessment"]
        for project in self:
            assessment = assessments.create(
                {
                    "name": f"Readiness Assessment - {project.code}",
                    "implementation_project_id": project.id,
                    "assessment_date": fields.Date.context_today(project),
                    "assessor_id": self.env.user.id,
                }
            )
            assessment.action_complete_assessment()
            assessments |= assessment
            project._log_qms_event(
                event_type="review",
                decision="Readiness assessment completed",
                notes=f"Assessment {assessment.code}: {assessment.readiness_percent:.2f}%",
            )
        return {
            "type": "ir.actions.act_window",
            "name": "Readiness Assessments",
            "res_model": "pm.qms.readiness.assessment",
            "view_mode": "list,form",
            "domain": [("id", "in", assessments.ids)],
        }

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_implementation_workflow"):
            raise AccessError("Use implementation project workflow actions to change status.")
        return super().write(vals)

    def unlink(self):
        if any(project.state != "draft" for project in self):
            raise UserError("Only draft implementation projects can be deleted.")
        return super().unlink()

    def copy(self, default=None):
        raise UserError("Copying implementation projects is not supported because generated controls, tasks, and assessments are historical execution records.")
