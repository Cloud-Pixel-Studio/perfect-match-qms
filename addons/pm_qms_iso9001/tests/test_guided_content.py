import copy
import json
from pathlib import Path

from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    AMENDMENT_PACK_VERSION,
    AMENDMENT_SHARED_KEYS,
    INITIAL_AUTHORED_CONTENT_FILES,
    INITIAL_PACK_CODE,
    INITIAL_PACK_VERSION,
    _combine_authored_content_blocks,
    _initial_authored_content,
    _validate_authored_blueprint_alignment,
    _validate_authored_content_block,
    seed_iso9001_initial_implementation,
)


@tagged("-at_install", "post_install")
class TestPmQmsIso9001GuidedContent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", INITIAL_PACK_CODE),
                ("version", "=", INITIAL_PACK_VERSION),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.amendment_pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", INITIAL_PACK_CODE),
                ("version", "=", AMENDMENT_PACK_VERSION),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.root = Path(__file__).parents[1]
        cls.blueprint = json.loads(
            (cls.root / "content" / "initial_implementation_v1.json").read_text()
        )
        cls.content = json.loads(
            (cls.root / "content" / "initial_implementation_p01_p06_v1.json").read_text()
        )
        cls.m25_5_content = json.loads(
            (cls.root / "content" / "initial_implementation_p07_p08_v1.json").read_text()
        )
        cls.m25_6_content = json.loads(
            (cls.root / "content" / "initial_implementation_p09_p10_v1.json").read_text()
        )
        cls.m25_7_content = json.loads(
            (cls.root / "content" / "initial_implementation_p11_p13_v1.json").read_text()
        )
        cls.blueprint_by_key = {
            item["activity_key"]: item for item in cls.blueprint["activities"]
        }
        cls.content_by_key = {
            item["activity_key"]: item for item in cls.content["activities"]
        }
        cls.target_keys = {f"ISO9001-INITIAL-A{i:03d}" for i in range(1, 11)}
        cls.m25_5_keys = {f"ISO9001-INITIAL-A{i:03d}" for i in range(11, 16)}
        cls.m25_6_keys = {f"ISO9001-INITIAL-A{i:03d}" for i in range(16, 28)}
        cls.m25_7_keys = {f"ISO9001-INITIAL-A{i:03d}" for i in range(28, 38)}
        cls.all_target_keys = (
            cls.target_keys | cls.m25_5_keys | cls.m25_6_keys | cls.m25_7_keys
        )

    def _expected_pack_scope(self, definition_key):
        if definition_key in AMENDMENT_SHARED_KEYS:
            return self.pack | self.amendment_pack
        return self.pack

    def test_blueprint_checkpoint_distribution_is_roadmap_aligned(self):
        counts = {}
        for item in self.blueprint["activities"]:
            checkpoint = item["content_checkpoint"]
            counts[checkpoint] = counts.get(checkpoint, 0) + 1
        self.assertEqual(
            counts,
            {"M25.4": 10, "M25.5": 5, "M25.6": 12, "M25.7": 10},
        )

    def test_exact_m25_4_content_block_matches_blueprint(self):
        self.assertEqual(set(self.content_by_key), self.target_keys)
        self.assertEqual(
            {
                key
                for key, item in self.blueprint_by_key.items()
                if item["content_checkpoint"] == "M25.4"
            },
            self.target_keys,
        )
        required = (
            "title",
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
        for key, item in self.content_by_key.items():
            self.assertEqual(item["content_checkpoint"], "M25.4")
            self.assertTrue(all(item.get(field_name) for field_name in required))
            self.assertEqual(item["activity_kind"], "qms_implementation")
            self.assertTrue(item["readiness_required"])

    def test_authored_registry_is_explicit_ordered_and_combined(self):
        self.assertEqual(
            [(filename, checkpoint) for filename, _schema, checkpoint, _keys in INITIAL_AUTHORED_CONTENT_FILES],
            [
                ("initial_implementation_p01_p06_v1.json", "M25.4"),
                ("initial_implementation_p07_p08_v1.json", "M25.5"),
                ("initial_implementation_p09_p10_v1.json", "M25.6"),
                ("initial_implementation_p11_p13_v1.json", "M25.7"),
            ],
        )
        self.assertEqual(set(_initial_authored_content()), self.all_target_keys)

    def test_m25_5_content_block_matches_blueprint_and_is_complete(self):
        self.assertEqual(
            {item["activity_key"] for item in self.m25_5_content["activities"]},
            self.m25_5_keys,
        )
        required = (
            "activity_key",
            "content_checkpoint",
            "title",
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
        expected = {
            "ISO9001-INITIAL-A011": ("PM-QMP-CMP-001", "P07"),
            "ISO9001-INITIAL-A012": ("PM-QMP-AWR-001", "P07"),
            "ISO9001-INITIAL-A013": ("PM-QMP-COM-001", "P07"),
            "ISO9001-INITIAL-A014": ("PM-QMP-DOC-001", "P08"),
            "ISO9001-INITIAL-A015": ("PM-QMP-REC-001", "P08"),
        }
        for item in self.m25_5_content["activities"]:
            self.assertTrue(all(item.get(field_name) for field_name in required))
            self.assertTrue(
                all(
                    isinstance(item[field_name], str)
                    for field_name in required
                    if field_name != "readiness_required"
                )
            )
            self.assertEqual(item["content_checkpoint"], "M25.5")
            self.assertEqual(item["activity_kind"], "qms_implementation")
            self.assertTrue(item["readiness_required"])
            self.assertEqual(self.blueprint_by_key[item["activity_key"]]["control_code"], expected[item["activity_key"]][0])
            self.assertEqual(self.blueprint_by_key[item["activity_key"]]["phase_key"], expected[item["activity_key"]][1])

    def test_authored_content_validation_rejects_invalid_blocks(self):
        payload = copy.deepcopy(self.m25_5_content)
        cases = (
            {"content_checkpoint": "M25.4"},
            {"pack_code": "PM-QMS-QUALITY"},
            {"schema_version": "wrong"},
            {"pack_version": "2.0"},
        )
        for change in cases:
            with self.assertRaises(UserError):
                _validate_authored_content_block(
                    {**payload, **change},
                    "fixture.json",
                    "m25.5-authored-content-v1",
                    "M25.5",
                    self.m25_5_keys,
                )
        payload["activities"][0]["activity_key"] = "ISO9001-INITIAL-A099"
        with self.assertRaises(UserError):
            _validate_authored_content_block(
                payload,
                "fixture.json",
                "m25.5-authored-content-v1",
                "M25.5",
                self.m25_5_keys,
            )
        payload = copy.deepcopy(self.m25_5_content)
        payload["activities"][0]["implementation_steps"] = ["not text"]
        with self.assertRaises(UserError):
            _validate_authored_content_block(
                payload,
                "fixture.json",
                "m25.5-authored-content-v1",
                "M25.5",
                self.m25_5_keys,
            )

    def test_authored_content_rejects_duplicate_and_unknown_blueprint_keys(self):
        with self.assertRaises(UserError):
            _combine_authored_content_blocks(
                [("one.json", {"DUP": {}}), ("two.json", {"DUP": {}})]
            )
        with self.assertRaises(UserError):
            _validate_authored_blueprint_alignment(
                {"UNKNOWN": {"content_checkpoint": "M25.5"}}, self.blueprint_by_key
            )

    def test_materialized_content_has_stable_identity_and_exact_pack_scope(self):
        activities = self.env["pm.qms.activity"].search(
            [("definition_key", "in", sorted(self.target_keys)), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(activities), 10)
        self.assertEqual(len(set(activities.mapped("definition_key"))), 10)
        for activity in activities:
            blueprint = self.blueprint_by_key[activity.definition_key]
            content = self.content_by_key[activity.definition_key]
            self.assertEqual(activity.name, content["title"])
            self.assertEqual(activity.control_id.code, blueprint["control_code"])
            line = self.pack.control_line_ids.filtered(
                lambda record, control=activity.control_id: record.control_id == control
            )
            self.assertEqual(len(line), 1)
            self.assertEqual(line.area_id.code, blueprint["phase_key"])
            self.assertEqual(
                activity.applicable_pack_ids,
                self._expected_pack_scope(activity.definition_key),
            )
            self.assertEqual(activity.activity_kind, "qms_implementation")
            self.assertTrue(activity.readiness_required)

    def test_a011_to_a015_are_materialized(self):
        activities = self.env["pm.qms.activity"].search(
            [("definition_key", "in", sorted(self.m25_5_keys)), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(activities), 5)
        self.assertEqual(set(activities.mapped("definition_key")), self.m25_5_keys)

    def test_m25_7_content_block_matches_blueprint_and_is_complete(self):
        self.assertEqual(
            {item["activity_key"] for item in self.m25_7_content["activities"]},
            self.m25_7_keys,
        )
        required = (
            "activity_key",
            "content_checkpoint",
            "title",
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
            "applicable_pack_ids",
        )
        expected = {
            "ISO9001-INITIAL-A028": ("PM-QMP-SAT-001", "P11"),
            "ISO9001-INITIAL-A029": ("PM-QMP-KPI-001", "P11"),
            "ISO9001-INITIAL-A030": ("PM-QMP-DATA-001", "P11"),
            "ISO9001-INITIAL-A031": ("PM-QMP-NCO-001", "P12"),
            "ISO9001-INITIAL-A032": ("PM-QMP-NCR-001", "P12"),
            "ISO9001-INITIAL-A033": ("PM-QMP-RCA-001", "P12"),
            "ISO9001-INITIAL-A034": ("PM-QMP-CAPA-001", "P12"),
            "ISO9001-INITIAL-A035": ("PM-QMP-CI-001", "P12"),
            "ISO9001-INITIAL-A036": ("PM-QMP-AUD-001", "P12"),
            "ISO9001-INITIAL-A037": ("PM-QMP-MRV-001", "P13"),
        }
        for item in self.m25_7_content["activities"]:
            self.assertTrue(all(item.get(field_name) for field_name in required))
            self.assertEqual(item["content_checkpoint"], "M25.7")
            self.assertEqual(item["activity_kind"], "qms_implementation")
            self.assertTrue(item["readiness_required"])
            self.assertEqual(item["applicable_pack_ids"], [INITIAL_PACK_CODE])
            self.assertEqual(
                self.blueprint_by_key[item["activity_key"]]["control_code"],
                expected[item["activity_key"]][0],
            )
            self.assertEqual(
                self.blueprint_by_key[item["activity_key"]]["phase_key"],
                expected[item["activity_key"]][1],
            )

    def test_m25_7_cross_activity_distinctions_are_explicit(self):
        by_key = {item["activity_key"]: item for item in self.m25_7_content["activities"]}
        text = {
            key: " ".join(
                item[field]
                for field in (
                    "title",
                    "description",
                    "objective",
                    "why_it_matters",
                    "implementation_steps",
                    "expected_output",
                    "evidence_expectations",
                    "success_criteria",
                )
            ).lower()
            for key, item in by_key.items()
        }
        self.assertIn("complaint", text["ISO9001-INITIAL-A028"])
        self.assertIn("feedback", text["ISO9001-INITIAL-A028"])
        self.assertIn("metric", text["ISO9001-INITIAL-A029"])
        self.assertIn("data", text["ISO9001-INITIAL-A030"])
        self.assertIn("immediate", text["ISO9001-INITIAL-A031"])
        self.assertIn("nonconformit", text["ISO9001-INITIAL-A032"])
        self.assertIn("cause", text["ISO9001-INITIAL-A033"])
        self.assertIn("effectiveness", text["ISO9001-INITIAL-A034"])
        self.assertIn("improvement", text["ISO9001-INITIAL-A035"])
        self.assertIn("objective evidence", text["ISO9001-INITIAL-A036"])
        self.assertIn("leadership", text["ISO9001-INITIAL-A037"])
        self.assertIn("decisions", text["ISO9001-INITIAL-A037"])
        self.assertNotIn("certification", text["ISO9001-INITIAL-A036"])
        self.assertNotIn("certification", text["ISO9001-INITIAL-A037"])

    def test_m25_7_content_is_standalone_and_narrative_only(self):
        text = (self.root / "content" / "initial_implementation_p11_p13_v1.json").read_text().lower()
        for marker in (
            "odoo sales",
            "odoo purchase",
            "odoo inventory",
            "odoo manufacturing",
            "odoo quality",
            "odoo maintenance",
            "accounting",
            "bi software",
            "iso 14001",
            "iso 45001",
            "as9100",
            "iatf",
            "shall",
            "certification",
            "raw ai",
            "chatter",
            "source database",
        ):
            self.assertNotIn(marker, text)

    def test_m25_7_activities_have_exact_control_phase_scope_and_semantics(self):
        activities = self.env["pm.qms.activity"].search(
            [
                ("definition_key", "in", sorted(self.m25_7_keys)),
                ("company_id", "=", self.company.id),
            ]
        )
        self.assertEqual(len(activities), 10)
        for activity in activities:
            blueprint = self.blueprint_by_key[activity.definition_key]
            self.assertEqual(activity.control_id.code, blueprint["control_code"])
            line = self.pack.control_line_ids.filtered(
                lambda record, control=activity.control_id: record.control_id == control
            )
            self.assertEqual(len(line), 1)
            self.assertEqual(line.area_id.code, blueprint["phase_key"])
            self.assertEqual(
                activity.applicable_pack_ids,
                self._expected_pack_scope(activity.definition_key),
            )
            self.assertEqual(activity.activity_kind, "qms_implementation")
            self.assertTrue(activity.readiness_required)

    def test_m25_6_content_block_matches_blueprint_and_is_complete(self):
        self.assertEqual(
            {item["activity_key"] for item in self.m25_6_content["activities"]},
            self.m25_6_keys,
        )
        required = (
            "activity_key",
            "content_checkpoint",
            "title",
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
        expected = {
            "ISO9001-INITIAL-A016": ("PM-QMP-DSG-001", "P09"),
            "ISO9001-INITIAL-A017": ("PM-QMP-OPS-001", "P09"),
            "ISO9001-INITIAL-A018": ("PM-QMP-OPS-002", "P09"),
            "ISO9001-INITIAL-A019": ("PM-QMP-REL-001", "P09"),
            "ISO9001-INITIAL-A020": ("PM-QMP-TRC-001", "P09"),
            "ISO9001-INITIAL-A021": ("PM-QMP-PROP-001", "P09"),
            "ISO9001-INITIAL-A022": ("PM-QMP-PRE-001", "P09"),
            "ISO9001-INITIAL-A023": ("PM-QMP-CHG-001", "P09"),
            "ISO9001-INITIAL-A024": ("PM-QMP-CUST-001", "P10"),
            "ISO9001-INITIAL-A025": ("PM-QMP-REQ-001", "P10"),
            "ISO9001-INITIAL-A026": ("PM-QMP-SUP-001", "P10"),
            "ISO9001-INITIAL-A027": ("PM-QMP-SUP-002", "P10"),
        }
        for item in self.m25_6_content["activities"]:
            self.assertTrue(all(item.get(field_name) for field_name in required))
            self.assertTrue(
                all(
                    isinstance(item[field_name], str)
                    for field_name in required
                    if field_name != "readiness_required"
                )
            )
            self.assertEqual(item["content_checkpoint"], "M25.6")
            self.assertEqual(item["activity_kind"], "qms_implementation")
            self.assertTrue(item["readiness_required"])
            self.assertEqual(
                self.blueprint_by_key[item["activity_key"]]["control_code"],
                expected[item["activity_key"]][0],
            )
            self.assertEqual(
                self.blueprint_by_key[item["activity_key"]]["phase_key"],
                expected[item["activity_key"]][1],
            )

    def test_m25_6_cross_activity_distinctions_are_explicit(self):
        by_key = {item["activity_key"]: item for item in self.m25_6_content["activities"]}
        self.assertIn("operational planning", by_key["ISO9001-INITIAL-A017"]["title"].lower())
        self.assertIn("work instructions", by_key["ISO9001-INITIAL-A018"]["title"].lower())
        self.assertIn("release", by_key["ISO9001-INITIAL-A019"]["title"].lower())
        self.assertIn("traceability", by_key["ISO9001-INITIAL-A020"]["title"].lower())
        self.assertIn("capture", by_key["ISO9001-INITIAL-A024"]["title"].lower())
        self.assertIn("commitment", by_key["ISO9001-INITIAL-A025"]["title"].lower())
        self.assertIn("qualify", by_key["ISO9001-INITIAL-A026"]["title"].lower())
        self.assertIn("monitor", by_key["ISO9001-INITIAL-A027"]["title"].lower())
        self.assertNotEqual(
            by_key["ISO9001-INITIAL-A024"]["objective"],
            by_key["ISO9001-INITIAL-A025"]["objective"],
        )
        self.assertNotEqual(
            by_key["ISO9001-INITIAL-A026"]["objective"],
            by_key["ISO9001-INITIAL-A027"]["objective"],
        )

    def test_m25_6_design_guidance_requires_contextual_applicability(self):
        design = next(
            item for item in self.m25_6_content["activities"]
            if item["activity_key"] == "ISO9001-INITIAL-A016"
        )
        text = " ".join(design[field] for field in (
            "description", "objective", "why_it_matters", "implementation_steps",
            "expected_output", "evidence_expectations", "success_criteria",
        )).lower()
        for marker in ("determine whether", "business-context", "applicability", "rationale"):
            self.assertIn(marker, text)
        for forbidden in (
            "every organization",
            "every customer",
            "automatically mark",
            "automatically excluded",
            "must create a design procedure",
        ):
            self.assertNotIn(forbidden, text)

    def test_m25_6_content_is_standalone_and_does_not_add_formal_evidence(self):
        text = (self.root / "content" / "initial_implementation_p09_p10_v1.json").read_text().lower()
        for marker in (
            "odoo sales", "odoo purchase", "odoo inventory", "odoo manufacturing",
            "odoo quality", "odoo maintenance", " accounting", "iso 14001",
            "iso 45001", "as9100", "iatf", "shall", "certification guarantee",
        ):
            self.assertNotIn(marker, text)
        control_codes = {
            self.blueprint_by_key[key]["control_code"] for key in self.m25_6_keys
        }
        controls = self.env["pm.qms.control"].search(
            [("code", "in", sorted(control_codes)), ("company_id", "=", self.company.id)]
        )
        before = {
            control.code: self.env["pm.qms.evidence.requirement"].search_count(
                [("control_id", "=", control.id)]
            )
            for control in controls
        }
        seed_iso9001_initial_implementation(self.env)
        after = {
            control.code: self.env["pm.qms.evidence.requirement"].search_count(
                [("control_id", "=", control.id)]
            )
            for control in controls
        }
        self.assertEqual(after, before)

    def test_m25_6_activities_have_exact_control_phase_scope_and_semantics(self):
        activities = self.env["pm.qms.activity"].search(
            [("definition_key", "in", sorted(self.m25_6_keys)), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(activities), 12)
        for activity in activities:
            blueprint = self.blueprint_by_key[activity.definition_key]
            self.assertEqual(activity.control_id.code, blueprint["control_code"])
            line = self.pack.control_line_ids.filtered(
                lambda record, control=activity.control_id: record.control_id == control
            )
            self.assertEqual(len(line), 1)
            self.assertEqual(line.area_id.code, blueprint["phase_key"])
            self.assertEqual(
                activity.applicable_pack_ids,
                self._expected_pack_scope(activity.definition_key),
            )
            self.assertEqual(activity.activity_kind, "qms_implementation")
            self.assertTrue(activity.readiness_required)

    def test_m25_5_activities_have_exact_control_phase_scope_and_semantics(self):
        activities = self.env["pm.qms.activity"].search(
            [("definition_key", "in", sorted(self.m25_5_keys)), ("company_id", "=", self.company.id)]
        )
        expected = {
            "ISO9001-INITIAL-A011": ("PM-QMP-CMP-001", "P07"),
            "ISO9001-INITIAL-A012": ("PM-QMP-AWR-001", "P07"),
            "ISO9001-INITIAL-A013": ("PM-QMP-COM-001", "P07"),
            "ISO9001-INITIAL-A014": ("PM-QMP-DOC-001", "P08"),
            "ISO9001-INITIAL-A015": ("PM-QMP-REC-001", "P08"),
        }
        self.assertEqual(len(activities), 5)
        for activity in activities:
            control_code, phase_key = expected[activity.definition_key]
            self.assertEqual(activity.control_id.code, control_code)
            line = self.pack.control_line_ids.filtered(
                lambda record, control=activity.control_id: record.control_id == control
            )
            self.assertEqual(len(line), 1)
            self.assertEqual(line.area_id.code, phase_key)
            self.assertEqual(
                activity.applicable_pack_ids,
                self._expected_pack_scope(activity.definition_key),
            )
            self.assertEqual(activity.activity_kind, "qms_implementation")
            self.assertTrue(activity.readiness_required)

    def test_loader_is_idempotent_and_seeded_identity_is_immutable(self):
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_initial_implementation(self.env)
        activities = self.env["pm.qms.activity"].search(
            [("definition_key", "in", sorted(self.all_target_keys)), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(activities), 37)
        self.assertEqual(set(activities.mapped("definition_key")), self.all_target_keys)
        with self.assertRaises(ValidationError):
            activities[0].write({"definition_key": "ISO9001-INITIAL-CHANGED"})

    def test_task_related_guidance_is_read_only_and_activity_specific(self):
        self.env.user.write(
            {"group_ids": [(4, self.env.ref("pm_qms_core.group_pm_qms_manager").id)]}
        )
        organization = self.env["pm.qms.organization"].create(
            {"name": "M25.4 Test Organization", "code": "M254-TEST-ORG", "company_id": self.company.id}
        )
        project = self.env["pm.qms.implementation.project"].create(
            {
                "name": "M25.4 Guided Content Test",
                "company_id": self.company.id,
                "organization_id": organization.id,
                "date_start": "2026-08-27",
                "target_date": "2026-09-30",
                "pack_ids": [Command.set([self.pack.id])],
            }
        )
        project._sync_framework()
        tasks = project.generated_task_ids.filtered(
            lambda task: task.pm_activity_id.definition_key in self.target_keys
        )
        self.assertEqual(len(tasks), 10)
        for field_name in (
            "pm_activity_objective",
            "pm_activity_why_it_matters",
            "pm_activity_implementation_steps",
            "pm_activity_expected_output",
            "pm_activity_evidence_expectations",
            "pm_activity_success_criteria",
            "pm_activity_responsible_role",
        ):
            self.assertTrue(self.env["project.task"]._fields[field_name].readonly)
        task = tasks[0]
        source = task.pm_activity_id
        self.assertEqual(task.pm_activity_objective, source.objective)
        self.assertEqual(task.pm_activity_evidence_expectations, source.evidence_expectations)
        self.assertEqual(task.pm_activity_responsible_role, source.responsible_role)

    def test_generation_materializes_thirty_seven_iso_tasks_and_no_generic_pack_leak(self):
        self.env.user.write(
            {"group_ids": [(4, self.env.ref("pm_qms_core.group_pm_qms_manager").id)]}
        )
        organization = self.env["pm.qms.organization"].create(
            {"name": "M25.5 Test Organization", "code": "M255-TEST-ORG", "company_id": self.company.id}
        )
        project = self.env["pm.qms.implementation.project"].create(
            {
                "name": "M25.5 ISO Guided Content Test",
                "company_id": self.company.id,
                "organization_id": organization.id,
                "date_start": "2026-08-27",
                "target_date": "2026-09-30",
                "pack_ids": [Command.set([self.pack.id])],
            }
        )
        project._sync_framework()
        tasks = project.generated_task_ids.filtered(
            lambda task: task.pm_activity_id.definition_key in self.all_target_keys
        )
        self.assertEqual(len(tasks), 37)
        self.assertEqual(
            len(tasks.filtered(lambda task: task.pm_activity_id.definition_key in self.m25_5_keys)),
            5,
        )
        self.assertEqual(
            len(tasks.filtered(lambda task: task.pm_activity_id.definition_key in self.m25_6_keys)),
            12,
        )
        self.assertEqual(
            len(tasks.filtered(lambda task: task.pm_activity_id.definition_key in self.m25_7_keys)),
            10,
        )
        self.assertTrue(all(tasks.mapped("pm_required")))

        quality_pack = self.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", "PM-QMS-QUALITY"),
                ("version", "=", "1.0"),
                ("company_id", "=", self.company.id),
            ],
            limit=1,
        )
        generic_project = self.env["pm.qms.implementation.project"].create(
            {
                "name": "M25.5 Generic Pack Isolation Test",
                "company_id": self.company.id,
                "organization_id": organization.id,
                "date_start": "2026-08-27",
                "target_date": "2026-09-30",
                "pack_ids": [Command.set([quality_pack.id])],
            }
        )
        generic_project._sync_framework()
        self.assertFalse(
            generic_project.generated_task_ids.filtered(
                lambda task: task.pm_activity_id.definition_key in self.m25_5_keys
            )
        )

    def test_m25_6_applicability_uses_existing_control_instance_workflow(self):
        self.env.user.write(
            {"group_ids": [(4, self.env.ref("pm_qms_core.group_pm_qms_manager").id)]}
        )
        organization = self.env["pm.qms.organization"].create(
            {"name": "M25.6 Applicability Organization", "code": "M256-APP-ORG", "company_id": self.company.id}
        )
        project = self.env["pm.qms.implementation.project"].create(
            {
                "name": "M25.6 Applicability Test",
                "company_id": self.company.id,
                "organization_id": organization.id,
                "date_start": "2026-08-27",
                "target_date": "2026-09-30",
                "pack_ids": [Command.set([self.pack.id])],
            }
        )
        project._sync_framework()
        lines = project.implementation_control_ids.filtered(
            lambda line: line.control_id.code in {"PM-QMP-DSG-001", "PM-QMP-PROP-001"}
        )
        self.assertEqual(len(lines), 2)
        design = lines.filtered(lambda line: line.control_id.code == "PM-QMP-DSG-001")
        property_line = lines.filtered(lambda line: line.control_id.code == "PM-QMP-PROP-001")
        design_task = design.task_ids.filtered("pm_generated")[:1]
        self.assertEqual(design.applicability, "applicable")
        self.assertTrue(design_task)
        self.assertTrue(design_task.pm_required)

        for line in (design, property_line):
            line.control_instance_id.with_user(self.env.user).write(
                {"justification": "This fictional organization does not control this activity in its current scope."}
            )
            line.control_instance_id.with_user(self.env.user).action_mark_not_applicable()

        self.assertEqual(design.readiness_state, "not_applicable")
        self.assertEqual(property_line.readiness_state, "not_applicable")
        self.assertEqual(design.implementation_status, "not_applicable")
        self.assertEqual(property_line.implementation_status, "not_applicable")
        self.assertTrue(design_task.pm_required)
        self.assertGreaterEqual(design.open_activity_count, 1)
        self.assertEqual(project.not_applicable_controls, 2)
        self.assertEqual(
            project.applicable_controls,
            project.total_controls - project.not_applicable_controls,
        )

    def test_m25_5_narrative_guidance_does_not_change_formal_evidence(self):
        control_codes = {
            "PM-QMP-CMP-001",
            "PM-QMP-AWR-001",
            "PM-QMP-COM-001",
            "PM-QMP-DOC-001",
            "PM-QMP-REC-001",
        }
        controls = self.env["pm.qms.control"].search(
            [("code", "in", sorted(control_codes)), ("company_id", "=", self.company.id)]
        )
        before = {
            control.code: self.env["pm.qms.evidence.requirement"].search_count(
                [("control_id", "=", control.id)]
            )
            for control in controls
        }
        seed_iso9001_initial_implementation(self.env)
        after = {
            control.code: self.env["pm.qms.evidence.requirement"].search_count(
                [("control_id", "=", control.id)]
            )
            for control in controls
        }
        self.assertEqual(after, before)

    def test_narrative_guidance_does_not_create_structured_iso_evidence(self):
        control_ids = self.pack.control_line_ids.filtered(
            lambda line: line.control_id.code in {
                item["control_code"] for item in self.blueprint["activities"][:10]
            }
        ).mapped("control_id").ids
        before = {
            control_id: self.env["pm.qms.evidence.requirement"].search_count(
                [("control_id", "=", control_id)]
            )
            for control_id in control_ids
        }
        seed_iso9001_initial_implementation(self.env)
        after = {
            control_id: self.env["pm.qms.evidence.requirement"].search_count(
                [("control_id", "=", control_id)]
            )
            for control_id in control_ids
        }
        self.assertEqual(after, before)

    def test_authored_content_has_no_source_or_protected_content_markers(self):
        for filename in (
            "initial_implementation_p01_p06_v1.json",
            "initial_implementation_p07_p08_v1.json",
            "initial_implementation_p09_p10_v1.json",
            "initial_implementation_p11_p13_v1.json",
        ):
            text = (self.root / "content" / filename).read_text().lower()
            for marker in (
                "raw ai",
                "chatter",
                "email",
                "customer identifier",
                "source database",
                "source user",
                "iso 14001",
                "iso 45001",
                "as9100",
                "iatf",
                "transition",
                "certification",
                "shall",
            ):
                self.assertNotIn(marker, text)
