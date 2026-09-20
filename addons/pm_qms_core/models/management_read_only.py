from odoo import models
from odoo.exceptions import AccessError


class PmQmsManagementReadOnlyMixin(models.AbstractModel):
    _name = "pm.qms.management.read.only.mixin"
    _description = "Management User read-only security boundary"

    def check_access(self, operation):
        if operation in ("create", "write", "unlink") and self.env.user.has_group(
            "pm_qms_core.group_qms_management_user"
        ):
            raise AccessError("Management User has read-only access to this QMS model.")
        return super().check_access(operation)

    def check_access_rights(self, operation, raise_exception=True):
        if operation in ("create", "write", "unlink") and self.env.user.has_group(
            "pm_qms_core.group_qms_management_user"
        ):
            if raise_exception:
                raise AccessError("Management User has read-only access to this QMS model.")
            return False
        return super().check_access_rights(operation, raise_exception=raise_exception)
