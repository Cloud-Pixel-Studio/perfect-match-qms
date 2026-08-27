import json
from pathlib import Path

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import (
    INITIAL_PACK_CODE,
    INITIAL_PACK_VERSION,
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
        cls.root = Path(__file__).parents[1]
        cls.blueprint = json.loads(
            (cls.root / "content" / "initial_implementation_v1.json").read_text()
        )
        cls.content = json.loads(
            (cls.root / "content" / "initial_implementation_p01_p06_v1.json").read_text()
        )
        cls.blueprint_by_key = {
            item["activity_key"]: item for item in cls.blueprint["activities"]
        }
        cls.content_by_key = {
            item["activity_key"]: item for item in cls.content["activities"]
        }
        cls.target_keys = {f"ISO9001-INITIAL-A{i:03d}" for i in range(1, 11)}

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
            self.assertEqual(activity.applicable_pack_ids, self.pack)
            self.assertEqual(activity.activity_kind, "qms_implementation")
            self.assertTrue(activity.readiness_required)

    def test_a011_to_a037_remain_blueprint_only(self):
        later_keys = {
            f"ISO9001-INITIAL-A{i:03d}" for i in range(11, 38)
        }
        self.assertFalse(
            self.env["pm.qms.activity"].search(
                [("definition_key", "in", sorted(later_keys))]
            )
        )

    def test_loader_is_idempotent_and_seeded_identity_is_immutable(self):
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_initial_implementation(self.env)
        activities = self.env["pm.qms.activity"].search(
            [("definition_key", "in", sorted(self.target_keys)), ("company_id", "=", self.company.id)]
        )
        self.assertEqual(len(activities), 10)
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
        text = (self.root / "content" / "initial_implementation_p01_p06_v1.json").read_text().lower()
        for marker in (
            "raw ai",
            "chatter",
            "email",
            "customer identifier",
            "source database",
            "iso 14001",
            "iso 45001",
            "as9100",
            "iatf",
            "certification-ready",
            "shall",
        ):
            self.assertNotIn(marker, text)
