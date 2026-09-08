from odoo import models
from odoo.api import SUPERUSER_ID
from odoo.exceptions import AccessError


class ResUsersApiKeyRoleGuard(models.Model):
    _inherit = "res.users"

    def write(self, vals):
        role_field = "qms_role_group_ids"
        api_group = self.env.ref(
            "pm_qms_app.group_api_integration_administrator",
            raise_if_not_found=False,
        )
        if api_group and role_field in vals and not self.env.is_system():
            commands = vals[role_field] or []
            touches_api_group = any(
                (command[0] in (3, 4) and command[1] == api_group.id)
                or (command[0] == 6 and api_group.id in command[2])
                or (command[0] == 5 and api_group in self.mapped(role_field))
                for command in commands
            )
            if touches_api_group:
                raise AccessError(
                    "Only a Technical Administrator can assign or remove API Integration Administrator."
                )
        return super().write(vals)


class ResUsersApiKeysDescription(models.TransientModel):
    _inherit = "res.users.apikeys.description"

    def check_access_make_key(self):
        if not (
            self.env.is_system()
            or self.env.user.has_group("pm_qms_app.group_api_integration_administrator")
        ):
            raise AccessError(
                "Only a Technical Administrator or API Integration Administrator can create API keys."
            )
        return super().check_access_make_key()


class ResUsersApiKeys(models.Model):
    _inherit = "res.users.apikeys"

    def _check_credentials(self, *, scope, key):
        user_id = super()._check_credentials(scope=scope, key=key)
        if not user_id:
            return user_id

        owner = self.env["res.users"].browse(user_id)
        if not (
            owner.id == SUPERUSER_ID
            or owner._has_group("base.group_system")
            or owner._has_group("pm_qms_app.group_api_integration_administrator")
        ):
            return None
        return user_id

    def _remove(self):
        if not (
            self.env.is_system()
            or self.env.user.has_group("pm_qms_app.group_api_integration_administrator")
        ):
            raise AccessError(
                "Only a Technical Administrator or API Integration Administrator can revoke API keys."
            )
        return super()._remove()
