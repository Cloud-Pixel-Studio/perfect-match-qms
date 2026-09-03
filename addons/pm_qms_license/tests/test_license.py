import base64
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from ..services.environment import ensure_environment_id, read_environment_id, short_environment_id
from ..services import license_service
from ..services.license_service import issue_license, validate_document


@tagged("-at_install", "post_install")
class TestPmQmsCommercialLicensing(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Mission 20 Customer", "code": "M20-CUSTOMER", "company_id": cls.company.id}
        )
        cls.private_key = Ed25519PrivateKey.generate()
        cls.public_key = cls.private_key.public_key()
        cls.public_key_b64 = base64.b64encode(
            cls.public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode()
        cls.environment_id = "11111111-1111-4111-8111-111111111111"

    def _payload(self, **overrides):
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        payload = {
            "schema_version": 1,
            "license_id": "PMQMS-M20-TEST",
            "license_revision": 1,
            "customer_name": "Mission 20 Customer",
            "edition": "professional",
            "environment_id": self.environment_id,
            "company_limit": 1,
            "site_limit": 3,
            "named_user_limit": 1,
            "issued_at": now,
            "not_before": now,
            "expires_at": None,
            "perpetual": True,
            "key_id": "test-key",
            "metadata": {"test": True},
        }
        payload.update(overrides)
        return payload

    def _document(self, **overrides):
        return self._document_for_key(self.private_key, **overrides)

    def _document_for_key(self, private_key, **overrides):
        with tempfile.TemporaryDirectory() as directory:
            private_path = Path(directory) / "private.pem"
            private_path.write_bytes(
                private_key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption(),
                )
            )
            return issue_license(self._payload(**overrides), private_path, Path(directory) / "license.pmql")

    def _import(self, **overrides):
        document = self._document(**overrides)
        with patch.object(license_service, "load_public_keys", return_value={"test-key": self.public_key_b64}):
            return self.env["pm.qms.license"].import_document(document, expected_environment_id=self.environment_id)

    def _user(self, login, *groups):
        base_user = self.env.ref("base.group_user")
        group_ids = [base_user.id, *(group.id for group in groups)]
        return self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set(sorted(set(group_ids)))],
            }
        )

    def test_environment_identity_is_stable_and_shortened(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "environment_id"
            first = ensure_environment_id(path)
            second = ensure_environment_id(path)
            self.assertEqual(first, second)
            self.assertEqual(read_environment_id(path), first)
            self.assertEqual(short_environment_id(first), first.replace("-", "")[:8].upper())

    def test_valid_signature_and_tamper_rejection(self):
        document = self._document()
        with patch.object(license_service, "load_public_keys", return_value={"test-key": self.public_key_b64}):
            result = validate_document(document, expected_environment_id=self.environment_id)
            self.assertEqual(result["state"], "valid")
            altered = json.loads(json.dumps(document))
            altered["payload"]["site_limit"] = 99
            with self.assertRaises(ValueError):
                validate_document(altered, expected_environment_id=self.environment_id)
            altered_signature = json.loads(json.dumps(document))
            altered_signature["signature"] = base64.b64encode(b"x" * 64).decode()
            with self.assertRaises(ValueError):
                validate_document(altered_signature, expected_environment_id=self.environment_id)

    def test_wrong_environment_unknown_key_and_malformed_license_rejected(self):
        document = self._document()
        with patch.object(license_service, "load_public_keys", return_value={"test-key": self.public_key_b64}):
            with self.assertRaises(ValueError):
                validate_document(document, expected_environment_id="22222222-2222-4222-8222-222222222222")
            unknown = json.loads(json.dumps(document))
            unknown["payload"]["key_id"] = "unknown"
            with self.assertRaises(ValueError):
                validate_document(unknown, expected_environment_id=self.environment_id)
            with self.assertRaises(ValueError):
                validate_document("not json", expected_environment_id=self.environment_id)

    def test_old_and_new_authorities_coexist_during_rotation(self):
        old_private = Ed25519PrivateKey.generate()
        new_private = Ed25519PrivateKey.generate()
        old_public = old_private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        new_public = new_private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        old_document = self._document_for_key(
            old_private, key_id="pmqms-demo-2026", license_id="PMQMS-OLD-AUTHORITY"
        )
        new_document = self._document_for_key(
            new_private, key_id="pmqms-license-2026", license_id="PMQMS-NEW-AUTHORITY"
        )
        with patch.object(
            license_service,
            "load_public_keys",
            return_value={
                "pmqms-demo-2026": base64.b64encode(old_public).decode(),
                "pmqms-license-2026": base64.b64encode(new_public).decode(),
            },
        ):
            old_result = validate_document(old_document, expected_environment_id=self.environment_id)
            new_result = validate_document(new_document, expected_environment_id=self.environment_id)
        self.assertEqual(old_result["state"], "valid")
        self.assertEqual(new_result["state"], "valid")
        self.assertEqual(old_result["public_key_fingerprint"], hashlib.sha256(old_public).hexdigest())
        self.assertEqual(new_result["public_key_fingerprint"], hashlib.sha256(new_public).hexdigest())

    def test_unknown_authority_is_rejected(self):
        document = self._document(key_id="unknown-authority")
        with patch.object(license_service, "load_public_keys", return_value={"test-key": self.public_key_b64}):
            with self.assertRaises(ValueError):
                validate_document(document, expected_environment_id=self.environment_id)

    def test_known_authority_with_wrong_signature_is_rejected(self):
        document = self._document()
        wrong_private = Ed25519PrivateKey.generate()
        wrong_public = wrong_private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        with patch.object(
            license_service,
            "load_public_keys",
            return_value={"test-key": base64.b64encode(wrong_public).decode()},
        ):
            with self.assertRaises(ValueError):
                validate_document(document, expected_environment_id=self.environment_id)

    def test_correct_signature_with_wrong_environment_is_rejected(self):
        document = self._document()
        with patch.object(license_service, "load_public_keys", return_value={"test-key": self.public_key_b64}):
            with self.assertRaises(ValueError):
                validate_document(document, expected_environment_id="22222222-2222-4222-8222-222222222222")

    def test_public_registry_and_issuer_use_active_authority_without_private_material(self):
        registry_path = Path(__file__).resolve().parents[1] / "data" / "public_keys.json"
        registry_text = registry_path.read_text(encoding="utf-8")
        registry = json.loads(registry_text)["keys"]
        self.assertEqual(set(registry), {"pmqms-demo-2026", "pmqms-license-2026"})
        self.assertNotIn("PRIVATE KEY", registry_text)
        for encoded_key in registry.values():
            self.assertEqual(len(base64.b64decode(encoded_key, validate=True)), 32)
        self.assertEqual(license_service.DEFAULT_ISSUANCE_KEY_ID, "pmqms-license-2026")

    def test_revision_replacement_and_older_revision_rejection(self):
        self._import()
        with self.assertRaises(UserError):
            self._import()
        replacement = self._import(license_revision=2, site_limit=4)
        self.assertEqual(replacement.license_revision, 2)
        self.assertFalse(self.env["pm.qms.license"].search([("license_revision", "=", 1), ("is_current", "=", True)]))

    def test_site_capacity_archive_and_reactivation(self):
        self._import()
        Site = self.env["pm.qms.site"].with_context(pm_qms_enforce_license=True)
        sites = Site.create(
            [
                {"name": "M20 HQ", "code": "M20-HQ", "organization_id": self.organization.id, "site_type": "headquarters"},
                {"name": "M20 Plant", "code": "M20-PLANT", "organization_id": self.organization.id, "site_type": "manufacturing"},
                {"name": "M20 Inspection", "code": "M20-INSP", "organization_id": self.organization.id, "site_type": "inspection"},
            ]
        )
        with self.assertRaises(UserError):
            Site.create({"name": "M20 Overflow", "code": "M20-OVER", "organization_id": self.organization.id, "site_type": "office"})
        sites[0].active = False
        extra = Site.create({"name": "M20 Replacement", "code": "M20-REPL", "organization_id": self.organization.id, "site_type": "office"})
        with self.assertRaises(UserError):
            sites[0].active = True
        self.assertTrue(extra.active)

    def test_framework_organization_does_not_consume_company_capacity(self):
        self._import()
        framework = self.env["pm.qms.organization"].with_context(pm_qms_enforce_license=True).create(
            {"name": "M20 Framework", "code": "M20-FRAMEWORK", "company_id": self.company.id, "organization_kind": "framework"}
        )
        self.assertEqual(framework.organization_kind, "framework")
        with self.assertRaises(UserError):
            self.env["pm.qms.organization"].with_context(pm_qms_enforce_license=True).create(
                {"name": "M20 Second Customer", "code": "M20-SECOND", "company_id": self.company.id}
            )

    def test_named_user_is_counted_once_and_exemption_is_protected(self):
        self._import()
        base_group = self.env.ref("base.group_user")
        manager_group = self.env.ref("pm_qms_core.group_qms_quality_manager")
        inspector_group = self.env.ref("pm_qms_core.group_qms_quality_inspector")
        User = self.env["res.users"].with_context(pmqms_enforce_license=True)
        regular = User.create(
            {
                "name": "Mission 20 Regular User",
                "login": "m20.regular",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([base_group.id])],
            }
        )
        user = User.create(
            {
                "name": "Mission 20 Named User",
                "login": "m20.named",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([base_group.id, manager_group.id, inspector_group.id])],
            }
        )
        self.assertEqual(self.env["pm.qms.entitlement.service"].usage(self.company)["named_user"]["used"], 1)
        with self.assertRaises(UserError):
            User.create(
                {
                    "name": "Mission 20 Second User",
                    "login": "m20.second",
                    "company_id": self.company.id,
                    "company_ids": [Command.set([self.company.id])],
                    "group_ids": [Command.set([base_group.id, self.env.ref("pm_qms_core.group_qms_viewer").id])],
                }
            )
        with self.assertRaises(AccessError):
            user.with_user(regular).write({"pmqms_license_exempt": True})

    def test_organization_capacity_counts_active_current_company_only(self):
        self._import()
        Organization = self.env["pm.qms.organization"].with_context(pmqms_enforce_license=True)
        other_company = self.env["res.company"].create({"name": "Mission 27 Other Company"})
        organization_records = self.env["pm.qms.organization"].sudo().with_context(active_test=False)
        before_ids = set(organization_records.search([]).ids)
        service = self.env["pm.qms.entitlement.service"]

        inactive = Organization.create(
            {
                "name": "Mission 27 Inactive Organization",
                "code": "M27-INACTIVE",
                "company_id": self.company.id,
                "active": False,
            }
        )
        other = Organization.create(
            {
                "name": "Mission 27 Other Organization",
                "code": "M27-OTHER",
                "company_id": other_company.id,
            }
        )
        current_usage = service.usage(self.company)
        other_usage = service.usage(other_company)

        self.assertFalse(inactive.active)
        self.assertEqual(current_usage["company"]["used"], 1)
        self.assertEqual(other_usage["company"]["used"], 1)
        self.assertEqual(service.usage(self.company)["company"]["used"], 1)
        self.assertEqual(set(organization_records.search([]).ids), before_ids | {inactive.id, other.id})
        self.assertEqual(set(current_usage["company"]), {"used", "limit", "remaining"})
        self.assertNotIn("records", current_usage["company"])

    def test_invalid_import_does_not_replace_current_license(self):
        current = self._import()
        broken = self._document(license_revision=2)
        broken["signature"] = base64.b64encode(b"bad" * 20).decode()
        with patch.object(license_service, "load_public_keys", return_value={"test-key": self.public_key_b64}):
            with self.assertRaises(UserError):
                self.env["pm.qms.license"].import_document(broken, expected_environment_id=self.environment_id)
        self.assertEqual(self.env["pm.qms.license"].current(), current)

    def test_license_surface_is_reserved_for_quality_manager_and_admin(self):
        quality_manager = self.env.ref("pm_qms_core.group_qms_quality_manager")
        viewer = self.env.ref("pm_qms_core.group_qms_viewer")
        license_menu = self.env.ref("pm_qms_license.menu_pm_qms_license")
        license_action = self.env.ref("pm_qms_license.action_pm_qms_license")
        self.assertIn(quality_manager, license_menu.group_ids)
        self.assertNotIn(viewer, license_menu.group_ids)
        self.assertIn(quality_manager, license_action.group_ids)
        self.assertNotIn(viewer, license_action.group_ids)

    def test_licensing_administrator_is_not_qms_administrator(self):
        licensing_admin = self.env.ref("pm_qms_license.group_pm_qms_license_admin")
        qms_admin = self.env.ref("pm_qms_core.group_pm_qms_administrator")
        license_model = self.env["pm.qms.license"]
        activation_model = self.env["pm.qms.activation.request"]
        framework_model = self.env["pm.qms.framework.pack"]

        self.assertNotIn(qms_admin, licensing_admin.implied_ids)
        licensing_admin_user = self._user("m27-license-admin", licensing_admin)
        self.assertTrue(licensing_admin_user.has_group("pm_qms_license.group_pm_qms_license_admin"))
        self.assertFalse(licensing_admin_user.has_group("pm_qms_core.group_pm_qms_administrator"))
        self.assertTrue(license_model.with_user(licensing_admin_user).check_access_rights("read", raise_exception=False))
        self.assertTrue(activation_model.with_user(licensing_admin_user).check_access_rights("create", raise_exception=False))
        self.assertFalse(framework_model.with_user(licensing_admin_user).check_access_rights("write", raise_exception=False))
        self.assertFalse(self.env["res.users"].with_user(licensing_admin_user).check_access_rights("write", raise_exception=False))

    def test_licensing_administrator_update_removes_only_former_implication(self):
        template = Path(__file__).resolve().parents[1] / "security" / "security.xml"
        content = template.read_text(encoding="utf-8")
        self.assertIn("Command.unlink(ref('pm_qms_core.group_pm_qms_administrator'))", content)
        self.assertNotIn("Command.clear()", content)

    def test_license_form_respects_activation_request_authority(self):
        """Exercise the compiled view metadata and web_read path used by the web client.

        PR #41 checked the postprocessed XML arch, which hid the restricted page,
        but did not check the model field metadata returned by get_views or the
        nested relation read used to render a form. This regression covers both
        layers so a restricted relation cannot leak back into the customer form.
        """
        quality_manager = self.env.ref("pm_qms_core.group_qms_quality_manager")
        licensing_admin = self.env.ref("pm_qms_license.group_pm_qms_license_admin")
        technical_admin = self.env.ref("base.group_system")
        viewer = self.env.ref("pm_qms_core.group_qms_viewer")
        quality_manager_user = self._user("m20-license-quality-manager", quality_manager)
        licensing_admin_user = self._user("m20-license-admin", licensing_admin)
        technical_admin_user = self._user("m20-license-technical-admin", technical_admin)
        viewer_user = self._user("m20-license-viewer", viewer)
        license_record = self._import()
        license_view = self.env.ref("pm_qms_license.view_pm_qms_license_form")

        quality_manager_views = self.env["pm.qms.license"].with_user(quality_manager_user).get_views(
            [(license_view.id, "form")]
        )
        quality_manager_view = self.env["pm.qms.license"].with_user(quality_manager_user).get_view(
            view_id=license_view.id, view_type="form"
        )
        licensing_admin_views = self.env["pm.qms.license"].with_user(licensing_admin_user).get_views(
            [(license_view.id, "form")]
        )
        licensing_admin_view = self.env["pm.qms.license"].with_user(licensing_admin_user).get_view(
            view_id=license_view.id, view_type="form"
        )
        quality_manager_arch = quality_manager_views["views"]["form"]["arch"]
        licensing_admin_arch = licensing_admin_views["views"]["form"]["arch"]
        quality_manager_fields = quality_manager_views["models"]["pm.qms.license"]["fields"]
        licensing_admin_fields = licensing_admin_views["models"]["pm.qms.license"]["fields"]
        quality_manager_view_fields = quality_manager_view["models"]["pm.qms.license"]
        licensing_admin_view_fields = licensing_admin_view["models"]["pm.qms.license"]

        self.assertNotIn("activation_request_ids", quality_manager_arch)
        self.assertNotIn("Activation Requests", quality_manager_arch)
        self.assertNotIn("activation_request_ids", quality_manager_fields)
        self.assertNotIn("activation_request_ids", quality_manager_view_fields)
        self.assertIn("activation_request_ids", licensing_admin_arch)
        self.assertIn("Activation Requests", licensing_admin_arch)
        self.assertIn("activation_request_ids", licensing_admin_fields)
        self.assertIn("activation_request_ids", licensing_admin_view_fields)

        quality_manager_read = license_record.with_user(quality_manager_user).web_read(
            {field_name: {} for field_name in quality_manager_fields}
        )
        self.assertEqual(quality_manager_read[0]["license_id"], license_record.license_id)
        self.assertEqual(quality_manager_read[0]["effective_state"], license_record.effective_state)
        self.assertEqual(quality_manager_read[0]["site_limit"], license_record.site_limit)
        self.assertEqual(quality_manager_read[0]["named_user_limit"], license_record.named_user_limit)

        with self.assertRaises(AccessError):
            license_record.with_user(quality_manager_user).read(["activation_request_ids"])

        activation_request = self.env["pm.qms.activation.request"].with_user(licensing_admin_user).create(
            {"license_id": license_record.id}
        )
        licensing_admin_read = license_record.with_user(licensing_admin_user).web_read(
            {
                "license_id": {},
                "state": {},
                "activation_request_ids": {
                    "fields": {"id": {}, "name": {}, "requested_at": {}, "state": {}},
                },
            }
        )
        self.assertEqual(licensing_admin_read[0]["activation_request_ids"][0]["id"], activation_request.id)
        with self.assertRaises(AccessError):
            license_record.with_user(technical_admin_user).read(["license_id"])
        with self.assertRaises(AccessError):
            license_record.with_user(viewer_user).read(["license_id"])
