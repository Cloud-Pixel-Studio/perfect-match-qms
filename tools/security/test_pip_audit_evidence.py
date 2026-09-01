"""Regression tests for explicit pip-audit evidence states."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.security import pip_audit_evidence as evidence


class TestPipAuditEvidence(unittest.TestCase):
    def test_missing_input_is_not_executed(self):
        result = evidence.classify_missing_input("requirements.txt")
        self.assertEqual(result["status"], evidence.NOT_EXECUTED)
        self.assertEqual(result["policy_result"], "NOT_APPLICABLE")

    def test_clean_output_is_pass_no_findings(self):
        result = evidence.classify_output("[]", 0, "requirements.txt")
        self.assertEqual(result["status"], evidence.PASS_NO_FINDINGS)
        self.assertEqual(result["policy_result"], "PASS")

    def test_vulnerable_output_is_untriaged_and_nonzero_policy(self):
        payload = json.dumps([{"name": "fictional-package", "vulns": [{"id": "PYSEC-0000"}]}])
        result = evidence.classify_output(payload, 1, "requirements.txt")
        self.assertEqual(result["status"], evidence.FINDINGS_UNTRIAGED)
        self.assertEqual(result["policy_result"], "FAIL")
        self.assertEqual(result["findings_count"], 1)

    def test_malformed_output_is_error_not_findings(self):
        result = evidence.classify_output("not-json", 2, "requirements.txt")
        self.assertEqual(result["status"], evidence.ERROR_BLOCKED)
        self.assertEqual(result["policy_result"], "ERROR")

    def test_summary_cannot_false_pass_vulnerable_result(self):
        base = {"status": "BASELINE", "policy_failures": 0, "infra_failures": 0, "exit_code": 0}
        vulnerable = evidence.classify_output(
            json.dumps({"dependencies": [{"name": "fictional-package", "vulns": [{"id": "PYSEC-0000"}]}]}),
            1,
        )
        result = evidence.apply_to_summary(base, vulnerable)
        self.assertEqual(result["pip_audit_status"], evidence.FINDINGS_UNTRIAGED)
        self.assertEqual(result["pip_audit_policy_result"], "FAIL")
        self.assertEqual(result["status"], "POLICY_FAILURE")
        self.assertEqual(result["exit_code"], 1)

    def test_summary_adds_one_policy_failure_for_one_vulnerability(self):
        base = {"status": "BASELINE", "policy_failures": 0, "infra_failures": 0, "exit_code": 0}
        result = evidence.apply_to_summary(
            base,
            evidence.classify_output(json.dumps([{"vulns": [{"id": "PYSEC-0000"}]}]), 1),
        )
        self.assertEqual(result["policy_failures"], 1)
        self.assertEqual(result["infra_failures"], 0)
        self.assertEqual(result["status"], "POLICY_FAILURE")
        self.assertEqual(result["exit_code"], 1)

    def test_summary_adds_one_infra_failure_for_one_tool_failure(self):
        base = {"status": "BASELINE", "policy_failures": 0, "infra_failures": 0, "exit_code": 0}
        result = evidence.apply_to_summary(base, evidence.classify_output("not-json", 2))
        self.assertEqual(result["policy_failures"], 0)
        self.assertEqual(result["infra_failures"], 1)
        self.assertEqual(result["status"], "INFRA_FAILURE")
        self.assertEqual(result["exit_code"], 2)

    def test_summary_preserves_unrelated_failures_without_duplication(self):
        base = {"status": "POLICY_FAILURE", "policy_failures": 2, "infra_failures": 0, "exit_code": 1}
        result = evidence.apply_to_summary(base, evidence.classify_output("[]", 0))
        self.assertEqual(result["policy_failures"], 2)
        self.assertEqual(result["infra_failures"], 0)
        self.assertEqual(result["status"], "POLICY_FAILURE")
        self.assertEqual(result["exit_code"], 1)

    def test_summary_missing_input_adds_no_failure(self):
        base = {"status": "BASELINE", "policy_failures": 0, "infra_failures": 0, "exit_code": 0}
        result = evidence.apply_to_summary(base, evidence.classify_missing_input())
        self.assertEqual(result["policy_failures"], 0)
        self.assertEqual(result["infra_failures"], 0)
        self.assertEqual(result["pip_audit_status"], evidence.NOT_EXECUTED)
        self.assertEqual(result["pip_audit_policy_result"], "NOT_APPLICABLE")
        self.assertEqual(result["exit_code"], 0)

    def test_cli_writes_distinct_tool_failure(self):
        with tempfile.TemporaryDirectory() as workspace:
            root = Path(workspace)
            output = root / "pip-audit.status.json"
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("pip_audit_evidence.py")), "--output", str(output), "--input-path", "requirements.txt", "--tool-exit-code", "2"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads(output.read_text())["status"], evidence.ERROR_BLOCKED)


if __name__ == "__main__":
    unittest.main()
