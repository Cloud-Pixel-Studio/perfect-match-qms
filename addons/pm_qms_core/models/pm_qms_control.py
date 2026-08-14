from odoo import api, fields, models


class PmQmsControl(models.Model):
    _name = "pm.qms.control"
    _description = "Perfect Match QMS Control"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "code, name"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, readonly=True, tracking=True)
    objective = fields.Text(required=True, tracking=True)
    process_id = fields.Many2one("pm.qms.process", required=True, index=True, tracking=True)
    owner_id = fields.Many2one("res.users", string="Control Owner", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="process_id.company_id",
        store=True,
        readonly=True,
        index=True,
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
        "pm.qms.implementation.activity",
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
    external_mapping_count = fields.Integer(compute="_compute_external_mapping_count")
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Control code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code", "New") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.control") or "PM-QMS-CTRL"
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


class PmQmsImplementationActivity(models.Model):
    _name = "pm.qms.implementation.activity"
    _description = "Perfect Match QMS Implementation Activity"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    name = fields.Char(required=True)
    description = fields.Text()
    responsible_id = fields.Many2one("res.users", string="Responsible")


class PmQmsEvidenceRequirement(models.Model):
    _name = "pm.qms.evidence.requirement"
    _description = "Perfect Match QMS Evidence Requirement"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    name = fields.Char(required=True)
    description = fields.Text()
    evidence_type = fields.Selection(
        [
            ("document", "Document"),
            ("record", "Record"),
            ("approval", "Approval"),
            ("system_data", "System Data"),
            ("other", "Other"),
        ],
        default="record",
        required=True,
    )
    required = fields.Boolean(default=True)


class PmQmsExternalMapping(models.Model):
    _name = "pm.qms.external.mapping"
    _description = "Perfect Match QMS External Reference Mapping"
    _order = "framework, reference"

    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="control_id.company_id", store=True, readonly=True)
    framework = fields.Selection(
        [
            ("iso9001", "ISO 9001"),
            ("iatf16949", "IATF 16949"),
            ("iso14001", "ISO 14001"),
            ("iso45001", "ISO 45001"),
            ("as9120", "AS9120"),
            ("cmmc_l1", "CMMC Level 1"),
            ("cmmc_l2", "CMMC Level 2"),
            ("other", "Other"),
        ],
        required=True,
    )
    reference = fields.Char(
        required=True,
        help="Reference identifier only. Do not copy copyrighted standard text.",
    )
    notes = fields.Text(
        help="Perfect Match internal notes only. Do not copy copyrighted standard text.",
    )

    _control_framework_ref_uniq = models.Constraint(
        "UNIQUE(control_id, framework, reference)",
        "External mapping references must be unique per control.",
    )
