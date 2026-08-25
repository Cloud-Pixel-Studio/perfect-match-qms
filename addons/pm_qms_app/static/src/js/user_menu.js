/** @odoo-module **/

import { onWillStart, useState } from "@odoo/owl";

import { ImStatusDropdown } from "@mail/core/common/im_status_dropdown";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { patch } from "@web/core/utils/patch";

import { resolveQmsCustomerShell } from "./customer_shell";

patch(UserMenu.prototype, {
    setup() {
        super.setup();
        this.qmsCustomerShell = useState({ value: false });
        onWillStart(async () => {
            this.qmsCustomerShell.value = await resolveQmsCustomerShell();
        });
    },

    getElements() {
        const elements = super.getElements();
        if (!this.qmsCustomerShell?.value) {
            return elements;
        }
        return elements.filter(
            (element) => element.id !== "account" && element.contentComponent !== ImStatusDropdown
        );
    },
});
