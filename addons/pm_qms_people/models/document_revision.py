from odoo import fields, models


class PmQmsDocumentRevision(models.Model):
    _inherit = "pm.qms.document.revision"

    acknowledgment_ids = fields.One2many("pm.qms.document.acknowledgment", "revision_id", string="Acknowledgments")
    required_acknowledgment_count = fields.Integer(compute="_compute_acknowledgment_counts")
    completed_acknowledgment_count = fields.Integer(compute="_compute_acknowledgment_counts")
    pending_acknowledgment_count = fields.Integer(compute="_compute_acknowledgment_counts")
    overdue_acknowledgment_count = fields.Integer(compute="_compute_acknowledgment_counts")

    def _compute_acknowledgment_counts(self):
        for revision in self:
            acknowledgments = revision.acknowledgment_ids
            revision.required_acknowledgment_count = len(acknowledgments)
            revision.completed_acknowledgment_count = len(
                acknowledgments.filtered(lambda item: item.state == "acknowledged")
            )
            revision.pending_acknowledgment_count = len(acknowledgments.filtered(lambda item: item.state == "pending"))
            revision.overdue_acknowledgment_count = len(acknowledgments.filtered("is_overdue"))

    def action_activate(self):
        result = super().action_activate()
        self.env["pm.qms.document.acknowledgment"].sync_for_revisions(self.filtered(lambda item: item.state == "active"))
        return result
