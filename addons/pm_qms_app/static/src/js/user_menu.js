/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

import { ImStatusDropdown } from "@mail/core/common/im_status_dropdown";
import { isQmsCustomerShell } from "./customer_shell";

// Keep the technical Odoo account entry for system administrators only.
function odooAccountItem() {
    return {
        type: "item",
        id: "account",
        description: _t("My Odoo.com Account"),
        show: () => user.hasGroup("base.group_system"),
        callback: () => {
            rpc("/web/session/account")
                .then((url) => browser.open(url, "_blank"))
                .catch(() => browser.open("https://accounts.odoo.com/account", "_blank"));
        },
        sequence: 60,
    };
}

registry.category("user_menuitems").add("odoo_account", odooAccountItem, { force: true });

// Keep presence infrastructure active, but remove its generic status selector
// from the customer-facing QMS shell.
function imStatusItem() {
    return {
        type: "component",
        contentComponent: ImStatusDropdown,
        show: () => !isQmsCustomerShell((group) => user.hasGroup(group)),
        sequence: 45,
    };
}

registry.category("user_menuitems").add("im_status", imStatusItem, { force: true });
