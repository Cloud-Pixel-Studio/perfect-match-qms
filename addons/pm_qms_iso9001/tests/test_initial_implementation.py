import json
from pathlib import Path

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    INITIAL_PACK_CODE,
    INITIAL_PACK_VERSION,
    PROFILE_CODE,
    PROFILE_EDITION,
    post_init_hook,
    seed_iso9001_initial_implementation,
)


@tagged("-at_install", "post_install")
class TestPmQmsIso9001InitialImplementation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.generic_pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", "PM-QMS-QUALITY"),
                ("version", "=", "1.0"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.initial_pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", INITIAL_PACK_CODE),
                ("version", "=", INITIAL_PACK_VERSION),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.blueprint_path = Path(__file__).parents[1] / "content" / "initial_implementation_v1.json"

    def test_initial_pack_identity_and_state(self):
        packs = self.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", INITIAL_PACK_CODE),
                ("version", "=", INITIAL_PACK_VERSION),
                ("company_id", "=", self.company.id),
            ]
        )
        self.assertEqual(len(packs), 1)
        pack = packs[0]
        self.assertEqual(pack.name, "ISO 9001 Initial Implementation")
        self.assertEqual(pack.pack_type, "standard")
        self.assertEqual(pack.state, "active")

    def test_initial_pack_has_thirteen_unique_phases(self):
        areas = self.initial_pack.area_ids.sorted("sequence")
        self.assertEqual(len(areas), 13)
        self.assertEqual(areas.mapped("code"), [f"P{i:02d}" for i in range(1, 14)])
        self.assertEqual(areas.mapped("sequence"), [i * 10 for i in range(1, 14)])
        self.assertEqual(len(set(areas.mapped("code"))), 13)

    def test_pack_controls_are_unique_and_reuse_generic_controls(self):
        lines = self.initial_pack.control_line_ids.filtered("active")
        control_ids = lines.mapped("control_id").ids
        self.assertEqual(len(lines), len(set(control_ids)))
        self.assertTrue(lines)
        for line in lines:
            self.assertIn(line.control_id, self.generic_pack.control_line_ids.mapped("control_id"))
            self.assertEqual(len(line.area_id), 1)

    def test_loader_is_idempotent_and_mapping_profile_is_unchanged(self):
        before = self.env["pm.qms.mapping.profile"].search(
            [
                ("code", "=", PROFILE_CODE),
                ("edition", "=", PROFILE_EDITION),
                ("company_id", "=", self.company.id),
            ],
            limit=1,
        )
        generic_pack_id = before.pack_id.id
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_initial_implementation(self.env)
        self.assertEqual(
            self.env["pm.qms.framework.pack"].search_count(
                [("code", "=", INITIAL_PACK_CODE), ("version", "=", INITIAL_PACK_VERSION), ("company_id", "=", self.company.id)]
            ),
            1,
        )
        pack = self.env["pm.qms.framework.pack"].search(
            [("code", "=", INITIAL_PACK_CODE), ("version", "=", INITIAL_PACK_VERSION), ("company_id", "=", self.company.id)],
            limit=1,
        )
        self.assertEqual(pack.area_count, 13)
        self.assertEqual(len(pack.control_line_ids.mapped("control_id")), len(set(pack.control_line_ids.mapped("control_id").ids)))
        self.assertEqual(before.pack_id.id, generic_pack_id)

    def test_blueprint_has_valid_phases_controls_and_unique_keys(self):
        blueprint = json.loads(self.blueprint_path.read_text())
        self.assertEqual(blueprint["pack"]["code"], INITIAL_PACK_CODE)
        self.assertEqual(blueprint["pack"]["version"], INITIAL_PACK_VERSION)
        self.assertEqual(len(blueprint["phases"]), 13)
        activities = blueprint["activities"]
        self.assertEqual(len(activities), 37)
        self.assertEqual(len({item["activity_key"] for item in activities}), len(activities))
        self.assertEqual(len({item["control_code"] for item in activities}), len(activities))
        phase_codes = {item["code"] for item in blueprint["phases"]}
        pack_controls = set(self.initial_pack.control_line_ids.mapped("control_id.code"))
        for activity in activities:
            self.assertIn(activity["phase_key"], phase_codes)
            self.assertIn(activity["control_code"], pack_controls)
            self.assertEqual(activity["activity_kind"], "qms_implementation")
            self.assertEqual(activity["authoring_status"], "blueprint")

    def test_blueprint_contains_no_source_or_protected_text_markers(self):
        text = self.blueprint_path.read_text().lower()
        for marker in ("raw historical", "chatter", "email", "ai prompt", "customer identifier", "iso 14001", "iso 45001", "as9100", "iatf"):
            self.assertNotIn(marker, text)

    def test_only_iso_9001_content_is_present_in_standard_addon(self):
        manifest_text = (Path(__file__).parents[1] / "__manifest__.py").read_text().lower()
        content_text = self.blueprint_path.read_text().lower()
        for marker in ("iso 14001", "iso 45001", "as9100", "as9120", "iatf", "cmmc"):
            self.assertNotIn(marker, manifest_text + content_text)
        self.assertFalse(
            self.env["pm.qms.mapping.profile"].search(
                [("standard_name", "in", ["ISO 14001", "ISO 45001", "AS9100", "AS9120", "IATF"])]
            )
        )

    def test_generic_dependency_direction_is_downward_only(self):
        implementation = (Path(__file__).parents[2] / "pm_qms_implementation" / "__manifest__.py").read_text()
        core = (Path(__file__).parents[2] / "pm_qms_core" / "__manifest__.py").read_text()
        iso = (Path(__file__).parents[1] / "__manifest__.py").read_text()
        self.assertNotIn("pm_qms_iso9001", implementation)
        self.assertNotIn("pm_qms_iso9001", core)
        self.assertIn("pm_qms_pack_quality", iso)

    def test_post_init_hook_preserves_existing_profile_and_pack(self):
        profile_before = self.env["pm.qms.mapping.profile"].search(
            [("code", "=", PROFILE_CODE), ("edition", "=", PROFILE_EDITION), ("company_id", "=", self.company.id)],
            limit=1,
        )
        post_init_hook(self.env)
        profile_after = self.env["pm.qms.mapping.profile"].search(
            [("code", "=", PROFILE_CODE), ("edition", "=", PROFILE_EDITION), ("company_id", "=", self.company.id)],
            limit=1,
        )
        self.assertEqual(profile_after.id, profile_before.id)
        self.assertEqual(profile_after.pack_id, self.generic_pack)
