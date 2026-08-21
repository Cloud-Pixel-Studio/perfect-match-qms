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
        "control_instance_id.evidence_ids.state",
        "control_instance_id.evidence_ids.evidence_requirement_id",
        "control_id.evidence_requirement_ids.mandatory",
        "task_ids.state",
        "task_ids.date_deadline",
        "task_ids.pm_required",
    )
    def _compute_readiness_components(self):
        now = fields.Datetime.now()
        for line in self:
            requirements = line.control_id.evidence_requirement_ids.filtered(lambda req: req.mandatory and req.active)
            evidence = line.control_instance_id.evidence_ids.filtered(lambda record: record.evidence_requirement_id in requirements)
            accepted_requirements = evidence.filtered(lambda record: record.state == "accepted").mapped("evidence_requirement_id")
            under_review = evidence.filtered(lambda record: record.state in {"submitted", "under_review"})
            required_tasks = line.task_ids.filtered(lambda task: task.pm_generated and task.pm_required)
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

            status = line.control_instance_id.implementation_status
            if line.control_instance_id.applicability == "not_applicable" or status == "not_applicable":
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
                line.task_ids.filtered(lambda task: task.pm_generated).write({"pm_required": line.required})
        return result

    def unlink(self):
        raise ValidationError("Implementation controls preserve deployment traceability and cannot be deleted.")
