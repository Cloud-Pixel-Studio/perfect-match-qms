from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError


class PmQmsReadinessAssessment(models.Model):
    _name = "pm.qms.readiness.assessment"
    _description = "Perfect Match QMS Readiness Assessment"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "assessment_date desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True)
    code = fields.Char(default="New", required=True, copy=False)
    implementation_project_id = fields.Many2one(
        "pm.qms.implementation.project",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(related="implementation_project_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="implementation_project_id.organization_id", store=True, readonly=True, index=True)
    assessment_date = fields.Date(required=True, default=fields.Date.context_today)
    assessor_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    notes = fields.Text()
    item_ids = fields.One2many(
        "pm.qms.readiness.assessment.item",
        "assessment_id",
        string="Assessment Items",
        copy=False,
    )
    total_controls = fields.Integer(readonly=True)
    applicable_controls = fields.Integer(readonly=True)
    ready_controls = fields.Integer(readonly=True)
    partial_controls = fields.Integer(readonly=True)
    gap_controls = fields.Integer(readonly=True)
    not_applicable_controls = fields.Integer(readonly=True)
    readiness_percent = fields.Float(readonly=True)
    evidence_completion_percent = fields.Float(readonly=True)
    activity_completion_percent = fields.Float(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.readiness.assessment") or "PM-RA-00000"
        return super().create(vals_list)

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can run readiness assessments.")

    def _item_values(self, line):
        source_packs = ", ".join(f"{pack.code} v{pack.version}" for pack in line.pack_ids.sorted("code"))
        return {
            "implementation_control_id": line.id,
            "control_instance_id": line.control_instance_id.id,
            "control_code_snapshot": line.control_id.code,
            "control_name_snapshot": line.control_id.name,
            "applicability_snapshot": line.control_instance_id.applicability,
            "implementation_status_snapshot": line.control_instance_id.implementation_status,
            "required_evidence_snapshot": line.required_evidence_count,
            "accepted_evidence_snapshot": line.accepted_evidence_count,
            "missing_evidence_snapshot": line.missing_evidence_count,
            "required_activity_snapshot": line.required_activity_count,
            "completed_activity_snapshot": line.completed_activity_count,
            "open_activity_snapshot": line.open_activity_count,
            "readiness_state_snapshot": line.readiness_state,
            "gap_reason_snapshot": line.gap_reason,
            "source_pack_snapshot": source_packs,
        }

    def action_complete_assessment(self):
        self._check_manager_permission()
        for assessment in self:
            if assessment.state != "draft":
                raise UserError("Only draft readiness assessments can be completed.")
            lines = assessment.implementation_project_id.implementation_control_ids.filtered("active")
            item_commands = [Command.create(assessment._item_values(line)) for line in lines]
            applicable = lines.filtered(lambda line: line.readiness_state != "not_applicable")
            ready = applicable.filtered(lambda line: line.readiness_state == "ready")
            required_evidence = sum(applicable.mapped("required_evidence_count"))
            accepted_evidence = sum(applicable.mapped("accepted_evidence_count"))
            required_activity = sum(applicable.mapped("required_activity_count"))
            completed_activity = sum(applicable.mapped("completed_activity_count"))
            values = {
                "item_ids": [Command.clear()] + item_commands,
                "total_controls": len(lines),
                "applicable_controls": len(applicable),
                "ready_controls": len(ready),
                "partial_controls": len(applicable.filtered(lambda line: line.readiness_state == "partial")),
                "gap_controls": len(applicable.filtered(lambda line: line.readiness_state == "gap")),
                "not_applicable_controls": len(lines.filtered(lambda line: line.readiness_state == "not_applicable")),
                "readiness_percent": (len(ready) / len(applicable) * 100.0) if applicable else 0.0,
                "evidence_completion_percent": (accepted_evidence / required_evidence * 100.0) if required_evidence else 100.0,
                "activity_completion_percent": (completed_activity / required_activity * 100.0) if required_activity else 100.0,
                "state": "completed",
            }
            assessment.with_context(pm_qms_assessment_workflow=True).write(values)
            assessment._log_qms_event(
                event_type="review",
                new_state="completed",
                reviewer=self.env.user,
                decision="Readiness assessment completed",
                notes=f"Implementation readiness {assessment.readiness_percent:.2f}%",
            )
        return True

    def action_cancel(self):
        for assessment in self:
            if assessment.state == "completed":
                raise UserError("Completed readiness assessments cannot be cancelled.")
        self.with_context(pm_qms_assessment_workflow=True).write({"state": "cancelled"})

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_assessment_workflow"):
            raise AccessError("Use readiness assessment workflow actions to change status.")
        if any(assessment.state == "completed" for assessment in self) and not self.env.context.get("pm_qms_assessment_workflow"):
            raise AccessError("Completed readiness assessments are historical snapshots and cannot be changed.")
        return super().write(vals)

    def unlink(self):
        if any(assessment.state != "draft" for assessment in self):
            raise UserError("Only draft readiness assessments can be deleted.")
        return super().unlink()

    def copy(self, default=None):
        raise UserError("Copying readiness assessments is not supported because they are historical snapshots.")


class PmQmsReadinessAssessmentItem(models.Model):
    _name = "pm.qms.readiness.assessment.item"
    _description = "Perfect Match QMS Readiness Assessment Item"
    _order = "assessment_id, control_code_snapshot, id"

    assessment_id = fields.Many2one("pm.qms.readiness.assessment", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="assessment_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="assessment_id.organization_id", store=True, readonly=True, index=True)
    implementation_control_id = fields.Many2one("pm.qms.implementation.control", required=True, ondelete="restrict")
    control_instance_id = fields.Many2one("pm.qms.control.instance", required=True, ondelete="restrict")
    control_code_snapshot = fields.Char(required=True)
    control_name_snapshot = fields.Char(required=True)
    applicability_snapshot = fields.Char()
    implementation_status_snapshot = fields.Char()
    required_evidence_snapshot = fields.Integer()
    accepted_evidence_snapshot = fields.Integer()
    missing_evidence_snapshot = fields.Integer()
    required_activity_snapshot = fields.Integer()
    completed_activity_snapshot = fields.Integer()
    open_activity_snapshot = fields.Integer()
    readiness_state_snapshot = fields.Selection(
        [
            ("ready", "Ready"),
            ("partial", "Partial"),
            ("gap", "Gap"),
            ("not_applicable", "Not Applicable"),
        ],
        required=True,
    )
    gap_reason_snapshot = fields.Char()
    source_pack_snapshot = fields.Text()
    notes = fields.Text()

    def write(self, vals):
        if any(item.assessment_id.state == "completed" for item in self):
            raise AccessError("Completed readiness assessment items are immutable historical snapshots.")
        return super().write(vals)

    def unlink(self):
        if any(item.assessment_id.state == "completed" for item in self):
            raise AccessError("Completed readiness assessment items cannot be deleted.")
        return super().unlink()
