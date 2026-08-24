from odoo import models
from odoo.exceptions import AccessError


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    def read(self, fields=None, load="_classic_read"):
        users_access_action = self.env.ref(
            "pm_qms_app.action_pm_qms_users_access", raise_if_not_found=False
        )
        if (
            users_access_action
            and users_access_action.id in self.ids
            and not (
                self.env.user.has_group("pm_qms_core.group_qms_quality_manager")
                or self.env.user.has_group("pm_qms_core.group_pm_qms_administrator")
                or self.env.user.has_group("base.group_system")
            )
        ):
            raise AccessError("Users & Access is restricted to QMS administrators.")
        return super().read(fields=fields, load=load)
