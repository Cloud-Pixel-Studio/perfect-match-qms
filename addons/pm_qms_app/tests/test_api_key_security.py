from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestApiKeySecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.internal_group = cls.env.ref("base.group_user")
        cls.quality_manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")
        cls.integration_group = cls.env.ref("pm_qms_app.group_api_integration_administrator")

        def make_user(login, groups):
            return cls.env["res.users"].sudo().create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": cls.company.id,
                    "company_ids": [Command.set([cls.company.id])],
                    "group_ids": [Command.set([group.id for group in groups])],
                }
            )

        cls.quality_manager = make_user(
            "m314b1-quality-manager",
            [cls.internal_group, cls.quality_manager_group],
        )
        cls.integration_admin = make_user(
            "m314b1-api-admin",
            [cls.internal_group, cls.quality_manager_group, cls.integration_group],
        )

    def _description(self, user, name):
        return self.env["res.users.apikeys.description"].with_user(user).create(
            {"name": name, "duration": "1"}
        )

    def _make_key(self, user, name):
        description = self._description(user, name)
        self.assertIsNone(description.check_access_make_key())
        self.env["res.users.apikeys"].with_user(user)._generate(
            None, description.name, description.expiration_date
        )

    def test_quality_manager_cannot_create_api_key(self):
        description = self._description(self.quality_manager, "M31.4-B1 denied create")
        with self.assertRaisesRegex(AccessError, "API Integration Administrator"):
            description.check_access_make_key()

    def test_quality_manager_cannot_revoke_existing_key(self):
        self._make_key(self.integration_admin, "M31.4-B1 revoke ownership")
        key = self.env["res.users.apikeys"].sudo().search(
            [("user_id", "=", self.integration_admin.id), ("name", "=", "M31.4-B1 revoke ownership")],
            limit=1,
        )
        with self.assertRaisesRegex(AccessError, "API Integration Administrator"):
            key.with_user(self.quality_manager)._remove()

    def test_integration_admin_can_create_and_revoke_own_key(self):
        description = self._description(self.integration_admin, "M31.4-B1 own key")
        self._make_key(self.integration_admin, description.name)
        key = self.env["res.users.apikeys"].sudo().search(
            [("user_id", "=", self.integration_admin.id), ("name", "=", "M31.4-B1 own key")],
            limit=1,
        )
        self.assertTrue(key)
        key.with_user(self.integration_admin)._remove()
        self.assertFalse(key.exists())

    def test_integration_admin_cannot_revoke_another_users_key(self):
        self._make_key(self.integration_admin, "M31.4-B1 owner key")
        key = self.env["res.users.apikeys"].sudo().search(
            [("user_id", "=", self.integration_admin.id), ("name", "=", "M31.4-B1 owner key")],
            limit=1,
        )
        other = self.env["res.users"].sudo().create(
            {
                "name": "M31.4-B1 other user",
                "login": "m314b1-other",
                "email": "m314b1-other@example.invalid",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([self.internal_group.id])],
            }
        )
        with self.assertRaisesRegex(AccessError, "API Integration Administrator"):
            key.with_user(other)._remove()

    def test_integration_admin_does_not_gain_technical_access(self):
        self.assertTrue(self.integration_admin.has_group("pm_qms_app.group_api_integration_administrator"))
        self.assertFalse(self.integration_admin.has_group("base.group_system"))
        self.assertFalse(self.integration_admin.has_group("base.group_erp_manager"))

    def test_quality_manager_cannot_assign_integration_role(self):
        with self.assertRaisesRegex(AccessError, "Technical Administrator"):
            self.env["res.users"].with_user(self.quality_manager).browse(self.quality_manager.id).write(
                {"qms_role_group_ids": [Command.link(self.integration_group.id)]}
            )

    def test_technical_admin_retains_native_api_key_authority(self):
        description = self._description(self.env.user, "M31.4-B1 technical key")
        self._make_key(self.env.user, description.name)
        key = self.env["res.users.apikeys"].sudo().search(
            [("user_id", "=", self.env.user.id), ("name", "=", "M31.4-B1 technical key")],
            limit=1,
        )
        self.assertTrue(key)
        key._remove()
        self.assertFalse(key.exists())

    def test_api_key_preference_views_are_scoped(self):
        for xmlid in (
            "pm_qms_app.view_users_form_api_key_security",
            "pm_qms_app.view_users_form_simple_modif_api_key_security",
        ):
            view = self.env.ref(xmlid)
            self.assertIn("base.group_system", view.arch_db)
            self.assertIn("pm_qms_app.group_api_integration_administrator", view.arch_db)
