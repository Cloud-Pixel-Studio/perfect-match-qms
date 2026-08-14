from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsControlInstance(models.Model):
    _name = "pm.qms.control.instance"
    _description = "Perfect Match QMS Control Instance"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "organization_id, code, id"
    _rec_name = "code"

    name = fields.Char(string="Implementation Title", required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    control_id = fields.Many2one("pm.qms.control", required=True, ondelete="restrict", index=True, tracking=True)
    organization_id = fields.Many2one(
        "pm.qms.organization",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True, tracking=True)
    owner_id = fields.Many2one("res.users", string="Implementation Owner", tracking=True)
    implementation_status = fields.Selection(
        [
            ("not_started", "Not Started"),
            ("in_progress", "In Progress"),
            ("evidence_required", "Evidence Required"),
            ("under_review", "Under Review"),
            ("implemented", "Implemented"),
            ("not_applicable", "Not Applicable"),
        ],
        default="not_started",
        required=True,
        tracking=True,
    )
    applicability = fields.Selection(
        [
            ("applicable", "Applicable"),
            ("conditional", "Conditional"),
            ("not_applicable", "Not Applicable"),
        ],
        default="applicable",
        required=True,
        tracking=True,
    )
    justification = fields.Text()
    target_date = fields.Date()
    implementation_date = fields.Date()
    review_date = fields.Date()
    notes = fields.Text()
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Control instance code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.control.instance") or "PM-QMS-INS-00000"
            if not vals.get("name") and vals.get("control_id"):
                control = self.env["pm.qms.control"].browse(vals["control_id"])
                vals["name"] = control.name
        return super().create(vals_list)

    @api.constrains("control_id", "organization_id", "process_id")
    def _check_company_alignment(self):
        for record in self:
            company = record.organization_id.company_id
            if record.process_id.company_id != company:
                raise ValidationError("Control instance process must belong to the same company as the organization.")
            if record.control_id.company_id and record.control_id.company_id != company:
                raise ValidationError("Control instance framework control must belong to the same company.")

    @api.constrains("process_id", "organization_id")
    def _check_process_organization_alignment(self):
        for record in self:
            if record.process_id.organization_id and record.process_id.organization_id != record.organization_id:
                raise ValidationError("Control instance process must belong to the selected organization.")

    def action_mark_in_progress(self):
        self.write({"implementation_status": "in_progress"})

    def action_request_evidence(self):
        self.write({"implementation_status": "evidence_required"})

    def action_submit_for_review(self):
        self.write({"implementation_status": "under_review"})

    def action_mark_implemented(self):
        self.write({"implementation_status": "implemented", "implementation_date": fields.Date.context_today(self)})

    def action_mark_not_applicable(self):
        self.write({"implementation_status": "not_applicable", "applicability": "not_applicable"})
