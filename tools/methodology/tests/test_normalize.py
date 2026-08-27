import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.methodology.normalize import normalize, sha256_file


FIXTURE = Path(__file__).parent / "fixtures" / "source"


def fixture_zip(folder: Path) -> Path:
    archive = folder / "fixture.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(FIXTURE.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(FIXTURE).as_posix())
    return archive


class NormalizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = fixture_zip(self.root)
        self.output = self.root / "generated"

    def tearDown(self):
        self.temp.cleanup()

    def run_normalizer(self):
        return normalize(self.source, self.output, sha256_file(self.source))

    def load(self, filename):
        return json.loads((self.output / filename).read_text(encoding="utf-8"))

    def test_source_package_hash_verification(self):
        result = self.run_normalizer()
        self.assertEqual(result["source_sha256"], sha256_file(self.source))
        with self.assertRaises(ValueError):
            normalize(self.source, self.root / "bad", "0" * 64)

    def test_deterministic_output(self):
        first = self.run_normalizer()["manifest"]["content_hash"]
        second = normalize(self.source, self.root / "generated-2", sha256_file(self.source))["manifest"]["content_hash"]
        self.assertEqual(first, second)

    def test_inventory_counts_and_stage_counts(self):
        self.run_normalizer()
        inventory = self.load("inventory.json")
        self.assertEqual(inventory["source_counts"], {
            "projects": 1, "stages": 5, "main_tasks": 10, "subtasks": 11,
            "total_tasks": 21, "tags": 4, "chatter": 1, "dependencies": 0,
            "attachments": 0,
        })
        self.assertEqual(inventory["source_stage_counts"]["Context of the Organization"], 3)
        self.assertEqual(inventory["source_stage_counts"]["ISO 9001:2026 Transition Readiness"], 2)

    def test_chatter_excluded(self):
        result = self.run_normalizer()
        candidates = self.load("normalized_candidates.json")
        self.assertNotIn("chatter", candidates)
        self.assertEqual(result["source_counts"]["chatter"], 1)

    def test_users_and_emails_excluded(self):
        result = self.run_normalizer()
        raw = (self.output / "normalized_candidates.json").read_text(encoding="utf-8")
        self.assertNotIn("person@example.invalid", raw)
        self.assertNotIn("Assignees/Email", raw)
        self.assertGreaterEqual(result["summary"]["personal_source_user_data_removed"], 1)

    def test_ai_raw_prompt_excluded(self):
        result = self.run_normalizer()
        raw = (self.output / "normalized_candidates.json").read_text(encoding="utf-8")
        self.assertNotIn("Fictional raw prompt", raw)
        self.assertGreater(result["summary"]["raw_ai_prompts_detected"], 0)

    def test_administrative_classification(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["main_tasks"] if row["title"] == "Project kickoff logistics")
        self.assertEqual(item["classification"], "PROJECT_ADMINISTRATION")
        self.assertEqual(item["readiness_candidate"], "FALSE")
        self.assertEqual(item["initial_implementation_candidate"], "NO")

    def test_stage_authority_prevents_shared_year_contamination(self):
        self.run_normalizer()
        mains = self.load("normalized_candidates.json")["main_tasks"]
        item = next(row for row in mains if row["title"] == "Define QMS Process Map")
        self.assertEqual(item["classification"], "QMS_IMPLEMENTATION")
        self.assertEqual(item["initial_implementation_candidate"], "YES")
        item = next(row for row in mains if row["title"] == "Review context with shared release metadata")
        self.assertEqual(item["classification"], "QMS_IMPLEMENTATION")
        self.assertNotIn("TRANSITION_CONTENT", item["review_flags"])

    def test_explicit_transition_stage_classifies_transition(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["main_tasks"] if row["title"] == "2026 transition planning")
        self.assertEqual(item["classification"], "TRANSITION")
        self.assertIn("TRANSITION_TRIGGER_STAGE_NAME", item["review_flags"])
        self.assertEqual(item["readiness_candidate"], "FALSE")

    def test_other_standard_quarantine(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["main_tasks"] if "14001" in row["title"])
        self.assertIn("OTHER_STANDARD_REFERENCE", item["review_flags"])
        self.assertIn(item, self.load("quarantine.json")["records"])

    def test_ip_review_quarantine(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["subtasks"] if row["title"] == "Protected text note")
        self.assertIn("POSSIBLE_STANDARD_TEXT", item["review_flags"])
        self.assertEqual(item["guidance"], "")
        self.assertIn(item, self.load("quarantine.json")["records"])

    def test_tag_normalization_and_unresolved_tags(self):
        result = self.run_normalizer()
        tags = self.load("tag_normalization.json")["tags"]
        self.assertEqual(next(row for row in tags if row["name"] == "Evidence")["status"], "KNOWN")
        self.assertEqual(next(row for row in tags if row["name"] == "Unmapped Concept")["status"], "UNRESOLVED")
        self.assertGreater(result["summary"]["unresolved_tags"], 0)

    def test_duplicate_detection_includes_candidate_content(self):
        result = self.run_normalizer()
        self.assertGreater(result["summary"]["duplicate_groups"], 0)
        self.assertTrue(any("DUPLICATE_CONTENT" in row["review_flags"] for row in self.load("normalized_candidates.json")["main_tasks"]))

    def test_stable_provenance_keys_and_parent_context(self):
        self.run_normalizer()
        data = self.load("normalized_candidates.json")
        self.assertTrue(all(row["source_record_key"].startswith("src-") for row in data["main_tasks"]))
        self.assertFalse(any("old-main" in json.dumps(row) for row in data["main_tasks"]))
        child = next(row for row in data["subtasks"] if row["title"] == "Collect evidence")
        self.assertEqual(child["parent_classification"], "QMS_IMPLEMENTATION")
        self.assertTrue(child["parent_source_record_key"].startswith("src-"))

    def test_transition_parent_preserves_semantic_subtask(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["subtasks"] if row["title"] == "Document current gap")
        self.assertIn(item["classification"], {"IMPLEMENTATION_STEP", "EVIDENCE_EXPECTATION", "DELIVERABLE", "SUCCESS_CRITERION"})
        self.assertEqual(item["readiness_candidate"], "FALSE")
        self.assertIn("parent_classification", item)

    def test_ambiguous_item_is_low_confidence_review(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["subtasks"] if row["title"] == "Check item")
        self.assertEqual(item["classification"], "NEEDS_REVIEW")
        self.assertEqual(item["confidence"], "LOW")
        self.assertIn(item, self.load("review_queue.json")["records"])

    def test_stable_content_hash(self):
        result = self.run_normalizer()
        self.assertEqual(result["manifest"]["content_hash"], self.load("manifest.json")["content_hash"])

    def test_no_raw_source_ids_as_product_ids(self):
        self.run_normalizer()
        raw = (self.output / "normalized_candidates.json").read_text(encoding="utf-8")
        self.assertNotIn("old-main-", raw)
        self.assertNotIn("old-sub-", raw)
        self.assertNotIn("External ID", raw)

    def test_synthetic_fixture_is_original_and_present(self):
        self.assertTrue((FIXTURE / "manifest.json").exists())
        self.assertIn("fictional", (FIXTURE / "manifest.json").read_text(encoding="utf-8"))

    def test_generated_workspace_is_explicit_output(self):
        result = self.run_normalizer()
        self.assertEqual(Path(result["output"]), self.output)
        self.assertTrue((self.output / "quarantine.json").exists())

    def test_subtask_semantics_are_not_collapsed_to_archive(self):
        result = self.run_normalizer()
        subtasks = self.load("normalized_candidates.json")["subtasks"]
        self.assertEqual(next(row for row in subtasks if row["title"] == "Collect evidence")["classification"], "EVIDENCE_EXPECTATION")
        self.assertEqual(next(row for row in subtasks if row["title"] == "Confirm success criterion")["classification"], "SUCCESS_CRITERION")
        self.assertNotEqual(result["summary"]["subtask_classification"].get("IGNORE_ARCHIVE", 0), len(subtasks))

    def test_distribution_warnings_are_clear_for_fixture(self):
        self.run_normalizer()
        warnings = self.load("classification_summary.json")["distribution_warnings"]
        self.assertFalse(warnings["main_category_over_80_percent"])
        self.assertFalse(warnings["subtasks_over_90_percent_ignore_archive"])
        self.assertFalse(warnings["no_semantic_subtasks"])


if __name__ == "__main__":
    unittest.main()
