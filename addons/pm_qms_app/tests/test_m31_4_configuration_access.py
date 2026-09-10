from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestM314ConfigurationAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user = cls.env.ref("base.group_user")
        cls.qms_manager = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.qms_admin = cls.env.ref("pm_qms_core.group_pm_qms_administrator")
        cls.quality_manager = cls.env.ref("pm_qms_core.group_qms_quality_manager")
        cls.quality_supervisor = cls.env.ref("pm_qms_core.group_qms_quality_supervisor")
        cls.internal_auditor = cls.env.ref("pm_qms_core.group_qms_internal_auditor")
        cls.process_owner = cls.env.ref("pm_qms_core.group_qms_process_owner")
        cls.viewer_group = cls.env.ref("pm_qms_core.group_qms_viewer")
        cls.integration_admin_group = cls.env.ref(
            "pm_qms_app.group_api_integration_administrator"
        )
        cls.technical_group = cls.env.ref("base.group_system")
        cls.licensing_admin_group = cls.env.ref("pm_qms_license.group_pm_qms_license_admin")
        cls.quality_manager_user = cls._create_user("m314_quality_manager", cls.quality_manager)
        cls.quality_supervisor_user = cls._create_user("m314_quality_supervisor", cls.quality_supervisor)
        cls.internal_auditor_user = cls._create_user("m314_internal_auditor", cls.internal_auditor)
        cls.process_owner_user = cls._create_user("m314_process_owner", cls.process_owner)
        cls.viewer_user = cls._create_user("m314_viewer", cls.viewer_group)
        cls.integration_admin_user = cls._create_user(
            "m314_integration_admin", cls.integration_admin_group
        )
        cls.qms_admin_user = cls._create_user("m314_qms_admin", cls.qms_admin)
        cls.technical_user = cls._create_user("m314_technical_admin", cls.technical_group)
        cls.licensing_admin_user = cls._create_user("m314_licensing_admin", cls.licensing_admin_group)

    @classmethod
    def _create_user(cls, login, group):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": cls.env.company.id,
                "company_ids": [Command.set([cls.env.company.id])],
                "group_ids": [Command.set([cls.base_user.id, group.id])],
            }
        )

    def _visible(self, user, xmlid):
        menu = self.env.ref(xmlid)
        return menu.id in self.env["ir.ui.menu"].with_user(user).load_menus(False)

    def test_quality_manager_configuration_navigation_is_explicitly_allowed(self):
        configuration = self.env.ref("pm_qms_core.menu_pm_qms_configuration")
        customer_groups = {
            self.quality_manager,
            self.qms_admin,
            self.env.ref("pm_qms_license.group_pm_qms_license_admin"),
            self.technical_group,
        }
        self.assertEqual(set(configuration.group_ids.ids), {group.id for group in customer_groups})

        for xmlid in (
            "pm_qms_core.menu_pm_qms_configuration",
            "pm_qms_core.menu_pm_qms_organizations",
            "pm_qms_core.menu_pm_qms_processes",
            "pm_qms_app.menu_pm_qms_sites",
            "pm_qms_app.menu_pm_qms_users_access",
            "pm_qms_license.menu_pm_qms_license",
        ):
            with self.subTest(menu=xmlid):
                self.assertTrue(self._visible(self.quality_manager_user, xmlid))

        self.assertFalse(
            self._visible(self.quality_manager_user, "pm_qms_core.menu_pm_qms_framework")
        )

    def test_other_customer_roles_do_not_receive_configuration_navigation(self):
        for user in (
            self.quality_supervisor_user,
            self.internal_auditor_user,
            self.process_owner_user,
            self.viewer_user,
            self.integration_admin_user,
        ):
            with self.subTest(user=user.login):
                self.assertFalse(
                    self._visible(user, "pm_qms_core.menu_pm_qms_configuration")
                )
                for xmlid in (
                    "pm_qms_core.menu_pm_qms_organizations",
                    "pm_qms_core.menu_pm_qms_processes",
                    "pm_qms_app.menu_pm_qms_sites",
                    "pm_qms_app.menu_pm_qms_users_access",
                    "pm_qms_license.menu_pm_qms_license",
                ):
                    self.assertFalse(self._visible(user, xmlid), xmlid)

    def test_framework_administration_is_outside_quality_manager_surface(self):
        framework = self.env.ref("pm_qms_core.menu_pm_qms_framework")
        self.assertEqual(
            set(framework.group_ids.ids),
            {self.qms_admin.id, self.technical_group.id},
        )
        self.assertFalse(
            self._visible(self.quality_manager_user, "pm_qms_core.menu_pm_qms_framework")
        )
        self.assertTrue(
            self._visible(self.qms_admin_user, "pm_qms_core.menu_pm_qms_framework")
        )
        self.assertTrue(
            self._visible(self.technical_user, "pm_qms_core.menu_pm_qms_framework")
        )

    def test_configuration_actions_have_direct_action_allow_list(self):
        allowed = {self.quality_manager, self.qms_admin, self.technical_group}
        actions = (
            "pm_qms_core.action_pm_qms_organization",
            "pm_qms_core.action_pm_qms_process",
            "pm_qms_core.action_pm_qms_site",
        )
        for xmlid in actions:
            action = self.env.ref(xmlid)
            with self.subTest(action=xmlid):
                self.assertEqual(set(action.group_ids.ids), {group.id for group in allowed})
                self.assertNotIn(self.qms_manager, action.group_ids)
                action_dict = action._get_action_dict()
                self.assertEqual(set(action_dict["group_ids"]), {group.id for group in allowed})
                for user in (
                    self.quality_supervisor_user,
                    self.internal_auditor_user,
                    self.process_owner_user,
                    self.viewer_user,
                    self.integration_admin_user,
                ):
                    self.assertFalse(
                        action.group_ids & user.all_group_ids,
                        f"{user.login} gained direct access to {xmlid}",
                    )
                self.assertTrue(action.group_ids & self.quality_manager_user.all_group_ids)
                self.assertTrue(action.group_ids & self.technical_user.all_group_ids)

        license_action = self.env.ref("pm_qms_license.action_pm_qms_license")
        self.assertIn(self.quality_manager, license_action.group_ids)
        self.assertIn(self.licensing_admin_group, license_action.group_ids)
        self.assertIn(self.technical_group, license_action.group_ids)

        activation_action = self.env.ref("pm_qms_license.action_pm_qms_activation_request")
        activation_menu = self.env.ref("pm_qms_license.menu_pm_qms_activation_requests")
        self.assertEqual(
            set(activation_action.group_ids.ids),
            {self.licensing_admin_group.id},
        )
        self.assertEqual(
            set(activation_action._get_action_dict()["group_ids"]),
            {self.licensing_admin_group.id},
        )
        self.assertEqual(set(activation_menu.group_ids.ids), {self.licensing_admin_group.id})
        self.assertTrue(activation_action.group_ids & self.licensing_admin_user.all_group_ids)
        self.assertFalse(activation_action.group_ids & self.quality_manager_user.all_group_ids)
        self.assertFalse(activation_action.group_ids & self.technical_user.all_group_ids)

    def test_users_access_has_customer_allow_list_and_independent_orm_guard(self):
        action = self.env.ref("pm_qms_app.action_pm_qms_users_access")
        menu = self.env.ref("pm_qms_app.menu_pm_qms_users_access")
        allowed = {self.quality_manager, self.qms_admin}
        self.assertEqual(set(action.group_ids.ids), {group.id for group in allowed})
        self.assertEqual(set(menu.group_ids.ids), {group.id for group in allowed})
        self.assertNotIn(self.qms_manager, action.group_ids)
        self.assertEqual(
            set(action._get_action_dict()["group_ids"]),
            {group.id for group in allowed},
        )

        for user in (self.quality_manager_user, self.qms_admin_user):
            with self.subTest(authorized=user.login):
                self.assertTrue(action.with_user(user).read(["id", "name", "res_model"]))

        for user in (
            self.quality_supervisor_user,
            self.internal_auditor_user,
            self.process_owner_user,
            self.viewer_user,
            self.integration_admin_user,
            self.licensing_admin_user,
        ):
            with self.subTest(unauthorized=user.login):
                self.assertFalse(action.group_ids & user.all_group_ids)
                with self.assertRaises(AccessError):
                    action.with_user(user).read(["id", "name", "res_model"])

        # Technical administrators retain platform administration, but not this
        # customer-facing action contract.
        self.assertFalse(action.group_ids & self.technical_user.all_group_ids)
        self.assertTrue(self.technical_user.has_group("base.group_system"))
        with self.assertRaises(AccessError):
            action.with_user(self.technical_user).read(["id", "name", "res_model"])

    def test_configuration_orm_permissions_remain_separate_from_action_visibility(self):
        for model_name in ("pm.qms.organization", "pm.qms.process", "pm.qms.site"):
            model = self.env[model_name]
            with self.subTest(model=model_name):
                self.assertTrue(
                    model.with_user(self.quality_manager_user).check_access_rights(
                        "read", raise_exception=False
                    )
                )
                self.assertTrue(
                    model.with_user(self.quality_manager_user).check_access_rights(
                        "create", raise_exception=False
                    )
                )
                self.assertTrue(
                    model.with_user(self.quality_manager_user).check_access_rights(
                        "write", raise_exception=False
                    )
                )
                for user in (
                    self.internal_auditor_user,
                    self.process_owner_user,
                    self.viewer_user,
                ):
                    self.assertTrue(
                        model.with_user(user).check_access_rights(
                            "read", raise_exception=False
                        )
                    )
                    self.assertFalse(
                        model.with_user(user).check_access_rights(
                            "create", raise_exception=False
                        )
                    )
                    self.assertFalse(
                        model.with_user(user).check_access_rights(
                            "write", raise_exception=False
                        )
                    )

        self.assertTrue(
            self.env["pm.qms.organization"]
            .with_user(self.quality_supervisor_user)
            .check_access_rights("create", raise_exception=False)
        )
        self.assertTrue(self.quality_supervisor_user.has_group("pm_qms_core.group_qms_quality_supervisor"))
        self.assertFalse(
            self.quality_supervisor_user.has_group("pm_qms_core.group_qms_quality_manager")
        )
        self.assertFalse(
            self.integration_admin_user.has_group("pm_qms_core.group_pm_qms_manager")
        )
