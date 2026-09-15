from odoo import models
from odoo.exceptions import AccessError
from odoo.http import request


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
        "pm_qms_core.action_pm_qms_control": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_core.action_pm_qms_activity": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_core.action_pm_qms_evidence_requirement": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_implementation.action_pm_qms_framework_pack": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_core.action_pm_qms_external_mapping": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_core.action_pm_qms_event": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_migration.action_pm_qms_document_import_wizard": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
        "pm_qms_migration.action_pm_qms_evidence_import_wizard": (
            "pm_qms_core.group_pm_qms_administrator",
            "base.group_system",
        ),
    }

    def _qms_customer_action_groups_by_id(self):
        """Return only the explicitly customer-approved action definitions."""
        return {
            action.id: groups
            for xmlid, groups in self._QMS_CUSTOMER_ACTION_GROUPS.items()
            if (action := self.env.sudo().ref(xmlid, raise_if_not_found=False))
        }

    def _qms_authorization_env(self):
        """Use the authenticated request user when Odoo loads an action with sudo."""
        try:
            request_env = request.env
        except RuntimeError:
            request_env = None
        if request_env and request_env.cr.dbname == self.env.cr.dbname and self.env.is_superuser():
            return request_env
        return self.env

    def _qms_can_read_customer_action(self, groups):
        # Keep metadata inspection available to Odoo's internal superuser used
        # by framework setup/tests; normal users still require the explicit map.
        authorization_env = self._qms_authorization_env()
        return authorization_env.is_superuser() or any(
            authorization_env.user.has_group(group) for group in groups
        )

    def _qms_check_customer_action_access(self):
        action_groups = self._qms_customer_action_groups_by_id()
        for action_id in self.ids:
            if action_id in action_groups and not self._qms_can_read_customer_action(
                action_groups[action_id]
            ):
                raise AccessError("This QMS action is restricted to its configured role allow-list.")

    def _get_action_dict(self):
        # The Odoo web controller calls this method on a sudoed recordset. Check
        # the original authenticated request before the native metadata read.
        self._qms_check_customer_action_access()
        return super()._get_action_dict()

    def read(self, fields=None, load="_classic_read"):
        self._qms_check_customer_action_access()

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
