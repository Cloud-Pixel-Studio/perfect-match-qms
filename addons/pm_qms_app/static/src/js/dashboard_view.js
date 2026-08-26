/** @odoo-module **/
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";

const pmQmsDashboardFormView = {
    ...formView,
};

registry.category("views").add("pm_qms_dashboard_form", pmQmsDashboardFormView);
