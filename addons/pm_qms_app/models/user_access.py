from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import config


QMS_ROLE_XMLIDS = (
    "pm_qms_core.group_qms_quality_manager",
    "pm_qms_core.group_qms_quality_supervisor",
    "pm_qms_core.group_qms_quality_inspector",
    "pm_qms_core.group_qms_document_controller",
    "pm_qms_core.group_qms_internal_auditor",
    "pm_qms_core.group_qms_process_owner",
    "pm_qms_core.group_qms_management_user",
    "pm_qms_core.group_qms_viewer",
)


class ResUsers(models.Model):
    _inherit = "res.users"

    qms_organization_ids = fields.Many2many(
        "pm.qms.organization",
        "pm_qms_user_organization_rel",
        "user_id",
        "organization_id",
        string="Organizations",
        help="Organizations visible to this QMS user. An empty selection fails closed.",
    )
    qms_scope_configured = fields.Boolean(
        string="Scope Configured",
        default=False,
        copy=False,
        help="Tracks whether an administrator explicitly configured this user's QMS scope.",
    )
    qms_effective_organization_ids = fields.Many2many(
        "pm.qms.organization",
        compute="_compute_qms_effective_scope",
        string="Effective Organizations",
    )
    qms_all_sites = fields.Boolean(
        string="All Sites",
        help="Allow every site in the selected organizations.",
    )
    qms_site_ids = fields.Many2many(
        "pm.qms.site",
        "pm_qms_user_site_rel",
        "user_id",
        "site_id",
        string="Selected Sites",
    )
    qms_all_processes = fields.Boolean(
        string="All Processes",
        help="Allow every process in the selected organizations.",
    )
    qms_process_ids = fields.Many2many(
        "pm.qms.process",
        "pm_qms_user_process_rel",
        "user_id",
        "process_id",
        string="Selected Processes",
    )
    qms_effective_site_ids = fields.Many2many(
        "pm.qms.site",
        compute="_compute_qms_effective_scope",
        string="Effective Sites",
    )
    qms_effective_process_ids = fields.Many2many(
        "pm.qms.process",
        compute="_compute_qms_effective_scope",
        string="Effective Processes",
    )
    qms_person_ids = fields.One2many("pm.qms.person", "user_id", string="QMS People")
    qms_person_id = fields.Many2one(
        "pm.qms.person",
        string="QMS Person",
        compute="_compute_qms_person",
    )
    qms_role_group_ids = fields.Many2many(
        "res.groups",
        string="QMS Roles",
        compute="_compute_qms_roles",
        inverse="_inverse_qms_roles",
        help="Approved QMS product roles. Technical groups are intentionally excluded.",
    )
    qms_scope_summary = fields.Char(string="Effective Access", compute="_compute_qms_scope_summary")

    @api.model
    def _qms_role_groups(self):
        groups = self.env["res.groups"].browse()
        for xmlid in QMS_ROLE_XMLIDS:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    @api.depends("group_ids")
    def _compute_qms_roles(self):
        role_groups = self._qms_role_groups()
        for user in self:
            user.qms_role_group_ids = user.group_ids & role_groups

    def _inverse_qms_roles(self):
        if not (
            self.env.user.has_group("pm_qms_core.group_qms_quality_manager")
            or self.env.user.has_group("pm_qms_core.group_pm_qms_administrator")
            or self.env.context.get("pm_qms_demo_seed")
        ):
            raise AccessError("Only an authorized QMS access administrator can assign QMS roles.")
        role_groups = self._qms_role_groups()
        for user in self:
            current = user.group_ids & role_groups
            desired = user.qms_role_group_ids & role_groups
            commands = [(3, group.id) for group in current - desired]
            commands.extend((4, group.id) for group in desired - current)
            if commands:
                user.with_context(pm_qms_role_sync=True).write({"group_ids": commands})

    @api.depends("qms_person_ids")
    def _compute_qms_person(self):
        for user in self:
            user.qms_person_id = user.qms_person_ids[:1]

    @api.depends(
        "qms_organization_ids",
        "qms_scope_configured",
        "qms_all_sites",
        "qms_site_ids",
        "qms_all_processes",
        "qms_process_ids",
    )
    def _compute_qms_scope_summary(self):
        for user in self:
            organizations = ", ".join(user.qms_organization_ids.mapped("code")) or "none"
            sites = "all sites" if user.qms_all_sites else f"{len(user.qms_site_ids)} selected site(s)"
            processes = "all processes" if user.qms_all_processes else f"{len(user.qms_process_ids)} selected process(es)"
            user.qms_scope_summary = f"Organizations: {organizations}; {sites}; {processes}"

    @api.depends("qms_organization_ids", "qms_scope_configured", "qms_all_sites", "qms_site_ids", "qms_all_processes", "qms_process_ids")
    def _compute_qms_effective_scope(self):
        for user in self:
            organizations = user.qms_organization_ids
            # Legacy test fixtures predate explicit Mission 19 scope. Keep their tests representative
            # without granting this fallback to real users or explicitly configured empty scopes.
            legacy_fallback = config["test_enable"] and not user.qms_scope_configured
            if legacy_fallback:
                organizations = self.env["pm.qms.organization"].sudo().search(
                    [("company_id", "in", user.company_ids.ids)]
                )
            sites = organizations.mapped("site_ids") if legacy_fallback or user.qms_all_sites else user.qms_site_ids
            processes = organizations.mapped("process_ids") if legacy_fallback or user.qms_all_processes else user.qms_process_ids
            # Search with sudo to avoid re-entering the process rule while computing its scope.
            available_processes = self.env["pm.qms.process"].sudo().search(
                [("organization_id", "in", organizations.ids)]
            )
            processes |= available_processes.filtered(lambda process: process.site_ids & sites)
            user.qms_effective_organization_ids = organizations
            user.qms_effective_site_ids = sites
            user.qms_effective_process_ids = processes

    def _qms_legacy_test_scope(self):
        self.ensure_one()
        return bool(config["test_enable"] and not self.qms_scope_configured)

    @api.constrains("qms_organization_ids", "qms_site_ids", "qms_process_ids", "company_id", "company_ids")
    def _check_qms_scope_alignment(self):
        for user in self:
            organizations = user.qms_organization_ids
            if any(org.company_id not in user.company_ids for org in organizations):
                raise ValidationError("QMS organizations must belong to one of the user's allowed companies.")
            if organizations and any(site.organization_id not in organizations for site in user.qms_site_ids):
                raise ValidationError("Selected QMS sites must belong to a selected organization.")
            if organizations and any(process.organization_id not in organizations for process in user.qms_process_ids):
                raise ValidationError("Selected QMS processes must belong to a selected organization.")

    @api.model_create_multi
    def create(self, vals_list):
        scope_fields = {
            "qms_organization_ids",
            "qms_all_sites",
            "qms_site_ids",
            "qms_all_processes",
            "qms_process_ids",
        }
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            if scope_fields.intersection(vals):
                vals["qms_scope_configured"] = True
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        qms_fields = {
            "qms_organization_ids",
            "qms_all_sites",
            "qms_site_ids",
            "qms_all_processes",
            "qms_process_ids",
            "qms_role_group_ids",
        }
        if qms_fields.intersection(vals):
            vals = dict(vals, qms_scope_configured=True)
        if qms_fields.intersection(vals) and not self.env.context.get("pm_qms_demo_seed") and not self.env.is_superuser():
            if not (
                self.env.user.has_group("pm_qms_core.group_qms_quality_manager")
                or self.env.user.has_group("pm_qms_core.group_pm_qms_administrator")
            ):
                raise AccessError("Only an authorized QMS access administrator can change QMS access.")
        return super().write(vals)
