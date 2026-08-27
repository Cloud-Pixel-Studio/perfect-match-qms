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

    def test_inventory_counts(self):
        self.run_normalizer()
        self.assertEqual(self.load("inventory.json")["source_counts"], {
            "projects": 1, "stages": 2, "main_tasks": 8, "subtasks": 9,
            "total_tasks": 17, "tags": 4, "chatter": 1, "dependencies": 0,
            "attachments": 0,
        })

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
        mains = self.load("normalized_candidates.json")["main_tasks"]
        item = next(row for row in mains if row["title"] == "Project kickoff logistics")
        self.assertEqual(item["classification"], "PROJECT_ADMINISTRATION")
        self.assertEqual(item["readiness_candidate"], "FALSE")
        self.assertEqual(item["initial_implementation_candidate"], "NO")

    def test_transition_separation(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["main_tasks"] if "transition" in row["title"])
        self.assertEqual(item["classification"], "TRANSITION")
        self.assertIn("TRANSITION_CONTENT", item["review_flags"])
        self.assertEqual(item["readiness_candidate"], "FALSE")

    def test_other_standard_quarantine(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["main_tasks"] if "14001" in row["title"])
        self.assertIn("OTHER_STANDARD_REFERENCE", item["review_flags"])
        self.assertIn(item, self.load("quarantine.json")["records"])

    def test_ip_review_quarantine(self):
        self.run_normalizer()
        item = next(row for row in self.load("normalized_candidates.json")["main_tasks"] if row["title"] == "Mystery item")
        self.assertIn("AMBIGUOUS_CLASSIFICATION", item["review_flags"])
        self.assertIn(item, self.load("review_queue.json")["records"])

    def test_possible_protected_text_is_quarantined(self):
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

    def test_duplicate_detection(self):
        result = self.run_normalizer()
        self.assertGreater(result["summary"]["duplicate_groups"], 0)

    def test_stable_provenance_keys(self):
        self.run_normalizer()
        rows = self.load("normalized_candidates.json")["main_tasks"]
        self.assertTrue(all(row["source_record_key"].startswith("src-") for row in rows))
        self.assertFalse(any("old-main" in json.dumps(row) for row in rows))

    def test_stable_content_hash(self):
        result = self.run_normalizer()
        self.assertEqual(result["manifest"]["content_hash"], self.load("manifest.json")["content_hash"])

    def test_no_raw_source_ids_as_product_ids(self):
        self.run_normalizer()
        raw = (self.output / "normalized_candidates.json").read_text(encoding="utf-8")
        self.assertNotIn("old-main-", raw)
        self.assertNotIn("External ID", raw)

    def test_synthetic_fixture_is_original_and_present(self):
        self.assertTrue((FIXTURE / "manifest.json").exists())
        self.assertIn("fictional", (FIXTURE / "manifest.json").read_text(encoding="utf-8"))

    def test_generated_workspace_is_explicit_output(self):
        result = self.run_normalizer()
        self.assertEqual(Path(result["output"]), self.output)
        self.assertTrue((self.output / "quarantine.json").exists())

    def test_subtask_semantics(self):
        self.run_normalizer()
        subtasks = self.load("normalized_candidates.json")["subtasks"]
        self.assertEqual(next(row for row in subtasks if row["title"] == "Collect evidence")["classification"], "EVIDENCE_EXPECTATION")
        self.assertEqual(next(row for row in subtasks if row["title"] == "Confirm success criterion")["classification"], "SUCCESS_CRITERION")
        self.assertEqual(next(row for row in subtasks if row["title"] == "Transition note")["classification"], "IGNORE_ARCHIVE")


if __name__ == "__main__":
    unittest.main()
