from odoo import fields, models


class PmQmsControlInstance(models.Model):
    _inherit = "pm.qms.control.instance"

    audit_ids = fields.Many2many(
        "pm.qms.audit",
        compute="_compute_audit_relationships",
        string="Related Audits",
    )
    audit_finding_ids = fields.One2many("pm.qms.audit.finding", "control_instance_id", string="Audit Findings")
    audit_count = fields.Integer(compute="_compute_audit_relationships")
    audit_finding_count = fields.Integer(compute="_compute_audit_relationships")
    open_audit_finding_count = fields.Integer(compute="_compute_audit_relationships")
    latest_audit_date = fields.Date(compute="_compute_audit_relationships")

    def _compute_audit_relationships(self):
        Scope = self.env["pm.qms.audit.scope"]
        for instance in self:
            scope_audits = Scope.search([("control_instance_ids", "in", instance.id)]).mapped("audit_id")
            finding_audits = instance.audit_finding_ids.mapped("audit_id")
            audits = scope_audits | finding_audits
            instance.audit_ids = audits
            instance.audit_count = len(audits)
            instance.audit_finding_count = len(instance.audit_finding_ids)
            instance.open_audit_finding_count = len(
                instance.audit_finding_ids.filtered(lambda finding: finding.state not in ("closed", "cancelled"))
            )
            dates = [audit.actual_end or audit.planned_end for audit in audits if audit.actual_end or audit.planned_end]
            instance.latest_audit_date = max(dates) if dates else False
