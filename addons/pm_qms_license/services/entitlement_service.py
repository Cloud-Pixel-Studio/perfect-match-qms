from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import config


USABLE_STATES = ("valid", "expiring")


class PmQmsEntitlementService(models.AbstractModel):
    _name = "pm.qms.entitlement.service"
    _description = "Perfect Match QMS Commercial Entitlement Service"

    @api.model
    def current_license(self):
        return self.env["pm.qms.license"].sudo().search([("is_current", "=", True)], order="id desc", limit=1)

    @api.model
    def _enforcement_enabled(self):
        return not config["test_enable"] or self.env.context.get("pmqms_enforce_license")

    @api.model
    def _license_or_raise(self):
        license_record = self.current_license()
        if not license_record:
            raise UserError("Commercial license is missing. Generate an activation request and import a signed license.")
        if license_record.state not in USABLE_STATES:
            raise UserError(f"Commercial license is {license_record.state.replace('_', ' ')} and cannot authorize new capacity.")
        return license_record

    @api.model
    def _operational_organizations(self, company):
        return self.env["pm.qms.organization"].sudo().search(
            [("company_id", "=", company.id), ("organization_kind", "=", "operational"), ("active", "=", True)]
        )

    @api.model
    def _active_sites(self, company):
        return self.env["pm.qms.site"].sudo().search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
                ("organization_id.organization_kind", "=", "operational"),
                ("organization_id.active", "=", True),
            ]
        )

    @api.model
    def _named_users(self, company):
        role_groups = self.env["res.users"]._qms_role_groups()
        if not role_groups:
            return self.env["res.users"].sudo().browse()
        return self.env["res.users"].sudo().search(
            [
                ("active", "=", True),
                ("share", "=", False),
                ("company_id", "=", company.id),
                ("pmqms_license_account_type", "=", "customer"),
                ("pmqms_license_exempt", "=", False),
                ("groups_id", "in", role_groups.ids),
            ]
        )

    @api.model
    def usage(self, company=None):
        company = company or self.env.company
        license_record = self.current_license()
        organizations = self._operational_organizations(company)
        sites = self._active_sites(company)
        users = self._named_users(company)
        limits = {
            "company": license_record.company_limit if license_record else 0,
            "site": license_record.site_limit if license_record else 0,
            "named_user": license_record.named_user_limit if license_record else 0,
        }
        return {
            "license": license_record,
            "status": license_record.state if license_record else "missing",
            "company": {"used": len(organizations), "limit": limits["company"], "remaining": max(limits["company"] - len(organizations), 0)},
            "site": {"used": len(sites), "limit": limits["site"], "remaining": max(limits["site"] - len(sites), 0)},
            "named_user": {"used": len(users), "limit": limits["named_user"], "remaining": max(limits["named_user"] - len(users), 0)},
        }

    @api.model
    def enforce_organization(self, organizations):
        if not self._enforcement_enabled() or self.env.context.get("pmqms_license_seed"):
            return
        for organization in organizations:
            if organization.organization_kind != "operational" or not organization.active:
                continue
            usage = self.usage(organization.company_id)
            if usage["company"]["used"] > usage["company"]["limit"]:
                raise UserError(
                    "The commercial license allows "
                    f"{usage['company']['limit']} operational company environment(s); activate another isolated environment instead."
                )

    @api.model
    def enforce_sites(self, sites):
        if not self._enforcement_enabled() or self.env.context.get("pmqms_license_seed"):
            return
        for site in sites:
            if not site.active or site.organization_id.organization_kind != "operational":
                continue
            usage = self.usage(site.company_id)
            if usage["site"]["used"] > usage["site"]["limit"]:
                raise UserError(
                    f"The commercial license allows {usage['site']['limit']} active site(s). Archive a site or import an expanded license."
                )

    @api.model
    def enforce_named_users(self, users):
        if not self._enforcement_enabled() or self.env.context.get("pmqms_license_seed"):
            return
        companies = users.mapped("company_id")
        for company in companies:
            usage = self.usage(company)
            if usage["named_user"]["used"] > usage["named_user"]["limit"]:
                raise UserError(
                    f"The commercial license allows {usage['named_user']['limit']} active named QMS user(s). Import an expanded license before activating another user."
                )

    @api.model
    def check_activation_capacity(self, company):
        license_record = self._license_or_raise()
        usage = self.usage(company)
        return license_record, usage
