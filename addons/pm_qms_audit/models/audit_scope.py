from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PmQmsAuditScope(models.Model):
    _name = "pm.qms.audit.scope"
    _description = "Perfect Match QMS Audit Scope"
    _order = "audit_id, sequence, id"

    audit_id = fields.Many2one("pm.qms.audit", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="audit_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", ondelete="restrict", index=True)
    control_instance_ids = fields.Many2many(
        "pm.qms.control.instance",
        "pm_qms_audit_scope_control_instance_rel",
        "scope_id",
        "control_instance_id",
        string="Control Instances",
    )
    description = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("audit_id") and not vals.get("organization_id"):
                audit = self.env["pm.qms.audit"].browse(vals["audit_id"])
                vals["organization_id"] = audit.organization_id.id
        return super().create(vals_list)

    @api.constrains("audit_id", "organization_id", "process_id", "control_instance_ids")
    def _check_scope_alignment(self):
        for scope in self:
            if scope.organization_id != scope.audit_id.organization_id:
                raise ValidationError("Audit scope organization must match the audit organization.")
            if scope.process_id:
                if scope.process_id.company_id != scope.company_id:
                    raise ValidationError("Audit scope process must belong to the audit company.")
                if scope.process_id.organization_id and scope.process_id.organization_id != scope.organization_id:
                    raise ValidationError("Audit scope process must belong to the selected organization.")
            for instance in scope.control_instance_ids:
                if instance.company_id != scope.company_id or instance.organization_id != scope.organization_id:
                    raise ValidationError("Audit scope control instances must match the audit company and organization.")
                if scope.process_id and instance.process_id != scope.process_id:
                    raise ValidationError("Scoped control instances must belong to the selected scope process.")

    def unlink(self):
        if any(scope.audit_id.state not in ("draft", "planned") for scope in self):
            raise UserError("Audit scope can only be deleted while the audit is draft or planned.")
        return super().unlink()

    def write(self, vals):
        if any(scope.audit_id.state not in ("draft", "planned") for scope in self):
            raise UserError("Audit scope can only be changed while the audit is draft or planned.")
        return super().write(vals)
