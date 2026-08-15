from odoo import fields, models


class PmQmsProcess(models.Model):
    _inherit = "pm.qms.process"

    audit_ids = fields.Many2many("pm.qms.audit", compute="_compute_audit_relationships", string="Audits")
    audit_finding_ids = fields.One2many("pm.qms.audit.finding", "process_id", string="Audit Findings")
    audit_count = fields.Integer(compute="_compute_audit_relationships")
    audit_finding_count = fields.Integer(compute="_compute_audit_relationships")
    open_audit_finding_count = fields.Integer(compute="_compute_audit_relationships")
    open_ncr_count = fields.Integer(compute="_compute_audit_relationships")

    def _compute_audit_relationships(self):
        Scope = self.env["pm.qms.audit.scope"]
        Ncr = self.env["pm.qms.nonconformity"]
        for process in self:
            audits = Scope.search([("process_id", "=", process.id)]).mapped("audit_id") | process.audit_finding_ids.mapped("audit_id")
            process.audit_ids = audits
            process.audit_count = len(audits)
            process.audit_finding_count = len(process.audit_finding_ids)
            process.open_audit_finding_count = len(
                process.audit_finding_ids.filtered(lambda finding: finding.state not in ("closed", "cancelled"))
            )
            process.open_ncr_count = Ncr.search_count(
                [
                    ("process_id", "=", process.id),
                    ("state", "not in", ("closed", "cancelled")),
                ]
            )
