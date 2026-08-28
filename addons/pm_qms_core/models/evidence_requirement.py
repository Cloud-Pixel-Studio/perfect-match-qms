from odoo import fields, models
from odoo.exceptions import ValidationError


class PmQmsEvidenceRequirement(models.Model):
    _name = "pm.qms.evidence.requirement"
    _description = "Perfect Match QMS Evidence Requirement"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    definition_key = fields.Char(
        index=True,
        copy=False,
        help="Stable identity for a seeded evidence definition; optional for legacy records.",
    )
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    description = fields.Text()
    acceptance_criteria = fields.Text(
        help="Observable conditions a reviewer uses to accept the submitted evidence set."
    )
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

    _definition_key_company_uniq = models.Constraint(
        "unique(company_id, definition_key)",
        "An evidence requirement definition key must be unique within a company.",
    )

    def write(self, vals):
        vals = dict(vals)
        if "definition_key" in vals:
            for requirement in self:
                new_key = vals.get("definition_key")
                if requirement.definition_key and new_key != requirement.definition_key:
                    raise ValidationError(
                        "An evidence requirement definition key is immutable after assignment."
                    )
        return super().write(vals)
