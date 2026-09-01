"""Classify pip-audit evidence without treating missing input as a clean scan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


NOT_EXECUTED = "NOT_EXECUTED"
PASS_NO_FINDINGS = "PASS_NO_FINDINGS"
FINDINGS_UNTRIAGED = "FINDINGS_UNTRIAGED"
ERROR_BLOCKED = "ERROR/BLOCKED"


def classify_missing_input(input_path: str | None = None) -> dict[str, Any]:
    """Return the explicit state for a repository without a lock/input file."""
    return {
        "tool": "pip-audit",
        "status": NOT_EXECUTED,
        "policy_result": "NOT_APPLICABLE",
        "exit_code": 0,
        "findings_count": 0,
        "input": input_path,
        "reason": "No canonical dependency lock or requirements input exists.",
        "follow_up": "Issue #98",
    }


def _finding_count(payload: Any) -> int:
    if isinstance(payload, list):
        return sum(len(item.get("vulns", [])) for item in payload if isinstance(item, dict))
    if isinstance(payload, dict):
        for key in ("vulnerabilities", "findings"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        dependencies = payload.get("dependencies")
        if isinstance(dependencies, list):
            return _finding_count(dependencies)
    raise ValueError("pip-audit JSON has no recognized dependency result shape")


def classify_output(raw: str, tool_exit_code: int, input_path: str | None = None) -> dict[str, Any]:
    """Classify valid pip-audit JSON and distinguish findings from tool failure."""
    try:
        payload = json.loads(raw)
        findings_count = _finding_count(payload)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return {
            "tool": "pip-audit",
            "status": ERROR_BLOCKED,
            "policy_result": "ERROR",
            "exit_code": tool_exit_code or 2,
            "findings_count": 0,
            "input": input_path,
            "reason": f"Malformed or unusable pip-audit output: {exc}",
        }

    if findings_count:
        return {
            "tool": "pip-audit",
            "status": FINDINGS_UNTRIAGED,
            "policy_result": "FAIL",
            "exit_code": tool_exit_code or 1,
            "findings_count": findings_count,
            "input": input_path,
            "reason": "pip-audit reported vulnerabilities requiring triage.",
        }
    if tool_exit_code:
        return {
            "tool": "pip-audit",
            "status": ERROR_BLOCKED,
            "policy_result": "ERROR",
            "exit_code": tool_exit_code,
            "findings_count": 0,
            "input": input_path,
            "reason": "pip-audit exited non-zero without vulnerability findings.",
        }
    return {
        "tool": "pip-audit",
        "status": PASS_NO_FINDINGS,
        "policy_result": "PASS",
        "exit_code": 0,
        "findings_count": 0,
        "input": input_path,
        "reason": "pip-audit completed with no reported vulnerabilities.",
    }


def apply_to_summary(summary: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Add pip-audit evidence and its policy effect to an authoritative summary."""
    result = dict(summary)
    result["pip_audit"] = evidence
    result["pip_audit_findings"] = int(evidence.get("findings_count", 0))
    result["pip_audit_policy_result"] = evidence.get("policy_result", "ERROR")
    result["pip_audit_status"] = evidence.get("status", ERROR_BLOCKED)
    result["policy_failures"] = int(result.get("policy_failures", 0))
    result["infra_failures"] = int(result.get("infra_failures", 0))
    if evidence.get("status") == FINDINGS_UNTRIAGED:
        result["policy_failures"] += 1
    elif evidence.get("status") == ERROR_BLOCKED:
        result["infra_failures"] += 1
    if result["infra_failures"]:
        result["status"] = "INFRA_FAILURE"
        result["exit_code"] = 2
    elif result["policy_failures"]:
        result["status"] = "POLICY_FAILURE"
        result["exit_code"] = 1
    return result


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--input-path")
    parser.add_argument("--tool-exit-code", type=int, default=0)
    parser.add_argument("--missing-input", action="store_true")
    args = parser.parse_args()
    if args.missing_input:
        evidence = classify_missing_input(args.input_path)
    elif args.input is None or not args.input.is_file():
        evidence = {
            "tool": "pip-audit",
            "status": ERROR_BLOCKED,
            "policy_result": "ERROR",
            "exit_code": args.tool_exit_code or 2,
            "findings_count": 0,
            "input": args.input_path,
            "reason": "pip-audit output was not produced.",
        }
    else:
        evidence = classify_output(args.input.read_text(encoding="utf-8"), args.tool_exit_code, args.input_path)
    _write(args.output, evidence)
    print(json.dumps(evidence, sort_keys=True))
    if evidence["status"] == FINDINGS_UNTRIAGED:
        return 1
    if evidence["status"] == ERROR_BLOCKED:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
