/** @odoo-module **/
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { PerfectMatchDashboardButtonBox } from "./dashboard_button_box";

class PerfectMatchDashboardController extends FormController {
    static components = {
        ...FormController.components,
        ButtonBox: PerfectMatchDashboardButtonBox,
    };
}

const pmQmsDashboardFormView = {
    ...formView,
    Controller: PerfectMatchDashboardController,
};

registry.category("views").add("pm_qms_dashboard_form", pmQmsDashboardFormView);
