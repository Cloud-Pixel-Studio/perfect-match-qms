from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PmQmsAuditCriterion(models.Model):
    _name = "pm.qms.audit.criterion"
    _description = "Perfect Match QMS Audit Criterion"
    _order = "audit_id, sequence, id"

    audit_id = fields.Many2one("pm.qms.audit", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="audit_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="audit_id.organization_id", store=True, readonly=True, index=True)
    name = fields.Char(required=True)
    criterion_type = fields.Selection(
        [
            ("perfect_match_control", "Perfect Match Control"),
            ("company_procedure", "Company Procedure"),
            ("customer_requirement", "Customer Requirement"),
            ("regulatory", "Regulatory"),
            ("external_standard_reference", "External Standard Reference"),
            ("other", "Other"),
        ],
        default="perfect_match_control",
        required=True,
    )
    control_id = fields.Many2one("pm.qms.control", ondelete="restrict", index=True)
    control_instance_id = fields.Many2one("pm.qms.control.instance", ondelete="restrict", index=True)
    external_mapping_id = fields.Many2one("pm.qms.external.mapping", ondelete="restrict", index=True)
    reference = fields.Char()
    description = fields.Text()
    active = fields.Boolean(default=True)

    @api.constrains("audit_id", "control_id", "control_instance_id", "external_mapping_id")
    def _check_criterion_alignment(self):
        for criterion in self:
            if criterion.control_id and criterion.control_id.company_id != criterion.company_id:
                raise ValidationError("Audit criterion control must belong to the audit company.")
            if criterion.control_instance_id:
                if criterion.control_instance_id.company_id != criterion.company_id:
                    raise ValidationError("Audit criterion control instance must belong to the audit company.")
                if criterion.control_instance_id.organization_id != criterion.organization_id:
                    raise ValidationError("Audit criterion control instance must belong to the audit organization.")
                if criterion.control_id and criterion.control_instance_id.control_id != criterion.control_id:
                    raise ValidationError("Audit criterion control instance must implement the selected control.")
            if criterion.external_mapping_id:
                mapping = criterion.external_mapping_id
                if mapping.company_id != criterion.company_id:
                    raise ValidationError("Audit criterion external mapping must belong to the audit company.")
                if criterion.control_id and mapping.control_id != criterion.control_id:
                    raise ValidationError("Audit criterion external mapping must reference the selected control.")

    def unlink(self):
        if any(criterion.audit_id.state not in ("draft", "planned") for criterion in self):
            raise UserError("Audit criteria can only be deleted while the audit is draft or planned.")
        return super().unlink()

    def write(self, vals):
        if any(criterion.audit_id.state not in ("draft", "planned") for criterion in self):
            raise UserError("Audit criteria can only be changed while the audit is draft or planned.")
        return super().write(vals)
