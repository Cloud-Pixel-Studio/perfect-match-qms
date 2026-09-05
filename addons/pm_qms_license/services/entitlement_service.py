from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import config


USABLE_STATES = ("valid", "expiring")

QMS_ROLE_XMLIDS = (
    "pm_qms_core.group_qms_quality_manager",
    "pm_qms_core.group_qms_quality_supervisor",
    "pm_qms_core.group_qms_quality_inspector",
    "pm_qms_core.group_qms_document_controller",
    "pm_qms_core.group_qms_internal_auditor",
    "pm_qms_core.group_qms_process_owner",
    "pm_qms_core.group_qms_management_user",
    "pm_qms_core.group_qms_viewer",
)


class PmQmsEntitlementService(models.AbstractModel):
    _name = "pm.qms.entitlement.service"
    _description = "Perfect Match QMS Commercial Entitlement Service"

    @api.model
    def current_license(self):
        return self.env["pm.qms.license"].sudo().search([("is_current", "=", True)], order="id desc", limit=1)

    @api.model
    def _locked_current_license(self):
        """Serialize capacity checks around the current license row.

        The row lock makes concurrent activation attempts re-read usage after
        the transaction that won the lock commits. It does not lock customer
        data globally and is intentionally limited to entitlement checks.
        """
        license_record = self.current_license()
        if license_record:
            self.env.cr.execute(
                "SELECT id FROM pm_qms_license WHERE id = %s FOR UPDATE",
                (license_record.id,),
            )
            license_record.invalidate_recordset()
        return license_record

    @api.model
    def _enforcement_enabled(self):
        if not config["test_enable"]:
            return True
        # Existing regression fixtures predate licensing and have no license.
        # Once a test explicitly installs a license, capacity enforcement must
        # remain active even when an inherited ORM wrapper drops custom context.
        return bool(self.current_license()) or self.env.context.get("pmqms_enforce_license")

    @api.model
    def _license_or_raise(self, license_record=None):
        license_record = license_record or self.current_license()
        if not license_record:
            raise UserError("Commercial license is missing. Generate an activation request and import a signed license.")
        status = license_record.effective_state
        if status not in USABLE_STATES:
            raise UserError(f"Commercial license is {status.replace('_', ' ')} and cannot authorize new capacity.")
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
    def _qms_role_groups(self):
        """Resolve approved QMS roles without depending on the app shell.

        Licensing is loaded before ``pm_qms_app`` in a clean customer database,
        so it cannot call an extension that is registered by that later module.
        Keeping this lookup local also lets the entitlement service remain
        usable by standalone deployment and migration flows.
        """
        groups = self.env["res.groups"].sudo().browse()
        for xmlid in QMS_ROLE_XMLIDS:
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                groups |= group
        return groups

    @api.model
    def _named_users(self, company):
        role_groups = self._qms_role_groups()
        if not role_groups:
            return self.env["res.users"].sudo().browse()
        return self.env["res.users"].sudo().search(
            [
                ("active", "=", True),
                ("share", "=", False),
                ("company_id", "=", company.id),
                ("pmqms_license_account_type", "=", "customer"),
                ("pmqms_license_exempt", "=", False),
                ("group_ids", "in", role_groups.ids),
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
            "status": license_record.effective_state if license_record else "missing",
            "company": {"used": len(organizations), "limit": limits["company"], "remaining": max(limits["company"] - len(organizations), 0)},
            "site": {"used": len(sites), "limit": limits["site"], "remaining": max(limits["site"] - len(sites), 0)},
            "named_user": {"used": len(users), "limit": limits["named_user"], "remaining": max(limits["named_user"] - len(users), 0)},
        }

    @api.model
    def enforce_organization(self, organizations):
        if not self._enforcement_enabled():
            return
        billable = organizations.filtered(
            lambda organization: organization.active and organization.organization_kind == "operational"
        )
        if not billable:
            return
        license_record = self._locked_current_license()
        self._license_or_raise(license_record)
        for company in billable.mapped("company_id"):
            usage = self.usage(company)
            if usage["company"]["used"] > usage["company"]["limit"]:
                raise UserError(
                    "The commercial license allows "
                    f"{usage['company']['limit']} operational company environment(s); activate another isolated environment instead."
                )

    @api.model
    def enforce_sites(self, sites):
        if not self._enforcement_enabled():
            return
        billable = sites.filtered(
            lambda site: (
                site.active
                and site.organization_id.active
                and site.organization_id.organization_kind == "operational"
            )
        )
        if not billable:
            return
        license_record = self._locked_current_license()
        self._license_or_raise(license_record)
        for company in billable.mapped("company_id"):
            usage = self.usage(company)
            if usage["site"]["used"] > usage["site"]["limit"]:
                raise UserError(
                    f"The commercial license allows {usage['site']['limit']} active site(s). Archive a site or import an expanded license."
                )

    @api.model
    def enforce_named_users(self, users):
        if not self._enforcement_enabled():
            return
        role_groups = self._qms_role_groups()
        billable = users.filtered(
            lambda user: (
                user.active
                and not user.share
                and user.pmqms_license_account_type == "customer"
                and not user.pmqms_license_exempt
                and bool(user.group_ids & role_groups)
            )
        )
        if not billable:
            return
        license_record = self._locked_current_license()
        self._license_or_raise(license_record)
        companies = billable.mapped("company_id")
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
