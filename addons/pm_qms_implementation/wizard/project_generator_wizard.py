from odoo import fields, models
from odoo.exceptions import UserError, ValidationError


class PmQmsProjectGeneratorWizard(models.TransientModel):
    _name = "pm.qms.project.generator.wizard"
    _description = "Perfect Match QMS Project Generator Wizard"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    organization_id = fields.Many2one("pm.qms.organization", required=True)
    project_manager_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    date_start = fields.Date(required=True, default=fields.Date.context_today)
    target_date = fields.Date(required=True)
    assessment_goal_type = fields.Selection(
        [
            ("internal_readiness", "Internal Readiness"),
            ("certification", "Certification"),
            ("surveillance", "Surveillance"),
            ("customer_audit", "Customer Audit"),
            ("regulatory_assessment", "Regulatory Assessment"),
            ("other", "Other"),
        ],
        default="internal_readiness",
        required=True,
    )
    target_assessment_date = fields.Date()
    implementation_type = fields.Selection(
        [
            ("new_implementation", "New Implementation"),
            ("migration", "Migration"),
            ("optimization", "Optimization"),
            ("gap_assessment", "Gap Assessment"),
            ("upgrade", "Upgrade"),
            ("custom", "Custom"),
        ],
        default="new_implementation",
        required=True,
    )
    pack_ids = fields.Many2many("pm.qms.framework.pack", string="Framework Packs", required=True)
    create_odoo_project = fields.Boolean(default=True)
    notes = fields.Text()

    def action_generate_implementation(self):
        self.ensure_one()
        if self.organization_id.company_id != self.company_id:
            raise ValidationError("Organization must belong to the selected company.")
        if not self.pack_ids:
            raise UserError("Select at least one active framework pack.")
        if any(pack.state != "active" for pack in self.pack_ids):
            raise UserError("Only active framework packs can be deployed.")
        if any(pack.company_id != self.company_id for pack in self.pack_ids):
            raise ValidationError("Framework packs must belong to the selected company.")
        project = self.env["pm.qms.implementation.project"].generate_from_wizard(
            {
                "name": self.name,
                "company_id": self.company_id.id,
                "organization_id": self.organization_id.id,
                "project_manager_id": self.project_manager_id.id,
                "date_start": self.date_start,
                "target_date": self.target_date,
                "assessment_goal_type": self.assessment_goal_type,
                "target_assessment_date": self.target_assessment_date,
                "implementation_type": self.implementation_type,
                "pack_ids": self.pack_ids.ids,
                "create_odoo_project": self.create_odoo_project,
                "notes": self.notes,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Implementation Project",
            "res_model": "pm.qms.implementation.project",
            "view_mode": "form",
            "res_id": project.id,
        }
