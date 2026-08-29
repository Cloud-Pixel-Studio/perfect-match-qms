/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { Message } from "@mail/core/common/message_model";
import { ResPartner } from "@mail/core/common/res_partner_model";
import { fields } from "@mail/core/common/record";
import { patch } from "@web/core/utils/patch";

const CUSTOMER_SHELL_CLASS = "o_pm_qms_customer_shell";
const PM_QMS_MODEL_PREFIX = "pm.qms.";

patch(ResPartner.prototype, {
    pm_qms_system_actor: fields.Attr(false),
});

patch(Message.prototype, {
    get authorName() {
        if (
            this.author_id?.pm_qms_system_actor &&
            this.thread?.model?.startsWith(PM_QMS_MODEL_PREFIX) &&
            document.documentElement.classList.contains(CUSTOMER_SHELL_CLASS)
        ) {
            return "Perfect Match QMS · System";
        }
        return super.authorName;
    },
});

patch(Chatter.prototype, {
    get isQmsCustomerHistory() {
        return (
            document.documentElement.classList.contains(CUSTOMER_SHELL_CLASS) &&
            this.props.threadModel?.startsWith(PM_QMS_MODEL_PREFIX)
        );
    },
});
