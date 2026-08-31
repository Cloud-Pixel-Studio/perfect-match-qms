import json
from pathlib import Path

from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    AMENDMENT_PACK_VERSION,
    AMENDMENT_REVISED_LOGICAL_IDS,
    AMENDMENT_SHARED_KEYS,
    INITIAL_PACK_CODE,
    INITIAL_PACK_VERSION,
    PROFILE_CODE,
    PROFILE_EDITION,
    _initial_authored_content,
    seed_iso9001_initial_implementation,
)


@tagged("-at_install", "post_install")
class TestPmQmsIso9001Amendment1(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.root = Path(__file__).parents[1]
        cls.v1_blueprint = json.loads(
            (cls.root / "content" / "initial_implementation_v1.json").read_text()
        )
        cls.v11_blueprint = json.loads(
            (cls.root / "content" / "initial_implementation_v1_1.json").read_text()
        )
        cls.v11_content = json.loads(
            (cls.root / "content" / "initial_implementation_amendment1_v1_1.json").read_text()
        )
        cls.crosswalk = json.loads(
            (cls.root / "content" / "initial_implementation_evidence_profile_v1_1.json").read_text()
        )
        cls.v1_pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", INITIAL_PACK_CODE),
                ("version", "=", INITIAL_PACK_VERSION),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.v11_pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", INITIAL_PACK_CODE),
                ("version", "=", AMENDMENT_PACK_VERSION),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.v1_by_key = {
            item["activity_key"]: item for item in cls.v1_blueprint["activities"]
        }
        cls.v11_by_key = {
            item["activity_key"]: item for item in cls.v11_blueprint["activities"]
        }
        cls.v11_content_by_key = {
            item["activity_key"]: item for item in cls.v11_content["activities"]
        }

    def test_versioned_packs_have_independent_complete_structure(self):
        self.assertEqual(self.v1_pack.state, "active")
        self.assertEqual(self.v11_pack.state, "active")
        for pack in (self.v1_pack, self.v11_pack):
            self.assertEqual(pack.area_ids.sorted("sequence").mapped("code"), [f"P{i:02d}" for i in range(1, 14)])
            lines = pack.control_line_ids.filtered("active")
            control_ids = lines.mapped("control_id").ids
            self.assertEqual(len(lines), 37)
            self.assertEqual(len(control_ids), len(set(control_ids)))
            self.assertEqual(len(set(lines.mapped("control_id.code"))), 37)
        self.assertEqual(
            set(self.v1_pack.control_line_ids.mapped("control_id.code")),
            set(self.v11_pack.control_line_ids.mapped("control_id.code")),
        )
        self.assertNotEqual(
            set(self.v1_pack.control_line_ids.ids),
            set(self.v11_pack.control_line_ids.ids),
        )

    def test_shared_and_revised_activity_identity_and_pack_scope(self):
        Activity = self.env["pm.qms.activity"]
        all_v1_keys = set(self.v1_by_key)
        all_v11_keys = set(self.v11_by_key)
        self.assertEqual(len(all_v1_keys), 37)
        self.assertEqual(len(all_v11_keys), 37)
        self.assertEqual(len(AMENDMENT_SHARED_KEYS), 30)
        self.assertEqual(len(AMENDMENT_REVISED_LOGICAL_IDS), 7)

        for key in sorted(AMENDMENT_SHARED_KEYS):
            activity = Activity.search(
                [("definition_key", "=", key), ("company_id", "=", self.company.id)]
            )
            self.assertEqual(len(activity), 1, key)
            self.assertEqual(set(activity.applicable_pack_ids.ids), {self.v1_pack.id, self.v11_pack.id})

        for logical_id in AMENDMENT_REVISED_LOGICAL_IDS:
            old_key = f"ISO9001-INITIAL-{logical_id}"
            new_key = f"ISO9001-INITIAL-V11-{logical_id}"
            old = Activity.search(
                [("definition_key", "=", old_key), ("company_id", "=", self.company.id)]
            )
            revised = Activity.search(
                [("definition_key", "=", new_key), ("company_id", "=", self.company.id)]
            )
            self.assertEqual(len(old), 1)
            self.assertEqual(len(revised), 1)
            self.assertEqual(set(old.applicable_pack_ids.ids), {self.v1_pack.id})
            self.assertEqual(set(revised.applicable_pack_ids.ids), {self.v11_pack.id})
            self.assertEqual(old.control_id, revised.control_id)

    def test_v1_authored_content_is_unchanged(self):
        Activity = self.env["pm.qms.activity"]
        authored = _initial_authored_content()
        fields = (
            "name",
            "description",
            "objective",
            "why_it_matters",
            "implementation_steps",
            "expected_output",
            "evidence_expectations",
            "success_criteria",
            "responsible_role",
            "activity_kind",
            "readiness_required",
        )
        for key, content in authored.items():
            activity = Activity.search(
                [("definition_key", "=", key), ("company_id", "=", self.company.id)]
            )
            self.assertEqual(len(activity), 1)
            expected = dict(content)
            expected["name"] = expected.pop("title")
            for field_name in fields:
                self.assertEqual(getattr(activity, field_name), expected[field_name], key)

    def test_v11_content_covers_amendment_concepts_without_other_standards(self):
        required_markers = {
            "A001": ("climate", "relevance", "rationale", "review"),
            "A002": ("climate", "input", "relevance", "rationale", "monitor", "review"),
            "A008": ("context", "interested", "risk", "opportun", "significant qms change", "purpose", "consequence", "resource", "responsib", "follow-up"),
            "A010": ("organizational knowledge", "availability", "retention", "sharing", "transfer", "changing",),
            "A011": ("competence", "organizational knowledge", "distinct", "capability", "retention", "transfer"),
            "A023": ("operational change", "impact", "authorization", "communication", "verification", "follow-up"),
            "A037": ("management review", "significant qms change", "leadership decision", "owner", "resource", "timing", "follow-up"),
        }
        for logical_id, markers in required_markers.items():
            record = self.v11_content_by_key[f"ISO9001-INITIAL-V11-{logical_id}"]
            text = json.dumps(record).lower()
            self.assertTrue(all(marker in text for marker in markers), logical_id)
            self.assertNotIn(" shall ", text)
        content_text = " ".join(
            path.read_text().lower() for path in (self.root / "content").glob("*.json")
        )
        for marker in ("iso 9001:2026", "edition 6", "iso 14001", "iso 45001", "as9100", "as9120", "iatf", "cmmc"):
            self.assertNotIn(marker, content_text)

    def test_profile_identity_and_mapping_crosswalk_are_stable(self):
        profiles = self.env["pm.qms.mapping.profile"].search(
            [
                ("code", "=", PROFILE_CODE),
                ("edition", "=", PROFILE_EDITION),
                ("company_id", "=", self.company.id),
            ]
        )
        self.assertEqual(len(profiles), 1)
        profile = profiles[0]
        self.assertEqual(profile.name, "ISO 9001:2015 + Amendment 1:2024 Mapping")
        self.assertEqual(profile.standard_name, "ISO 9001")
        self.assertEqual(profile.edition, "2015")
        # The crosswalk is authoring metadata for existing generic evidence;
        # it must not materialize external mapping records.
        self.assertFalse(profile.mapping_ids)
        self.assertEqual(len(self.crosswalk["mappings"]), 37)
        self.assertEqual(
            {item["control_code"] for item in self.crosswalk["mappings"]},
            set(self.v1_pack.control_line_ids.mapped("control_id.code")),
        )
        self.assertEqual(
            {item["activity_key"] for item in self.crosswalk["mappings"]},
            {
                (
                    f"ISO9001-INITIAL-V11-{logical_id}"
                    if logical_id in AMENDMENT_REVISED_LOGICAL_IDS
                    else f"ISO9001-INITIAL-{logical_id}"
                )
                for logical_id in [f"A{i:03d}" for i in range(1, 38)]
            },
        )

    def test_evidence_crosswalk_reuses_existing_generic_definitions(self):
        Requirement = self.env["pm.qms.evidence.requirement"]
        mappings = self.crosswalk["mappings"]
        keys = [item["evidence_definition_key"] for item in mappings]
        self.assertEqual(len(keys), 37)
        self.assertEqual(len(set(keys)), 37)
        requirements = Requirement.search(
            [("definition_key", "in", sorted(set(keys))), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(requirements), 37)
        self.assertEqual(set(requirements.mapped("definition_key")), set(keys))

    def test_seed_is_idempotent_and_does_not_create_migration_records(self):
        Pack = self.env["pm.qms.framework.pack"]
        Activity = self.env["pm.qms.activity"]
        Profile = self.env["pm.qms.mapping.profile"]
        before = (
            Pack.search_count([("code", "=", INITIAL_PACK_CODE), ("company_id", "=", self.company.id)]),
            Activity.search_count([("company_id", "=", self.company.id), ("definition_key", "like", "ISO9001-INITIAL-%")]),
            Profile.search_count([("code", "=", PROFILE_CODE), ("company_id", "=", self.company.id)]),
        )
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_initial_implementation(self.env)
        after = (
            Pack.search_count([("code", "=", INITIAL_PACK_CODE), ("company_id", "=", self.company.id)]),
            Activity.search_count([("company_id", "=", self.company.id), ("definition_key", "like", "ISO9001-INITIAL-%")]),
            Profile.search_count([("code", "=", PROFILE_CODE), ("company_id", "=", self.company.id)]),
        )
        self.assertEqual(after, before)
