from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsRootCauseAnalysis(models.Model):
    _name = "pm.qms.root.cause.analysis"
    _description = "Perfect Match QMS Root Cause Analysis"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code desc, id desc"
    _rec_name = "code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one("res.company", related="organization_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True)
    method = fields.Selection(
        [("5why", "5 Why"), ("cause_effect", "Cause-and-Effect"), ("fault_tree", "Fault Tree"), ("other", "Other")],
        default="5why",
        required=True,
        tracking=True,
    )
    problem_statement = fields.Text(required=True)
    root_cause = fields.Text()
    contributing_causes = fields.Text()
    evidence_summary = fields.Text()
    reviewer_id = fields.Many2one("res.users")
    approved_by_id = fields.Many2one("res.users", readonly=True)
    approved_on = fields.Datetime(readonly=True)
    complaint_id = fields.Many2one("pm.qms.customer.complaint", ondelete="restrict")
    ncr_id = fields.Many2one("pm.qms.nonconformity", ondelete="restrict")
    eight_d_id = fields.Many2one("pm.qms.eight.d", ondelete="cascade")
    supplier_issue_id = fields.Many2one("pm.qms.supplier.issue", ondelete="restrict")
    scar_id = fields.Many2one("pm.qms.scar", ondelete="restrict")
    why_line_ids = fields.One2many("pm.qms.root.cause.line", "analysis_id", string="Why / Cause Lines")
    related_evidence_ids = fields.Many2many("pm.qms.evidence", "pm_qms_rca_evidence_rel", "analysis_id", "evidence_id")
    attachment_ids = fields.Many2many("ir.attachment", "pm_qms_rca_attachment_rel", "analysis_id", "attachment_id")
    state = fields.Selection(
        [("draft", "Draft"), ("in_review", "In Review"), ("approved", "Approved"), ("cancelled", "Cancelled")],
        default="draft",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint("UNIQUE(code, company_id)", "Root-cause analysis code must be unique per company.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.root.cause.analysis") or "RCA-0000"
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.constrains("organization_id", "process_id")
    def _check_process_alignment(self):
        for analysis in self:
            if analysis.process_id.company_id != analysis.company_id:
                raise ValidationError("Root-cause process must belong to the same company as the organization.")
            if analysis.process_id.organization_id and analysis.process_id.organization_id != analysis.organization_id:
                raise ValidationError("Root-cause process must belong to the selected organization.")

    @api.constrains("complaint_id", "ncr_id", "eight_d_id", "supplier_issue_id", "scar_id", "related_evidence_ids")
    def _check_source_alignment(self):
        for analysis in self:
            for sources in (analysis.complaint_id, analysis.ncr_id, analysis.eight_d_id, analysis.supplier_issue_id, analysis.scar_id):
                for source in sources:
                    if source.company_id != analysis.company_id or source.organization_id != analysis.organization_id:
                        raise ValidationError("Root-cause sources must match the analysis company and organization.")
            for evidence in analysis.related_evidence_ids:
                if evidence.company_id != analysis.company_id or evidence.organization_id != analysis.organization_id:
                    raise ValidationError("Root-cause evidence must match the analysis company and organization.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can approve root-cause analysis.")

    def _transition(self, state, decision, event_type="workflow", values=None):
        self._check_manager_permission()
        for analysis in self:
            previous = analysis.state
            payload = {"state": state}
            if values:
                payload.update(values)
            analysis.with_context(pm_qms_root_cause_workflow=True).write(payload)
            analysis._log_qms_event(event_type=event_type, previous_state=previous, new_state=state, reviewer=self.env.user, approver=self.env.user if event_type == "approval" else None, decision=decision)

    def action_submit_review(self):
        self._transition("in_review", "Root-cause analysis submitted for review")

    def action_approve(self):
        for analysis in self:
            if not analysis.root_cause:
                raise UserError("Root cause is required before approval.")
        self._transition("approved", "Root-cause analysis approved", event_type="approval", values={"approved_by_id": self.env.user.id, "approved_on": fields.Datetime.now()})

    def action_cancel(self):
        self._transition("cancelled", "Root-cause analysis cancelled", event_type="closure")

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_root_cause_workflow"):
            raise AccessError("Use root-cause workflow actions to change status.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(analysis.state != "draft" for analysis in self):
            raise UserError("Only draft root-cause analyses can be deleted.")
        return super().unlink()


class PmQmsRootCauseLine(models.Model):
    _name = "pm.qms.root.cause.line"
    _description = "Perfect Match QMS Root Cause Line"
    _order = "analysis_id, sequence, id"

    analysis_id = fields.Many2one("pm.qms.root.cause.analysis", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="analysis_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="analysis_id.organization_id", store=True, readonly=True, index=True)
    sequence = fields.Integer(default=1)
    question = fields.Char(required=True)
    answer = fields.Text()
    evidence = fields.Text()

    def unlink(self):
        if any(line.analysis_id.state != "draft" for line in self):
            raise UserError("Root-cause lines cannot be deleted after review starts.")
        return super().unlink()
