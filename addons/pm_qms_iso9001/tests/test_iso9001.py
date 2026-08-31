from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    PROFILE_CODE,
    PROFILE_EDITION,
    PROFILE_NAME,
    PROFILE_NOTES,
    post_init_hook,
)


@tagged("-at_install", "post_install")
class TestPmQmsIso9001(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.pack = cls.env["pm.qms.framework.pack"].search(
            [("code", "=", "PM-QMS-QUALITY"), ("version", "=", "1.0"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.admin = cls.env["res.users"].create(
            {
                "name": "ISO 9001 Test Administrator",
                "login": "iso9001.test.administrator",
                "email": "iso9001.test.administrator@example.invalid",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("pm_qms_core.group_pm_qms_administrator").id,
                        ],
                    )
                ],
            }
        )
        cls.manager = cls.env["res.users"].create(
            {
                "name": "ISO 9001 Test Manager",
                "login": "iso9001.test.manager",
                "email": "iso9001.test.manager@example.invalid",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id, cls.env.ref("pm_qms_core.group_qms_quality_manager").id])],
            }
        )

    def _profile(self):
        return self.env["pm.qms.mapping.profile"].search(
            [("code", "=", PROFILE_CODE), ("edition", "=", PROFILE_EDITION), ("company_id", "=", self.company.id)],
            limit=1,
        )

    def test_profile_is_idempotent_and_has_no_invented_mappings(self):
        post_init_hook(self.env)
        post_init_hook(self.env)
        profiles = self.env["pm.qms.mapping.profile"].search(
            [("code", "=", PROFILE_CODE), ("edition", "=", PROFILE_EDITION), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(profiles), 1)
        profile = profiles[0]
        self.assertEqual(profile.standard_name, "ISO 9001")
        self.assertEqual(profile.publisher, "ISO")
        self.assertEqual(profile.state, "active")
        self.assertEqual(profile.pack_id, self.pack)
        self.assertEqual(profile.mapping_ids.filtered(lambda item: item.review_status == "approved"), self.env["pm.qms.external.mapping"])
        self.assertEqual(len(self.pack.control_line_ids.mapped("control_id")), len(set(self.pack.control_line_ids.mapped("control_id").ids)))

    def test_normal_qms_manager_cannot_configure_profile(self):
        profile = self._profile()
        with self.assertRaises(AccessError):
            profile.with_user(self.manager).write({"name": "Not allowed"})

    def test_normal_module_update_normalizes_existing_profile_metadata(self):
        profile = self._profile()
        before = {
            "id": profile.id,
            "pack_id": profile.pack_id.id,
            "mapping_ids": tuple(profile.mapping_ids.ids),
            "code": profile.code,
            "edition": profile.edition,
            "standard_name": profile.standard_name,
            "publisher": profile.publisher,
        }
        profile.with_context(module=True).write(
            {
                "name": "ISO 9001 Current Published Edition Mapping",
                "notes": "Legacy module-owned profile notes.",
            }
        )

        self.env["pm.qms.framework.pack"].seed_iso9001_initial_implementation()

        profile.invalidate_recordset()
        self.assertEqual(profile.id, before["id"])
        self.assertEqual(profile.name, PROFILE_NAME)
        self.assertEqual(profile.notes, PROFILE_NOTES)
        self.assertEqual(profile.pack_id.id, before["pack_id"])
        self.assertEqual(tuple(profile.mapping_ids.ids), before["mapping_ids"])
        self.assertEqual(profile.code, before["code"])
        self.assertEqual(profile.edition, before["edition"])
        self.assertEqual(profile.standard_name, before["standard_name"])
        self.assertEqual(profile.publisher, before["publisher"])
        self.assertEqual(profile.state, "active")

    def test_standards_menu_is_iso_only(self):
        menu = self.env.ref("pm_qms_iso9001.menu_pm_qms_standards")
        self.assertEqual(menu.name, "Standards")
        self.assertFalse(self.env["ir.ui.menu"].search([("name", "in", ["ISO 14001", "ISO 45001", "AS9100", "AS9120", "IATF 16949"])]))

    def test_iso9001_overview_opens_existing_profile_list(self):
        action = self.env.ref("pm_qms_iso9001.action_pm_qms_iso9001_overview")
        list_view = self.env.ref("pm_qms_iso9001.view_pm_qms_iso9001_profile_list")
        self.assertEqual(action.res_model, "pm.qms.mapping.profile")
        self.assertEqual(action.view_mode, "list,form")
        self.assertEqual(action.view_id, list_view)
        self.assertEqual(action.domain, "[('code', '=', 'PM-QMS-QUALITY-ISO9001'), ('edition', '=', '2015')]")
        self.assertEqual(self._profile().name, "ISO 9001:2015 + Amendment 1:2024 Mapping")

    def test_standards_menu_is_visible_to_qms_personas_and_admin(self):
        menu_id = self.env.ref("pm_qms_iso9001.menu_pm_qms_standards").id
        for user in (self.admin, self.manager):
            self.assertIn(menu_id, self.env["ir.ui.menu"].with_user(user).load_menus(False))
        viewer = self.env["res.users"].create(
            {
                "name": "ISO 9001 Test Viewer",
                "login": "iso9001.test.viewer",
                "email": "iso9001.test.viewer@example.invalid",
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id, self.env.ref("pm_qms_core.group_qms_viewer").id])],
            }
        )
        self.assertIn(menu_id, self.env["ir.ui.menu"].with_user(viewer).load_menus(False))
