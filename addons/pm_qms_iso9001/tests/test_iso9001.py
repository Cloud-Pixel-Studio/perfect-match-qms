from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import PROFILE_CODE, PROFILE_EDITION, post_init_hook


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
        cls.admin = cls.env.ref("base.user_admin")
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

    def test_standards_menu_is_iso_only(self):
        menu = self.env.ref("pm_qms_iso9001.menu_pm_qms_standards")
        self.assertEqual(menu.name, "Standards")
        self.assertFalse(self.env["ir.ui.menu"].search([("name", "in", ["ISO 14001", "ISO 45001", "AS9100", "AS9120", "IATF 16949"])]))
