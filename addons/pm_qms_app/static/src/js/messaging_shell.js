/** @odoo-module **/

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { DiscussSearch } from "@mail/core/public_web/discuss_search";
import { onWillStart, useEffect, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

import { resolveQmsCustomerShell } from "./customer_shell";

const CUSTOMER_HIDDEN_TABS = new Set(["chat", "channel"]);

patch(MessagingMenu.prototype, {
    setup() {
        super.setup();
        this.qmsCustomerShell = useState({ value: false });
        onWillStart(async () => {
            this.qmsCustomerShell.value = await resolveQmsCustomerShell();
            if (this.isQmsCustomerShell && CUSTOMER_HIDDEN_TABS.has(this.store.discuss.activeTab)) {
                this.store.discuss.activeTab = "notification";
            }
        });
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

    get isQmsCustomerShell() {
        return this.qmsCustomerShell?.value || false;
    },

    get _tabs() {
        const tabs = super._tabs;
        if (!this.isQmsCustomerShell) {
            return tabs;
        }
        return tabs.filter((tab) => !CUSTOMER_HIDDEN_TABS.has(tab.id));
    },

    get threads() {
        const threads = super.threads;
        if (!this.isQmsCustomerShell) {
            return threads;
        }
        return threads.filter((thread) => !["chat", "channel"].includes(thread.channel_type));
    },

    onClickNavTab(tabId) {
        const safeTabId =
            this.isQmsCustomerShell && CUSTOMER_HIDDEN_TABS.has(tabId)
                ? "notification"
                : tabId;
        return super.onClickNavTab(safeTabId);
    },

});

patch(DiscussSearch.prototype, {
    setup() {
        super.setup();
        this.qmsCustomerShell = false;
        onWillStart(async () => {
            this.qmsCustomerShell = await resolveQmsCustomerShell();
        });
    },
});
