from pathlib import Path

from odoo.tests.common import TransactionCase


class TestProductIdentity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addon_root = Path(__file__).resolve().parents[1]

    def test_customer_identity_sources_are_bounded_and_branded(self):
        manifest = (self.addon_root / "__manifest__.py").read_text(encoding="utf-8")
        templates = (self.addon_root / "views" / "shell_templates.xml").read_text(
            encoding="utf-8"
        )
        identity = (
            self.addon_root / "static" / "src" / "js" / "product_identity.js"
        ).read_text(encoding="utf-8")
        controller = (
            self.addon_root / "controllers" / "webmanifest.py"
        ).read_text(encoding="utf-8")

        self.assertIn("product_identity.js", manifest)
        self.assertIn("Perfect Match QMS", templates)
        self.assertIn("/pm_qms_app/static/description/icon.svg", templates)
        self.assertIn('"name": "Perfect Match QMS"', controller)
        self.assertIn('"short_name": "Perfect Match QMS"', controller)
        self.assertIn("image/svg+xml", controller)
        self.assertIn('registry.category("services").add("title"', identity)
        self.assertIn("TECHNICAL_TITLE", identity)
        self.assertIn("PRODUCT_NAME", identity)
        self.assertNotIn("patch(", identity)

    def test_identity_does_not_change_security_boundaries(self):
        security_files = list((self.addon_root / "security").glob("*"))
        self.assertTrue(security_files)
        identity = (
            self.addon_root / "static" / "src" / "js" / "product_identity.js"
        ).read_text(encoding="utf-8")
        self.assertNotIn("sudo", identity)
