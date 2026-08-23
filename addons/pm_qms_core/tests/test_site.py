from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestPmQmsSite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Other Site Company"})
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Site Test Organization", "code": "PM-SITE-ORG", "company_id": cls.company.id}
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Site Organization", "code": "PM-SITE-OTHER", "company_id": cls.other_company.id}
        )

    def _site_values(self, **extra):
        values = {
            "name": "Headquarters",
            "code": "PM-SITE-HQ",
            "organization_id": self.organization.id,
            "site_type": "headquarters",
            "is_primary": True,
        }
        values.update(extra)
        return values

    def test_site_company_scope_and_primary_invariant(self):
        site = self.env["pm.qms.site"].create(self._site_values())
        self.assertEqual(site.company_id, self.company)

        other_partner = self.env["res.partner"].create(
            {"name": "Other Company Address", "company_id": self.other_company.id}
        )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.site"].create(
                self._site_values(code="PM-SITE-WRONG-CONTACT", partner_id=other_partner.id)
            )

        with self.assertRaises(ValidationError):
            self.env["pm.qms.site"].create(self._site_values(code="PM-SITE-SECONDARY", name="Second HQ"))

        site.active = False
        secondary = self.env["pm.qms.site"].create(
            self._site_values(code="PM-SITE-SECONDARY", name="Second HQ")
        )
        self.assertTrue(secondary.is_primary)
        self.assertFalse(site.active)
        self.assertEqual(
            self.env["pm.qms.site"].with_context(active_test=False).search_count(
                [("organization_id", "=", self.organization.id)]
            ),
            2,
        )

    def test_site_code_is_unique_per_organization(self):
        self.env["pm.qms.site"].create(self._site_values(is_primary=False))
        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["pm.qms.site"].create(
                    self._site_values(name="Duplicate Code", is_primary=False)
                )

    def test_archived_site_with_operational_reference_cannot_be_deleted(self):
        site = self.env["pm.qms.site"].create(self._site_values(is_primary=False))
        process = self.env["pm.qms.process"].create(
            {
                "name": "Site Scoped Process",
                "code": "PM-SITE-PROC",
                "organization_id": self.organization.id,
                "company_id": self.company.id,
                "site_ids": [(6, 0, [site.id])],
            }
        )
        self.assertIn(site, process.site_ids)
        site.active = False
        with self.assertRaises(UserError):
            site.unlink()

    def test_site_company_record_rule(self):
        own_site = self.env["pm.qms.site"].create(self._site_values(is_primary=False))
        other_site = self.env["pm.qms.site"].create(
            self._site_values(
                name="Other Company Site",
                code="PM-SITE-OTHER-COMPANY",
                organization_id=self.other_organization.id,
                is_primary=True,
            )
        )
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Site Boundary User",
                "login": "site-boundary-user",
                "email": "site-boundary-user@example.invalid",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "group_ids": [
                    (
                        6,
                        0,
                        [self.env.ref("base.group_user").id, self.env.ref("pm_qms_core.group_pm_qms_user").id],
                    )
                ],
            }
        )
        visible = self.env["pm.qms.site"].with_user(user).search([])
        self.assertIn(own_site, visible)
        self.assertNotIn(other_site, visible)
