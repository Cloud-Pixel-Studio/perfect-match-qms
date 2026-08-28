from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class PmQmsEvidence(models.Model):
    _name = "pm.qms.evidence"
    _description = "Perfect Match QMS Evidence"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "evidence_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    control_instance_id = fields.Many2one(
        "pm.qms.control.instance",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="control_instance_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one(
        "pm.qms.organization",
        related="control_instance_id.organization_id",
        store=True,
        readonly=True,
        index=True,
    )
    evidence_requirement_id = fields.Many2one(
        "pm.qms.evidence.requirement",
        required=True,
        ondelete="restrict",
        index=True,
    )
    requirement_description = fields.Text(
        related="evidence_requirement_id.description",
        string="Requirement Description",
        readonly=True,
    )
    requirement_acceptance_criteria = fields.Text(
        related="evidence_requirement_id.acceptance_criteria",
        string="Requirement Acceptance Criteria",
        readonly=True,
    )
    process_id = fields.Many2one(
        "pm.qms.process",
        related="control_instance_id.process_id",
        store=True,
        readonly=True,
        index=True,
    )
    evidence_type = fields.Selection(
        [
            ("document", "Document"),
            ("record", "Record"),
            ("report", "Report"),
            ("approval", "Approval"),
            ("system_record", "System Record"),
            ("meeting", "Meeting"),
            ("training", "Training"),
            ("metric", "Metric"),
            ("other", "Other"),
        ],
        default="record",
        required=True,
    )
    description = fields.Text()
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    evidence_date = fields.Date(default=fields.Date.context_today)
    expiration_date = fields.Date()
    review_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("under_review", "Under Review"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "pm_qms_evidence_attachment_rel",
        "evidence_id",
        "attachment_id",
        string="Attachments",
    )
    document_ids = fields.Many2many(
        "pm.qms.document",
        "pm_qms_evidence_document_rel",
        "evidence_id",
        "document_id",
        string="Controlled Documents",
    )
    reviewer_id = fields.Many2one("res.users", string="Reviewer")
    review_notes = fields.Text()
    reviewed_on = fields.Datetime()
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("evidence_requirement_id") and not vals.get("evidence_type"):
                requirement = self.env["pm.qms.evidence.requirement"].browse(vals["evidence_requirement_id"])
                vals["evidence_type"] = requirement.evidence_type
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.constrains("control_instance_id", "evidence_requirement_id")
    def _check_requirement_alignment(self):
        for evidence in self:
            if evidence.evidence_requirement_id.control_id != evidence.control_instance_id.control_id:
                raise ValidationError("Evidence requirement must belong to the same framework control as the control instance.")

    @api.constrains("document_ids")
    def _check_document_alignment(self):
        for evidence in self:
            if any(document.company_id != evidence.company_id for document in evidence.document_ids):
                raise ValidationError("Evidence documents must belong to the same company as the evidence record.")
            if any(document.organization_id != evidence.organization_id for document in evidence.document_ids):
                raise ValidationError("Evidence documents must belong to the same organization as the evidence record.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can review evidence.")

    def action_submit(self):
        previous = {evidence.id: evidence.state for evidence in self}
        self.with_context(pm_qms_evidence_workflow=True).write({"state": "submitted"})
        for evidence in self:
            evidence._log_qms_event(
                event_type="workflow",
                previous_state=previous[evidence.id],
                new_state="submitted",
                decision="Evidence submitted",
            )

    def action_review(self):
        self._check_manager_permission()
        previous = {evidence.id: evidence.state for evidence in self}
        self.with_context(pm_qms_evidence_workflow=True).write(
            {
                "state": "under_review",
                "reviewer_id": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
                "review_date": fields.Date.context_today(self),
            }
        )
        for evidence in self:
            evidence._log_qms_event(
                event_type="review",
                previous_state=previous[evidence.id],
                new_state="under_review",
                reviewer=self.env.user,
                decision="Evidence review started",
                notes=evidence.review_notes,
            )

    def action_accept(self):
        self._check_manager_permission()
        previous = {evidence.id: evidence.state for evidence in self}
        self.with_context(pm_qms_evidence_workflow=True).write(
            {
                "state": "accepted",
                "reviewer_id": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
                "review_date": fields.Date.context_today(self),
            }
        )
        for evidence in self:
            evidence._log_qms_event(
                event_type="approval",
                previous_state=previous[evidence.id],
                new_state="accepted",
                reviewer=self.env.user,
                decision="Evidence accepted",
                notes=evidence.review_notes,
            )

    def action_reject(self):
        self._check_manager_permission()
        previous = {evidence.id: evidence.state for evidence in self}
        self.with_context(pm_qms_evidence_workflow=True).write(
            {
                "state": "rejected",
                "reviewer_id": self.env.user.id,
                "reviewed_on": fields.Datetime.now(),
                "review_date": fields.Date.context_today(self),
            }
        )
        for evidence in self:
            evidence._log_qms_event(
                event_type="review",
                previous_state=previous[evidence.id],
                new_state="rejected",
                reviewer=self.env.user,
                decision="Evidence rejected",
                notes=evidence.review_notes,
            )

    def action_expire(self):
        self._check_manager_permission()
        previous = {evidence.id: evidence.state for evidence in self}
        self.with_context(pm_qms_evidence_workflow=True).write({"state": "expired"})
        for evidence in self:
            evidence._log_qms_event(
                event_type="closure",
                previous_state=previous[evidence.id],
                new_state="expired",
                reviewer=self.env.user,
                decision="Evidence expired",
            )

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_evidence_workflow"):
            raise AccessError("Use evidence workflow actions to change evidence state.")
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result
