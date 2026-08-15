from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    pm_implementation_project_id = fields.Many2one(
        "pm.qms.implementation.project",
        string="QMS Implementation Project",
        ondelete="set null",
        copy=False,
        index=True,
    )
