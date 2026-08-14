from odoo import fields, models


class PmQmsEvidenceRequirement(models.Model):
    _name = "pm.qms.evidence.requirement"
    _description = "Perfect Match QMS Evidence Requirement"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    description = fields.Text()
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
    mandatory = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
