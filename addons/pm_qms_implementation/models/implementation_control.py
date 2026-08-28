from datetime import datetime

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class PmQmsImplementationControl(models.Model):
    _name = "pm.qms.implementation.control"
    _description = "Perfect Match QMS Implementation Control"
    _order = "implementation_project_id, sequence, id"

    implementation_project_id = fields.Many2one(
        "pm.qms.implementation.project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="implementation_project_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="implementation_project_id.organization_id", store=True, readonly=True, index=True)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="restrict", index=True)
    control_instance_id = fields.Many2one("pm.qms.control.instance", required=True, ondelete="restrict", index=True)
    pack_ids = fields.Many2many(
        "pm.qms.framework.pack",
        "pm_qms_implementation_control_pack_rel",
        "implementation_control_id",
        "pack_id",
        string="Source Packs",
    )
    area_ids = fields.Many2many(
        "pm.qms.framework.area",
        "pm_qms_implementation_control_area_rel",
        "implementation_control_id",
        "area_id",
        string="Implementation Areas",
    )
    area_display = fields.Char(compute="_compute_area_display")
    required = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    control_code = fields.Char(related="control_id.code", readonly=True)
    control_name = fields.Char(related="control_id.name", readonly=True)
    applicability = fields.Selection(related="control_instance_id.applicability", readonly=True)
    implementation_status = fields.Selection(related="control_instance_id.implementation_status", readonly=True)
    guidance_purpose = fields.Text(related="control_id.guidance_purpose", readonly=True)
    guidance_why = fields.Text(related="control_id.guidance_why", readonly=True)
    implementation_guidance = fields.Text(related="control_id.implementation_guidance", readonly=True)
    recommended_steps = fields.Text(related="control_id.recommended_steps", readonly=True)
    recommended_tools = fields.Text(related="control_id.recommended_tools", readonly=True)
    evidence_guidance = fields.Text(related="control_id.evidence_guidance", readonly=True)
    practical_notes = fields.Text(related="control_id.practical_notes", readonly=True)
    external_alignment_summary = fields.Text(compute="_compute_external_alignment_summary")

    task_ids = fields.One2many("project.task", "pm_implementation_control_id", string="Generated Tasks")
    required_evidence_count = fields.Integer(compute="_compute_readiness_components", store=True)
    accepted_evidence_count = fields.Integer(compute="_compute_readiness_components", store=True)
    missing_evidence_count = fields.Integer(compute="_compute_readiness_components", store=True)
    evidence_under_review_count = fields.Integer(compute="_compute_readiness_components", store=True)
    required_activity_count = fields.Integer(compute="_compute_readiness_components", store=True)
    completed_activity_count = fields.Integer(compute="_compute_readiness_components", store=True)
    open_activity_count = fields.Integer(compute="_compute_readiness_components", store=True)
    overdue_activity_count = fields.Integer(compute="_compute_readiness_components", store=True)
    readiness_state = fields.Selection(
        [
            ("ready", "Ready"),
            ("partial", "Partial"),
            ("gap", "Gap"),
            ("not_applicable", "Not Applicable"),
        ],
        compute="_compute_readiness_components",
        store=True,
    )
    gap_reason = fields.Selection(
        [
            ("implementation_not_started", "Implementation Not Started"),
            ("implementation_in_progress", "Implementation In Progress"),
            ("missing_evidence", "Missing Evidence"),
            ("evidence_under_review", "Evidence Under Review"),
            ("open_required_activities", "Open Required Activities"),
            ("overdue_activities", "Overdue Activities"),
            ("other", "Other"),
        ],
        compute="_compute_readiness_components",
        store=True,
    )

    readiness_blocker_summary = fields.Text(
        compute="_compute_readiness_intelligence",
        string="Readiness Blockers",
        readonly=True,
    )
    recommended_next_action = fields.Text(
        compute="_compute_readiness_intelligence",
        string="Recommended Next Action",
        readonly=True,
    )
    recommended_done_when = fields.Text(
        compute="_compute_readiness_intelligence",
        string="Done When",
        readonly=True,
    )

    _implementation_control_uniq = models.Constraint(
        "UNIQUE(implementation_project_id, control_id)",
        "An implementation project can include each control only once.",
    )

    @api.constrains("implementation_project_id", "control_id", "control_instance_id", "pack_ids", "area_ids")
    def _check_relationships(self):
        for line in self:
            project = line.implementation_project_id
            if line.control_id.company_id != project.company_id:
                raise ValidationError("Implementation control must belong to the project company.")
            if line.control_instance_id.control_id != line.control_id:
                raise ValidationError("Implementation control line must use a control instance for the same control.")
            if line.control_instance_id.organization_id != project.organization_id:
                raise ValidationError("Implementation control instance must belong to the project organization.")
            if line.control_instance_id.company_id != project.company_id:
                raise ValidationError("Implementation control instance must belong to the project company.")
            if any(pack.company_id != project.company_id for pack in line.pack_ids):
                raise ValidationError("Source packs must belong to the project company.")
            if any(area.company_id != project.company_id for area in line.area_ids):
                raise ValidationError("Implementation areas must belong to the project company.")
            if line.area_ids and line.pack_ids and any(area.pack_id not in line.pack_ids for area in line.area_ids):
                raise ValidationError("Implementation areas must come from the selected source packs.")

    @api.depends("area_ids.name", "area_ids.code", "area_ids.sequence")
    def _compute_area_display(self):
        for line in self:
            areas = line.area_ids.sorted(lambda area: (area.sequence, area.code or "", area.id))
            line.area_display = ", ".join(areas.mapped("name"))

    @api.depends(
        "control_id.external_mapping_ids.standard_name",
        "control_id.external_mapping_ids.edition",
        "control_id.external_mapping_ids.reference",
        "control_id.external_mapping_ids.active",
    )
    def _compute_external_alignment_summary(self):
        for line in self:
            mappings = line.control_id.external_mapping_ids.filtered("active")
            if "review_status" in mappings._fields:
                mappings = mappings.filtered(lambda mapping: mapping.review_status == "approved")
            else:
                mappings = self.env["pm.qms.external.mapping"]
            parts = []
            for mapping in mappings.sorted(lambda item: (item.standard_name or "", item.edition or "", item.reference or "")):
                label = " ".join(part for part in [mapping.standard_name, mapping.edition] if part)
                parts.append(f"{label}: {mapping.reference}" if label else mapping.reference)
            line.external_alignment_summary = "\n".join(parts)

    @api.depends(
        "control_instance_id.implementation_status",
        "control_instance_id.applicability",
        "control_instance_id.evidence_ids.active",
        "control_instance_id.evidence_ids.state",
        "control_instance_id.evidence_ids.evidence_requirement_id",
        "control_id.evidence_requirement_ids.active",
        "control_id.evidence_requirement_ids.mandatory",
        "task_ids.state",
        "task_ids.date_deadline",
        "task_ids.pm_required",
    )
    def _compute_readiness_components(self):
        now = fields.Datetime.now()
        for line in self:
            status = line.control_instance_id.implementation_status
            not_applicable = (
                line.control_instance_id.applicability == "not_applicable"
                or status == "not_applicable"
            )
            requirements = line.control_id.evidence_requirement_ids.filtered(
                lambda req: req.mandatory and req.active
            )
            evidence = line.control_instance_id.evidence_ids.filtered(
                lambda record: record.active
                and record.evidence_requirement_id in requirements
            )
            accepted_requirements = evidence.filtered(
                lambda record: record.state == "accepted"
            ).mapped("evidence_requirement_id")
            missing_requirements = requirements.filtered(
                lambda requirement: requirement.id not in set(accepted_requirements.ids)
            )
            under_review = evidence.filtered(
                lambda record: record.evidence_requirement_id in missing_requirements
                and record.state in {"submitted", "under_review"}
            )
            required_tasks = line.task_ids.filtered(
                lambda task: task.pm_generated
                and task.pm_required
            )
            completed_tasks = required_tasks.filtered("is_closed")
            open_tasks = required_tasks - completed_tasks
            overdue_tasks = open_tasks.filtered(lambda task: task.date_deadline and task.date_deadline < now)

            line.required_evidence_count = len(requirements)
            line.accepted_evidence_count = len(set(accepted_requirements.ids))
            line.missing_evidence_count = max(line.required_evidence_count - line.accepted_evidence_count, 0)
            line.evidence_under_review_count = len(under_review)
            line.required_activity_count = len(required_tasks)
            line.completed_activity_count = len(completed_tasks)
            line.open_activity_count = len(open_tasks)
            line.overdue_activity_count = len(overdue_tasks)

            if not_applicable:
                line.readiness_state = "not_applicable"
                line.gap_reason = False
            elif status == "implemented" and not line.missing_evidence_count and not line.open_activity_count:
                line.readiness_state = "ready"
                line.gap_reason = False
            elif status == "not_started":
                line.readiness_state = "gap"
                line.gap_reason = "implementation_not_started"
            elif line.missing_evidence_count:
                line.readiness_state = "gap"
                line.gap_reason = "missing_evidence"
            elif line.evidence_under_review_count:
                line.readiness_state = "partial"
                line.gap_reason = "evidence_under_review"
            elif line.overdue_activity_count:
                line.readiness_state = "partial"
                line.gap_reason = "overdue_activities"
            elif line.open_activity_count:
                line.readiness_state = "partial"
                line.gap_reason = "open_required_activities"
            elif status in {"in_progress", "evidence_required", "under_review"}:
                line.readiness_state = "partial"
                line.gap_reason = "implementation_in_progress"
            else:
                line.readiness_state = "gap"
                line.gap_reason = "other"

    @api.depends(
        "readiness_state", "gap_reason", "implementation_status", "applicability",
        "required_evidence_count", "accepted_evidence_count", "missing_evidence_count",
        "evidence_under_review_count", "required_activity_count",
        "open_activity_count", "overdue_activity_count",
        "task_ids.name", "task_ids.date_deadline", "task_ids.is_closed",
        "task_ids.pm_generated", "task_ids.pm_required", "task_ids.pm_activity_id",
        "task_ids.pm_activity_id.success_criteria",
        "task_ids.pm_activity_id.expected_output",
        "control_instance_id.evidence_ids.active",
        "control_instance_id.evidence_ids.state",
        "control_instance_id.evidence_ids.evidence_requirement_id",
        "control_id.evidence_requirement_ids.active",
        "control_id.evidence_requirement_ids.mandatory",
        "control_id.evidence_requirement_ids.acceptance_criteria",
    )
    def _compute_readiness_intelligence(self):
        for line in self:
            values = line._readiness_intelligence_values()
            line.readiness_blocker_summary = values["blocker_summary"]
            line.recommended_next_action = values["name"]
            line.recommended_done_when = values["done_when"]

    def _readiness_intelligence_values(self):
        """Return deterministic, non-persistent guidance for one control."""
        self.ensure_one()
        empty = {
            "blocker_summary": False, "action_type": False, "priority": False,
            "name": False, "reason": False, "done_when": False,
            "task_id": False, "evidence_id": False,
            "evidence_requirement_id": False, "res_model": False, "res_id": False,
        }
        if self.readiness_state in {"ready", "not_applicable"}:
            return empty

        requirements = self.control_id.evidence_requirement_ids.filtered(
            lambda req: req.mandatory and req.active
        ).sorted(lambda req: (req.sequence, req.id))
        evidence = self.control_instance_id.evidence_ids.filtered(
            lambda record: record.active and record.evidence_requirement_id in requirements
        ).sorted(lambda record: (record.evidence_requirement_id.sequence, record.id))
        accepted_ids = set(
            evidence.filtered(lambda record: record.state == "accepted")
            .mapped("evidence_requirement_id").ids
        )
        missing = requirements.filtered(lambda req: req.id not in accepted_ids)
        blocking_evidence = evidence.filtered(
            lambda record: record.evidence_requirement_id in missing
        )
        under_review = blocking_evidence.filtered(
            lambda record: record.state in {"submitted", "under_review"}
        )
        rejected = blocking_evidence.filtered(lambda record: record.state == "rejected")
        expired = blocking_evidence.filtered(lambda record: record.state == "expired")
        required_tasks = self.task_ids.filtered(
            lambda task: task.pm_generated and task.pm_required
        )
        open_tasks = required_tasks.filtered(lambda task: not task.is_closed)
        overdue = open_tasks.filtered(
            lambda task: task.date_deadline and task.date_deadline < fields.Datetime.now()
        )

        blockers = []
        if self.implementation_status == "not_started":
            blockers.append("Implementation has not started.")
        if overdue:
            blockers.append(f"{len(overdue)} overdue required activity item(s).")
        if open_tasks:
            blockers.append(f"{len(open_tasks)} required activity item(s) remain open.")
        if under_review:
            blockers.append(f"{len(under_review)} evidence item(s) are under review.")
        if rejected:
            blockers.append(f"{len(rejected)} evidence item(s) were rejected and require correction.")
        if expired:
            blockers.append(f"{len(expired)} evidence item(s) are expired and require renewal or replacement.")
        if missing:
            blockers.append(
                f"{len(missing)} mandatory evidence requirement(s) lack accepted evidence."
            )
        if not blockers:
            blockers.append("Implementation status requires a manual readiness review.")

        def task_deadline(item):
            return str(item.date_deadline) if item.date_deadline else "9999-12-31"

        def task_sequence(item):
            return item.pm_activity_id.sequence or 10**9

        if overdue:
            task = overdue.sorted(lambda item: (task_deadline(item), task_sequence(item), item.id))[:1]
        else:
            task = open_tasks.sorted(lambda item: (task_sequence(item), task_deadline(item), item.id))[:1]
        evidence_record = (under_review[:1] or rejected[:1] or expired[:1])
        requirement = missing[:1]
        if self.implementation_status == "not_started":
            action_type, priority = "start_control", "high"
            name = f"Start implementation for {self.control_code}"
            reason = "Implementation has not started."
            done_when = "The control implementation is started and its owner is assigned."
            res_model, res_id = "pm.qms.implementation.control", self.id
        elif overdue:
            action_type, priority = "activity", "high"
            name = f"Complete overdue activity for {self.control_code}"
            reason = f"{len(overdue)} required activity item(s) are overdue."
            done_when = task.pm_activity_id.success_criteria or task.pm_activity_id.expected_output or "The overdue activity is completed and its outcome is recorded."
            res_model, res_id = "project.task", task.id
        elif open_tasks:
            action_type, priority = "activity", "normal"
            name = f"Complete activity for {self.control_code}"
            reason = f"{len(open_tasks)} required activity item(s) remain open."
            done_when = task.pm_activity_id.success_criteria or task.pm_activity_id.expected_output or "The selected activity is completed and its outcome is recorded."
            res_model, res_id = "project.task", task.id
        elif under_review:
            action_type, priority = "review_evidence", "normal"
            name = f"Review evidence for {self.control_code}"
            reason = f"{len(under_review)} evidence item(s) are under review."
            done_when = "An authorized reviewer records the evidence decision."
            res_model, res_id = "pm.qms.evidence", evidence_record.id
        elif rejected:
            action_type, priority = "evidence_correction", "high"
            name = f"Correct or replace rejected evidence for {self.control_code}"
            reason = f"{len(rejected)} evidence item(s) were rejected and do not satisfy the formal requirement."
            done_when = "Corrected or replacement evidence has been submitted and an authorized reviewer has accepted evidence satisfying the requirement acceptance criteria."
            res_model, res_id = "pm.qms.evidence", evidence_record.id
        elif expired:
            action_type, priority = "evidence_renewal", "high"
            name = f"Renew or replace expired evidence for {self.control_code}"
            reason = f"{len(expired)} evidence item(s) are expired and no current accepted evidence satisfies the requirement."
            done_when = "Current replacement or renewed evidence has been submitted and accepted against the formal requirement."
            res_model, res_id = "pm.qms.evidence", evidence_record.id
        elif requirement:
            action_type = "evidence"
            priority = "high" if self.readiness_state == "gap" else "normal"
            name = f"Add evidence for {self.control_code}"
            reason = f"{len(missing)} mandatory evidence item(s) lack accepted evidence."
            done_when = requirement.acceptance_criteria or "Evidence satisfying the requirement acceptance criteria is submitted."
            res_model, res_id = "pm.qms.evidence", False
        elif self.implementation_status in {"implemented", "in_progress", "evidence_required", "under_review"}:
            action_type, priority = "implementation", "normal"
            name = f"Complete final review for {self.control_code}"
            reason = "Implementation status requires a final readiness review."
            done_when = "The implementation control is reviewed and its readiness decision is recorded."
            res_model, res_id = "pm.qms.implementation.control", self.id
        else:
            action_type, priority = "implementation", "low"
            name = f"Review {self.control_code}"
            reason = "Implementation status needs review."
            done_when = "The implementation control is reviewed and its readiness decision is recorded."
            res_model, res_id = "pm.qms.implementation.control", self.id

        return {
            "blocker_summary": " ".join(blockers),
            "action_type": action_type, "priority": priority, "name": name,
            "reason": reason, "done_when": done_when,
            "task_id": task.id if task and res_model == "project.task" else False,
            "evidence_id": evidence_record.id if evidence_record and res_model == "pm.qms.evidence" else False,
            "evidence_requirement_id": requirement.id if requirement and action_type == "evidence" else False,
            "res_model": res_model, "res_id": res_id,
        }

    def action_generate_missing_tasks(self):
        projects = self.mapped("implementation_project_id")
        for project in projects:
            project._ensure_tasks_for_lines(self.filtered(lambda line: line.implementation_project_id == project))
        return True

    def action_open_tasks(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "pm_qms_implementation.action_pm_qms_implementation_activities"
        )
        action["domain"] = [
            ("pm_implementation_project_id", "=", self.implementation_project_id.id),
            ("pm_implementation_control_id", "=", self.id),
            ("pm_generated", "=", True),
        ]
        action["context"] = {
            "default_pm_implementation_project_id": self.implementation_project_id.id,
            "default_pm_implementation_control_id": self.id,
            "default_project_id": self.implementation_project_id.odoo_project_id.id,
        }
        action["name"] = "Activities"
        return action

    def action_open_control_instance(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Operational Control Record",
            "res_model": "pm.qms.control.instance",
            "view_mode": "form",
            "res_id": self.control_instance_id.id,
        }

    def action_open_evidence(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("pm_qms_evidence.action_pm_qms_evidence")
        action["domain"] = [("control_instance_id", "=", self.control_instance_id.id)]
        action["context"] = {
            "default_control_instance_id": self.control_instance_id.id,
            "default_organization_id": self.organization_id.id,
        }
        action["name"] = "Evidence"
        return action

    def write(self, vals):
        result = super().write(vals)
        if "required" in vals:
            for line in self:
                for task in line.task_ids.filtered(lambda item: item.pm_generated):
                    task.write(
                        {
                            "pm_required": bool(
                                line.required and task.pm_activity_id.readiness_required
                            )
                        }
                    )
        return result

    def unlink(self):
        raise ValidationError("Implementation controls preserve deployment traceability and cannot be deleted.")
