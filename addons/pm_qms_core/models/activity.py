from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsActivity(models.Model):
    _name = "pm.qms.activity"
    _description = "Perfect Match QMS Implementation Activity"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    description = fields.Text()
    objective = fields.Text(
        help="The outcome this specific implementation activity should achieve."
    )
    why_it_matters = fields.Text(
        help="Perfect Match-authored explanation of the activity's value."
    )
    implementation_steps = fields.Text(
        help="Practical guidance for completing the activity; not separate tasks."
    )
    success_criteria = fields.Text(
        help="Criteria used to determine whether the activity is complete."
    )
    activity_kind = fields.Selection(
        [
            ("qms_implementation", "QMS Implementation"),
            ("project_administration", "Project Administration"),
            ("readiness_assessment", "Readiness Assessment"),
            ("certification_preparation", "Certification Preparation"),
            ("transition", "Transition"),
            ("gap_remediation", "Gap Remediation"),
            ("other", "Other"),
        ],
        required=True,
        default="qms_implementation",
        help="Generic classification of the implementation activity.",
    )
    readiness_required = fields.Boolean(
        string="Required For Readiness",
        default=True,
        help="Whether a generated task for this activity participates in readiness.",
    )
    responsible_role = fields.Char()
    responsible_user_id = fields.Many2one("res.users", string="Responsible User")
    expected_output = fields.Text()
    evidence_expectations = fields.Text(
        help="Narrative guidance about evidence that would normally demonstrate effective completion; this does not create a formal evidence requirement."
    )
    definition_key = fields.Char(
        index=True,
        copy=False,
        help="Stable identity for a seeded methodology definition; optional for legacy activities."
    )
    active = fields.Boolean(default=True)

    _definition_key_company_uniq = models.Constraint(
        "unique(company_id, definition_key)",
        "A methodology activity definition key must be unique within a company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals) for vals in vals_list]
        for vals in vals_list:
            if vals.get("activity_kind") == "project_administration":
                vals["readiness_required"] = False
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if "definition_key" in vals:
            for activity in self:
                new_key = vals.get("definition_key")
                if activity.definition_key and new_key != activity.definition_key:
                    raise ValidationError(
                        "A seeded methodology activity definition key is immutable."
                    )
        if vals.get("activity_kind") == "project_administration":
            vals["readiness_required"] = False
        if vals.get("readiness_required") is True and not vals.get("activity_kind"):
            administrative = self.filtered(
                lambda activity: activity.activity_kind == "project_administration"
            )
            if administrative:
                super(PmQmsActivity, administrative).write(
                    {**vals, "readiness_required": False}
                )
                remaining = self - administrative
                return super(PmQmsActivity, remaining).write(vals) if remaining else True
        return super().write(vals)
