from odoo import models
from odoo.exceptions import AccessError


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    _QMS_CUSTOMER_ACTION_GROUPS = {
        "pm_qms_core.action_pm_qms_organization": (
            "pm_qms_core.group_qms_quality_manager",
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_core.action_pm_qms_process": (
            "pm_qms_core.group_qms_quality_manager",
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_core.action_pm_qms_site": (
            "pm_qms_core.group_qms_quality_manager",
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_app.action_pm_qms_users_access": (
            "pm_qms_core.group_qms_quality_manager",
            "pm_qms_core.group_pm_qms_administrator",
        ),
        "pm_qms_license.action_pm_qms_license": (
            "pm_qms_core.group_qms_quality_manager",
            "pm_qms_license.group_pm_qms_license_admin",
            "base.group_system",
        ),
        "pm_qms_license.action_pm_qms_activation_request": (
            "pm_qms_license.group_pm_qms_license_admin",
        ),
    }

    def _qms_customer_action_groups_by_id(self):
        """Return only the explicitly customer-approved action definitions."""
        return {
            action.id: groups
            for xmlid, groups in self._QMS_CUSTOMER_ACTION_GROUPS.items()
            if (action := self.env.ref(xmlid, raise_if_not_found=False))
        }

    def _qms_can_read_customer_action(self, groups):
        return any(self.env.user.has_group(group) for group in groups)

    def read(self, fields=None, load="_classic_read"):
        action_groups = self._qms_customer_action_groups_by_id()
        users_access_action = self.env.ref(
            "pm_qms_app.action_pm_qms_users_access", raise_if_not_found=False
        )
        if (
            users_access_action
            and users_access_action.id in self.ids
            and not self._qms_can_read_customer_action(
                action_groups.get(users_access_action.id, ())
            )
        ):
            raise AccessError("Users & Access is restricted to QMS administrators.")

        # Odoo's native ir.actions.act_window ACL is restricted to technical
        # administrators. Customer users may read metadata only for the
        # explicit action IDs above; target-model ACLs and record rules remain
        # the independent data boundary. No write/create/unlink capability is
        # delegated here.
        if self.ids and all(
            action_id in action_groups
            and self._qms_can_read_customer_action(action_groups[action_id])
            for action_id in self.ids
        ):
            return super(IrActionsActWindow, self.sudo()).read(fields=fields, load=load)
        return super().read(fields=fields, load=load)
