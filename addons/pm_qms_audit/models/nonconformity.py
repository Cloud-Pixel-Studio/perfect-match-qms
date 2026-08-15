from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsNonconformity(models.Model):
    _inherit = "pm.qms.nonconformity"

    source_audit_id = fields.Many2one("pm.qms.audit", string="Source Audit", ondelete="restrict", index=True)
    source_audit_finding_id = fields.Many2one(
        "pm.qms.audit.finding",
        string="Source Finding",
        ondelete="restrict",
        index=True,
    )
    source_audit_evidence_ids = fields.Many2many(
        "pm.qms.audit.evidence",
        "pm_qms_ncr_audit_evidence_rel",
        "nonconformity_id",
        "audit_evidence_id",
        string="Source Audit Evidence",
    )

    @api.constrains("source_audit_id", "source_audit_finding_id", "source_audit_evidence_ids")
    def _check_audit_source_alignment(self):
        for ncr in self:
            if ncr.source_audit_id and (
                ncr.source_audit_id.company_id != ncr.company_id
                or ncr.source_audit_id.organization_id != ncr.organization_id
            ):
                raise ValidationError("Source audit must match the NCR company and organization.")
            if ncr.source_audit_finding_id:
                finding = ncr.source_audit_finding_id
                if finding.company_id != ncr.company_id or finding.organization_id != ncr.organization_id:
                    raise ValidationError("Source audit finding must match the NCR company and organization.")
                if ncr.source_audit_id and finding.audit_id != ncr.source_audit_id:
                    raise ValidationError("Source finding must belong to the source audit.")
            for evidence in ncr.source_audit_evidence_ids:
                if evidence.company_id != ncr.company_id or evidence.organization_id != ncr.organization_id:
                    raise ValidationError("Source audit evidence must match the NCR company and organization.")
                if ncr.source_audit_id and evidence.audit_id != ncr.source_audit_id:
                    raise ValidationError("Source audit evidence must belong to the source audit.")
