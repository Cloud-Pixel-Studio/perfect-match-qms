/** @odoo-module **/

const CUSTOMER_QMS_GROUPS = [
    "pm_qms_core.group_pm_qms_user",
    "pm_qms_core.group_qms_viewer",
];

export function isQmsCustomerShell(hasGroup) {
    return (
        !hasGroup("base.group_system") &&
        CUSTOMER_QMS_GROUPS.some((group) => hasGroup(group))
    );
}
