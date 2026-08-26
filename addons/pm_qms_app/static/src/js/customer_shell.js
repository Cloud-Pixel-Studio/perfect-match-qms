/** @odoo-module **/

import { user } from "@web/core/user";

const CUSTOMER_QMS_GROUPS = [
    "pm_qms_core.group_pm_qms_user",
    "pm_qms_core.group_qms_viewer",
];

export async function isQmsCustomerShell(hasGroup) {
    const [isSystem, ...customerGroups] = await Promise.all([
        hasGroup("base.group_system"),
        ...CUSTOMER_QMS_GROUPS.map((group) => hasGroup(group)),
    ]);
    return !isSystem && customerGroups.some(Boolean);
}

let customerShellPromise;

export function resolveQmsCustomerShell() {
    if (!customerShellPromise) {
        customerShellPromise = isQmsCustomerShell((group) => user.hasGroup(group)).then(
            (isCustomerShell) => {
                document.documentElement.classList.toggle(
                    "o_pm_qms_customer_shell",
                    isCustomerShell,
                );
                return isCustomerShell;
            },
        );
    }
    return customerShellPromise;
}
