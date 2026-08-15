from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PmQmsAuditEvidence(models.Model):
    _name = "pm.qms.audit.evidence"
    _description = "Perfect Match QMS Audit Evidence"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "collected_date desc, id desc"

    name = fields.Char(required=True, tracking=True)
    audit_id = fields.Many2one("pm.qms.audit", required=True, ondelete="restrict", index=True, tracking=True)
    criterion_id = fields.Many2one("pm.qms.audit.criterion", ondelete="restrict", index=True)
    company_id = fields.Many2one(related="audit_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="audit_id.organization_id", store=True, readonly=True, index=True)
    source = fields.Selection(
        [
            ("interview", "Interview"),
            ("document_review", "Document Review"),
            ("record_sample", "Record Sample"),
            ("observation", "Observation"),
            ("system_report", "System Report"),
            ("other", "Other"),
        ],
        default="record_sample",
        required=True,
    )
    description = fields.Text(required=True)
    document_id = fields.Many2one("pm.qms.document", ondelete="restrict", index=True)
    control_instance_id = fields.Many2one("pm.qms.control.instance", ondelete="restrict", index=True)
    collected_by_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    collected_date = fields.Date(default=fields.Date.context_today, required=True)
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "pm_qms_audit_evidence_attachment_rel",
        "audit_evidence_id",
        "attachment_id",
        string="Attachments",
    )
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_qms_attachment_links()
        return records

    @api.constrains("audit_id", "criterion_id", "document_id", "control_instance_id")
    def _check_evidence_alignment(self):
        for evidence in self:
            if evidence.criterion_id and evidence.criterion_id.audit_id != evidence.audit_id:
                raise ValidationError("Audit evidence criterion must belong to the same audit.")
            if evidence.document_id:
                if evidence.document_id.company_id != evidence.company_id:
                    raise ValidationError("Audit evidence document must belong to the audit company.")
                if evidence.document_id.organization_id != evidence.organization_id:
                    raise ValidationError("Audit evidence document must belong to the audit organization.")
            if evidence.control_instance_id:
                if evidence.control_instance_id.company_id != evidence.company_id:
                    raise ValidationError("Audit evidence control instance must belong to the audit company.")
                if evidence.control_instance_id.organization_id != evidence.organization_id:
                    raise ValidationError("Audit evidence control instance must belong to the audit organization.")

    def write(self, vals):
        result = super().write(vals)
        if "attachment_ids" in vals:
            self._sync_qms_attachment_links()
        return result

    def unlink(self):
        if any(evidence.audit_id.state in ("reporting", "completed", "cancelled") for evidence in self):
            raise UserError("Audit evidence cannot be deleted after reporting has started.")
        return super().unlink()
