from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PmQmsAuditPlanLine(models.Model):
    _name = "pm.qms.audit.plan.line"
    _description = "Perfect Match QMS Audit Plan Line"
    _order = "audit_id, sequence, planned_datetime, id"

    audit_id = fields.Many2one("pm.qms.audit", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(related="audit_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="audit_id.organization_id", store=True, readonly=True, index=True)
    planned_datetime = fields.Datetime()
    duration = fields.Float(string="Duration Hours")
    process_id = fields.Many2one("pm.qms.process", ondelete="restrict", index=True)
    activity = fields.Char(required=True)
    auditor_id = fields.Many2one("res.users")
    auditee_id = fields.Many2one("res.users")
    notes = fields.Text()

    @api.constrains("duration")
    def _check_duration(self):
        for line in self:
            if line.duration and line.duration < 0:
                raise ValidationError("Audit plan line duration cannot be negative.")

    @api.constrains("process_id")
    def _check_process_alignment(self):
        for line in self:
            if not line.process_id:
                continue
            if line.process_id.company_id != line.company_id:
                raise ValidationError("Audit plan process must belong to the audit company.")
            if line.process_id.organization_id and line.process_id.organization_id != line.organization_id:
                raise ValidationError("Audit plan process must belong to the audit organization.")

    def unlink(self):
        if any(line.audit_id.state not in ("draft", "planned") for line in self):
            raise UserError("Audit plan lines can only be deleted while the audit is draft or planned.")
        return super().unlink()

    def write(self, vals):
        if any(line.audit_id.state not in ("draft", "planned") for line in self):
            raise UserError("Audit plan lines can only be changed while the audit is draft or planned.")
        return super().write(vals)
