from odoo import api, fields, models
from odoo.exceptions import AccessError


class ResUsersLicense(models.Model):
    _inherit = "res.users"

    pmqms_license_account_type = fields.Selection(
        [("customer", "Customer Named User"), ("technical", "Technical / Service Account"), ("support", "Perfect Match Support")],
        string="Commercial Account Type",
        default="customer",
        required=True,
        copy=False,
        help="Only customer named users consume a commercial QMS seat unless explicitly exempted by authorized technical administration.",
    )
    pmqms_license_exempt = fields.Boolean(string="License Exempt", copy=False)
    pmqms_license_exemption_reason = fields.Text(string="License Exemption Reason", copy=False)

    def _check_license_admin_change(self, vals):
        if not {"pmqms_license_account_type", "pmqms_license_exempt", "pmqms_license_exemption_reason"}.intersection(vals):
            return
        if self.env.is_superuser() or self.env.user.has_group("pm_qms_license.group_pm_qms_license_admin"):
            return
        raise AccessError("Only authorized technical QMS administration can change commercial account exemptions.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._check_license_admin_change(vals)
        users = super().create(vals_list)
        self.env["pm.qms.entitlement.service"].enforce_named_users(users)
        return users

    def write(self, vals):
        self._check_license_admin_change(vals)
        result = super().write(vals)
        if {"active", "share", "group_ids", "company_id", "company_ids", "pmqms_license_account_type", "pmqms_license_exempt"}.intersection(vals):
            self.env["pm.qms.entitlement.service"].enforce_named_users(self)
        return result
