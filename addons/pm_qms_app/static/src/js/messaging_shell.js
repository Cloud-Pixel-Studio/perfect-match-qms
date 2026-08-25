/** @odoo-module **/

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { useEffect } from "@odoo/owl";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

import { isQmsCustomerShell } from "./customer_shell";

const CUSTOMER_HIDDEN_TABS = new Set(["chat", "channel"]);

function isCustomerShellUser() {
    return isQmsCustomerShell((group) => user.hasGroup(group));
}

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.isQmsCustomerShell = isCustomerShellUser();
        if (this.isQmsCustomerShell && CUSTOMER_HIDDEN_TABS.has(this.store.discuss.activeTab)) {
            this.store.discuss.activeTab = "notification";
        }
        useEffect(
            () => {
                if (
                    this.isQmsCustomerShell &&
                    CUSTOMER_HIDDEN_TABS.has(this.store.discuss.activeTab)
                ) {
                    this.store.discuss.activeTab = "notification";
                }
            },
            () => [this.store.discuss.activeTab, this.isQmsCustomerShell]
        );
    },

    get _tabs() {
        const tabs = super._tabs;
        if (!this.isQmsCustomerShell) {
            return tabs;
        }
        return tabs.filter((tab) => !CUSTOMER_HIDDEN_TABS.has(tab.id));
    },

    onClickNavTab(tabId) {
        const safeTabId =
            this.isQmsCustomerShell && CUSTOMER_HIDDEN_TABS.has(tabId)
                ? "notification"
                : tabId;
        return super.onClickNavTab(safeTabId);
    },

    onClickNewMessage() {
        if (this.isQmsCustomerShell) {
            return;
        }
        return super.onClickNewMessage(...arguments);
    },
});
