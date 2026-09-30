import json
from pathlib import Path

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    INITIAL_PACK_CODE,
    INITIAL_PACK_VERSION,
    ISO9001_2026_PACK_CODE,
    ISO9001_2026_PACK_VERSION,
    ISO9001_2026_PACK_PROFILE_CODE,
    PROFILE_2026_CODE,
    seed_iso9001_2026_implementation_pack,
)


@tagged("-at_install", "post_install")
class TestPmQmsIso9001ImplementationPack2026(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.pack = cls.env["pm.qms.framework.pack"].search([
            ("code", "=", ISO9001_2026_PACK_CODE),
            ("version", "=", ISO9001_2026_PACK_VERSION),
            ("company_id", "=", cls.company.id),
        ], limit=1)
        cls.profile = cls.env["pm.qms.mapping.profile"].search([
            ("code", "=", ISO9001_2026_PACK_PROFILE_CODE),
            ("edition", "=", "2026"),
            ("company_id", "=", cls.company.id),
        ], limit=1)
        cls.blueprint_path = (
            Path(__file__).parents[1] / "content" / "iso9001_2026_implementation_pack_v1_draft.json"
        )
        cls.blueprint = json.loads(cls.blueprint_path.read_text())

    def test_draft_pack_is_distinct_and_review_gated(self):
        self.assertTrue(self.pack)
        self.assertEqual(self.pack.state, "draft")
        self.assertEqual(self.pack.pack_type, "standard")
        self.assertNotEqual(self.pack.code, INITIAL_PACK_CODE)
        self.assertEqual(len(self.pack.area_ids), 7)
        self.assertEqual(len(self.pack.control_line_ids), 38)
        self.assertEqual(self.profile.pack_id, self.pack)
        self.assertEqual(self.profile.state, "draft")
        with self.assertRaises(UserError):
            self.pack.action_activate()

    def test_every_inventory_reference_maps_once_to_a_pack_control(self):
        inventory = self.blueprint["normative_reference_inventory"]
        mappings = self.profile.mapping_ids
        self.assertEqual(len(inventory), 83)
        self.assertEqual(len(mappings), len(inventory))
        self.assertEqual(set(mappings.mapped("reference")), set(inventory))
        self.assertEqual(len(set(mappings.mapped("reference"))), len(mappings))
        self.assertTrue(all(mapping.review_status == "draft" for mapping in mappings))
        self.assertFalse(mappings.filtered(lambda mapping: mapping.review_status == "approved"))
        controls = set(self.pack.control_line_ids.mapped("control_id").ids)
        self.assertTrue(all(mapping.control_id.id in controls for mapping in mappings))

    def test_controls_have_activities_and_explicit_evidence_requirements(self):
        controls = self.pack.control_line_ids.mapped("control_id")
        self.assertEqual(len(controls), 38)
        self.assertTrue(all(control.state == "draft" for control in controls))
        activities = self.env["pm.qms.activity"].search([
            ("applicable_pack_ids", "in", [self.pack.id]),
            ("company_id", "=", self.company.id),
        ])
        self.assertEqual(len(activities), 38)
        requirements = self.env["pm.qms.evidence.requirement"].search([
            ("control_id", "in", controls.ids),
            ("company_id", "=", self.company.id),
        ])
        expected_count = sum(len(control["evidence_examples"]) for control in self.blueprint["controls"])
        self.assertEqual(len(requirements), expected_count)
        self.assertTrue(all(requirement.mandatory for requirement in requirements))

    def test_catalogue_is_complete_and_has_no_duplicates_or_orphans(self):
        controls = self.blueprint["controls"]
        inventory = self.blueprint["normative_reference_inventory"]
        mapped = [reference for control in controls for reference in control["clause_refs"]]
        self.assertEqual(len(controls), 38)
        self.assertEqual(len(mapped), len(set(mapped)))
        self.assertEqual(set(mapped), set(inventory))
        area_codes = {area["code"] for area in self.blueprint["areas"]}
        self.assertTrue(all(control["area"] in area_codes for control in controls))
        self.assertTrue(all(control["evidence_examples"] for control in controls))
        self.assertTrue(all(control["acceptance_criteria"] for control in controls))

    def test_seed_is_idempotent_and_preserves_historical_packs_and_profiles(self):
        legacy = self.env["pm.qms.framework.pack"].search([
            ("code", "=", INITIAL_PACK_CODE),
            ("version", "=", INITIAL_PACK_VERSION),
            ("company_id", "=", self.company.id),
        ], limit=1)
        generic = self.env["pm.qms.framework.pack"].search([
            ("code", "=", "PM-QMS-QUALITY"),
            ("version", "=", "1.0"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        existing_2026_profile = self.env["pm.qms.mapping.profile"].search([
            ("code", "=", PROFILE_2026_CODE),
            ("edition", "=", "2026"),
            ("company_id", "=", self.company.id),
        ], limit=1)
        snapshot = (legacy.id, legacy.state, len(legacy.control_line_ids), generic.id, generic.state,
                   len(generic.control_line_ids), existing_2026_profile.id, existing_2026_profile.pack_id.id)
        seed_iso9001_2026_implementation_pack(self.env)
        seed_iso9001_2026_implementation_pack(self.env)
        self.assertEqual(self.pack.area_count, 7)
        self.assertEqual(len(self.pack.control_line_ids), 38)
        after = (legacy.id, legacy.state, len(legacy.control_line_ids), generic.id, generic.state,
                 len(generic.control_line_ids), existing_2026_profile.id, existing_2026_profile.pack_id.id)
        self.assertEqual(after, snapshot)
        self.assertEqual(self.env["pm.qms.framework.pack"].search_count([
            ("code", "=", ISO9001_2026_PACK_CODE),
            ("version", "=", ISO9001_2026_PACK_VERSION),
            ("company_id", "=", self.company.id),
        ]), 1)
