/** @odoo-module **/

import { titleService } from "@web/core/browser/title_service";
import { registry } from "@web/core/registry";

const PRODUCT_NAME = "Perfect Match QMS";
const TECHNICAL_TITLE = /(?:\bOdoo\b|NewId|pm\.qms\.|(?:^|[._])(?:model|xmlid)(?:$|[._]))/i;

function clearTitleParts(service) {
    return Object.fromEntries(
        Object.keys(service.getParts()).map((key) => [key, null]),
    );
}

const productTitleService = {
    ...titleService,
    start(env, services) {
        const service = titleService.start(env, services);
        const setNativeParts = service.setParts;

        return {
            ...service,
            setParts(parts) {
                const value = Object.values(parts)
                    .filter(Boolean)
                    .map(String)
                    .join(" - ")
                    .trim();
                const title = TECHNICAL_TITLE.test(value)
                    ? PRODUCT_NAME
                    : value
                      ? `${value} - ${PRODUCT_NAME}`
                      : PRODUCT_NAME;
                setNativeParts({
                    ...clearTitleParts(service),
                    product: title,
                });
            },
        };
    },
};

registry.category("services").add("title", productTitleService, { force: true });
