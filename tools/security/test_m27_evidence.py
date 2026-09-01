"""Focused integrity checks for M27's generated security evidence."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import m27_authorization_matrix as matrix
import m27_sudo_inventory as sudo_inventory


class TestM27Evidence(unittest.TestCase):
    def test_matrix_is_deterministic_and_has_no_unsupported_claims(self):
        root = Path(__file__).resolve().parents[2]
        first = matrix.rows(root / "addons")
        second = matrix.rows(root / "addons")
        self.assertEqual(first, second)
        summary = matrix.validate(first)
        self.assertEqual(summary["p0_sensitive_untested"], 0)
        self.assertEqual(summary["p1_sensitive_untested"], 0)

    def test_matrix_rejects_static_pass_claim(self):
        root = Path(__file__).resolve().parents[2]
        row = matrix.rows(root / "addons")[0].copy()
        row.update(status="PASS", runtime_executed="NO", evidence="Source inventory only")
        with self.assertRaises(ValueError):
            matrix.validate([row])

    def test_sudo_inventory_has_specific_production_evidence(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as workspace:
            output = Path(workspace) / "sudo.csv"
            summary = sudo_inventory.generate(root / "addons", output)
            self.assertEqual(summary["production"], 17)
            self.assertGreater(summary["test_only"], 0)
            self.assertEqual(summary["total"], summary["production"] + summary["test_only"])
            self.assertEqual(summary["unresolved_p0"], 0)
            self.assertEqual(summary["unresolved_p1"], 0)
            with output.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertTrue(all(row["invoker"] and row["follow_up"] for row in rows if row["site_type"] == "PRODUCTION_REVIEWED"))

    def test_sudo_inventory_reports_uncovered_p1_instead_of_false_zero(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as workspace:
            output = Path(workspace) / "sudo.csv"
            sudo_inventory.generate(root / "addons", output)
            with output.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        row = next(row for row in rows if row["file"] == "addons/pm_qms_license/services/entitlement_service.py" and row["line"] == "65")
        row["runtime_covered"] = "NO"
        summary = sudo_inventory.validate(rows)
        self.assertEqual(summary["unresolved_p0"], 0)
        self.assertEqual(summary["unresolved_p1"], 1)
        self.assertEqual(summary["deferred_p2"], 2)


if __name__ == "__main__":
    unittest.main()
