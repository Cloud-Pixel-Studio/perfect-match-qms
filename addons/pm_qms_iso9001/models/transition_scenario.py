from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class PmQmsIso9001TransitionScenario(models.Model):
    _name = "pm.qms.iso9001.transition.scenario"
    _description = "PM-QMS ISO 9001 Implementation and Transition Scenario"
    _order = "sequence, code"

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, index=True, tracking=True)
    scenario_type = fields.Selection(
        [
            ("initial", "New implementation"),
            ("transition", "2015 to 2026 transition"),
            ("legacy", "Legacy or incomplete system migration"),
            ("recertification", "Recertification"),
            ("scope_expansion", "Scope expansion"),
            ("multi_site", "Multi-site rollout"),
            ("integrated", "Integrated management system"),
            ("partial", "Partial implementation"),
        ],
        required=True,
        tracking=True,
    )
    source_edition = fields.Char(tracking=True)
    target_edition = fields.Char(required=True, tracking=True)
    sequence = fields.Integer(default=10, required=True)
    profile_id = fields.Many2one(
        "pm.qms.mapping.profile",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
        tracking=True,
    )
    objective = fields.Text(required=True)
    entry_conditions = fields.Text(required=True)
    required_outputs = fields.Text(required=True)
    migration_policy = fields.Text(required=True)
    state = fields.Selection(
        [
            ("active", "Active"),
            ("retired", "Retired"),
        ],
        default="active",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Transition scenario codes must be unique per company.",
    )

    @api.constrains("profile_id", "company_id", "target_edition")
    def _check_profile_scope(self):
        for record in self:
            if record.profile_id.company_id != record.company_id:
                raise ValidationError("Scenario profile and scenario company must match.")
            if record.profile_id.edition != record.target_edition:
                raise ValidationError("Scenario target edition must match its profile edition.")

    def _check_admin(self):
        if self.env.context.get("module") or self.env.context.get("install_mode"):
            return
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
            raise AccessError("Only QMS Administrators can configure ISO 9001 transition scenarios.")

    def write(self, vals):
        protected = {
            "name",
            "code",
            "scenario_type",
            "source_edition",
            "target_edition",
            "sequence",
            "profile_id",
            "company_id",
            "objective",
            "entry_conditions",
            "required_outputs",
            "migration_policy",
            "state",
        }
        if protected.intersection(vals):
            self._check_admin()
        return super().write(vals)

    def unlink(self):
        self._check_admin()
        if any(record.state != "retired" for record in self):
            raise AccessError("Only retired transition scenarios can be deleted.")
        return super().unlink()
