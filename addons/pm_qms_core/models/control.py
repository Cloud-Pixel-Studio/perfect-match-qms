from odoo import api, fields, models


class PmQmsControl(models.Model):
    _name = "pm.qms.control"
    _description = "Perfect Match QMS Control"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(string="Title", required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    active = fields.Boolean(default=True)

    objective = fields.Text(required=True, tracking=True)
    description = fields.Text()
    guidance_purpose = fields.Text(
        string="Purpose",
        help="Reusable Perfect Match guidance describing what this control is meant to achieve.",
    )
    guidance_why = fields.Text(
        string="Why This Matters",
        help="Reusable Perfect Match guidance explaining the business reason for the control.",
    )
    implementation_guidance = fields.Text(
        help="Reusable implementation guidance. Keep client-specific notes on control instances.",
    )
    recommended_steps = fields.Text(help="Recommended proprietary implementation steps.")
    recommended_tools = fields.Text(help="Suggested Perfect Match or operational tools to use.")
    evidence_guidance = fields.Text(help="Reusable guidance for acceptable implementation evidence.")
    practical_notes = fields.Text(help="Practical Perfect Match notes for implementers.")

    owner_id = fields.Many2one("res.users", string="Control Owner", tracking=True)
    process_id = fields.Many2one("pm.qms.process", required=True, index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="process_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    category = fields.Selection(
        [
            ("governance", "Governance"),
            ("process", "Process"),
            ("document_control", "Document Control"),
            ("evidence", "Evidence"),
            ("supplier", "Supplier"),
            ("training", "Training"),
            ("performance", "Performance"),
            ("improvement", "Improvement"),
            ("other", "Other"),
        ],
        default="process",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("retired", "Retired"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    implementation_activity_ids = fields.One2many(
        "pm.qms.activity",
        "control_id",
        string="Implementation Activities",
    )
    evidence_requirement_ids = fields.One2many(
        "pm.qms.evidence.requirement",
        "control_id",
        string="Evidence Requirements",
    )
    external_mapping_ids = fields.One2many(
        "pm.qms.external.mapping",
        "control_id",
        string="External Mappings",
    )
    control_instance_ids = fields.One2many(
        "pm.qms.control.instance",
        "control_id",
        string="Client Implementations",
    )
    external_mapping_count = fields.Integer(compute="_compute_external_mapping_count")

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Control code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.control") or "PM-QMS-00000"
        return super().create(vals_list)

    def _compute_external_mapping_count(self):
        for control in self:
            control.external_mapping_count = len(control.external_mapping_ids)

    def action_activate(self):
        self.write({"state": "active"})

    def action_retire(self):
        self.write({"state": "retired"})

    def action_reset_to_draft(self):
        self.write({"state": "draft"})
