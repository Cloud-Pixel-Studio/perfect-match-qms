from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsDocumentRevision(models.Model):
    _name = "pm.qms.document.revision"
    _description = "Perfect Match QMS Document Revision"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "document_id, revision_date desc, id desc"

    document_id = fields.Many2one("pm.qms.document", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="document_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="document_id.organization_id", store=True, readonly=True)
    process_id = fields.Many2one(related="document_id.process_id", store=True, readonly=True)
    revision = fields.Char(required=True, tracking=True)
    revision_date = fields.Date(default=fields.Date.context_today, required=True)
    effective_date = fields.Date()
    review_date = fields.Date()
    prepared_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    reviewed_by = fields.Many2one("res.users")
    approved_by = fields.Many2one("res.users")
    approval_date = fields.Datetime()
    change_summary = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("superseded", "Superseded"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Revision File",
        help="File content is stored through Odoo attachments; revisions only link to the attachment.",
    )

    _revision_document_uniq = models.Constraint(
        "UNIQUE(document_id, revision)",
        "Revision must be unique per controlled document.",
    )

    @api.constrains("state", "document_id")
    def _check_single_active_revision(self):
        for revision in self.filtered(lambda item: item.state == "active"):
            active_count = self.search_count(
                [
                    ("document_id", "=", revision.document_id.id),
                    ("state", "=", "active"),
                    ("id", "!=", revision.id),
                ]
            )
            if active_count:
                raise ValidationError("Only one active revision is allowed for a controlled document.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can perform document revision workflow actions.")

    def action_submit_for_review(self):
        self._check_manager_permission()
        revisions = self.filtered(lambda revision: revision.state in ("draft", "rejected"))
        previous = {revision.id: revision.state for revision in revisions}
        revisions.with_context(pm_qms_document_workflow=True).write({"state": "under_review"})
        for revision in revisions:
            revision._log_qms_event(
                event_type="workflow",
                previous_state=previous[revision.id],
                new_state="under_review",
                reviewer=self.env.user,
                decision="Revision submitted for review",
            )

    def action_approve(self):
        self._check_manager_permission()
        revisions = self.filtered(lambda revision: revision.state == "under_review")
        previous = {revision.id: revision.state for revision in revisions}
        revisions.with_context(pm_qms_document_workflow=True).write(
            {
                "state": "approved",
                "reviewed_by": self.env.user.id,
                "approved_by": self.env.user.id,
                "approval_date": fields.Datetime.now(),
            }
        )
        for revision in revisions:
            revision._log_qms_event(
                event_type="approval",
                previous_state=previous[revision.id],
                new_state="approved",
                reviewer=self.env.user,
                approver=self.env.user,
                decision="Revision approved",
            )

    def action_reject(self):
        self._check_manager_permission()
        revisions = self.filtered(lambda revision: revision.state == "under_review")
        previous = {revision.id: revision.state for revision in revisions}
        revisions.with_context(pm_qms_document_workflow=True).write(
            {
                "state": "rejected",
                "reviewed_by": self.env.user.id,
            }
        )
        for revision in revisions:
            revision._log_qms_event(
                event_type="review",
                previous_state=previous[revision.id],
                new_state="rejected",
                reviewer=self.env.user,
                decision="Revision rejected",
            )

    def action_activate(self):
        self._check_manager_permission()
        for revision in self:
            if revision.state not in ("approved", "active"):
                raise UserError("Only approved revisions can be activated.")
            previous_active = revision.document_id.revision_ids.filtered(
                lambda item: item.state == "active" and item != revision
            )
            previous_active.with_context(pm_qms_document_workflow=True).write({"state": "superseded"})
            for previous_revision in previous_active:
                previous_revision._log_qms_event(
                    event_type="workflow",
                    previous_state="active",
                    new_state="superseded",
                    approver=self.env.user,
                    decision="Revision superseded",
                )
            previous = revision.state
            revision.with_context(pm_qms_document_workflow=True).write(
                {
                    "state": "active",
                    "effective_date": revision.effective_date or fields.Date.context_today(revision),
                }
            )
            revision.document_id.with_context(pm_qms_document_workflow=True).write(
                {
                    "current_revision_id": revision.id,
                    "state": "active",
                    "active": True,
                }
            )
            revision._log_qms_event(
                event_type="approval",
                previous_state=previous,
                new_state="active",
                approver=self.env.user,
                decision="Revision activated",
            )

    def action_supersede(self):
        self._check_manager_permission()
        revisions = self.filtered(lambda revision: revision.state == "active")
        revisions.with_context(pm_qms_document_workflow=True).write({"state": "superseded"})
        for revision in revisions:
            revision._log_qms_event(
                event_type="workflow",
                previous_state="active",
                new_state="superseded",
                approver=self.env.user,
                decision="Revision superseded",
            )

    def unlink(self):
        if any(revision.state != "draft" for revision in self):
            raise UserError("Historical document revisions cannot be deleted.")
        return super().unlink()

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_document_workflow"):
            raise AccessError("Use controlled revision workflow actions to change revision status.")
        result = super().write(vals)
        if "attachment_id" in vals:
            for revision in self.filtered("attachment_id"):
                revision.attachment_id.write({"res_model": revision._name, "res_id": revision.id})
        return result
