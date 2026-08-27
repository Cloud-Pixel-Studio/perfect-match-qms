#!/usr/bin/env python3
"""Deterministic, local-only normalization of historical methodology ZIPs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

VERSION = "m25.2.0"
MAIN_CATEGORIES = (
    "QMS_IMPLEMENTATION", "PROJECT_ADMINISTRATION", "READINESS_ASSESSMENT",
    "CERTIFICATION_PREPARATION", "TRANSITION", "GAP_REMEDIATION", "OTHER",
    "NEEDS_REVIEW",
)
SUBTASK_CATEGORIES = (
    "IMPLEMENTATION_STEP", "GUIDANCE", "DELIVERABLE", "EVIDENCE_EXPECTATION",
    "SUCCESS_CRITERION", "DEPENDENCY", "NEXT_ACTION", "PROJECT_ADMINISTRATION",
    "IGNORE_ARCHIVE", "NEEDS_REVIEW",
)
OTHER_STANDARDS = ("ISO 14001", "ISO 45001", "AS9100", "AS9120", "IATF", "CMMC")
SENSITIVE_FIELD = re.compile(
    r"(?:email|author|user|login|avatar|password|token|database|server|environment|"
    r"created|updated|timestamp|date|follower|subscriber|message|chatter|prompt|"
    r"response|model|source.?id|record.?id|company|customer|attachment|technical)", re.I
)
HTML_TAG = re.compile(r"<[^>]+>")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def normalize_text(value: Any) -> str:
    text = HTML_TAG.sub(" ", html.unescape(str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


def safe_value(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[REDACTED_EMAIL]", text)
    return re.sub(r"\b(?:https?://|ssh://)\S+", "[REDACTED_URI]", text, flags=re.I)


def read_csv(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    with zf.open(name) as stream:
        text = io.TextIOWrapper(stream, encoding="utf-8-sig", errors="replace", newline="")
        return list(csv.DictReader(text))


def read_json(zf: zipfile.ZipFile, name: str) -> Any:
    with zf.open(name) as stream:
        return json.load(io.TextIOWrapper(stream, encoding="utf-8", errors="replace"))


def find_member(zf: zipfile.ZipFile, suffix: str) -> str | None:
    suffix = suffix.lstrip("/")
    matches = sorted(name for name in zf.namelist() if name.endswith(suffix))
    return matches[0] if matches else None


def field(row: dict[str, Any], *names: str) -> str:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lowered:
            return safe_value(lowered[name.lower()])
    for key, value in lowered.items():
        if any(name.lower() in key for name in names):
            return safe_value(value)
    return ""


def source_key(kind: str, row: dict[str, Any], ordinal: int) -> str:
    structural = {
        "kind": kind,
        "ordinal": ordinal,
        "stage": field(row, "stage name", "stage", "parent task name"),
        "title": field(row, "name", "title"),
        "description": field(row, "description", "description html"),
        "sequence": field(row, "sequence"),
    }
    digest = hashlib.sha256(stable_json(structural).encode()).hexdigest()
    return f"src-{digest[:20]}"


def search_text(row: dict[str, Any]) -> str:
    return " ".join(
        safe_value(value).lower()
        for key, value in row.items()
        if not SENSITIVE_FIELD.search(str(key))
    )


def other_standard_refs(text: str) -> list[str]:
    upper = text.upper()
    return [standard for standard in OTHER_STANDARDS if standard in upper]


def classify_main(row: dict[str, Any]) -> tuple[str, str, list[str]]:
    text = search_text(row)
    flags: list[str] = []
    if other_standard_refs(text):
        flags.append("OTHER_STANDARD_REFERENCE")
    if "transition" in text or "2026" in text:
        return "TRANSITION", "HIGH", flags + ["TRANSITION_CONTENT"]
    if any(word in text for word in (
        "kickoff", "kick-off", "schedule", "meeting", "logistics",
        "communication cadence", "project closure", "consulting administration",
    )):
        return "PROJECT_ADMINISTRATION", "HIGH", flags + ["ADMINISTRATIVE_ONLY"]
    if any(word in text for word in ("certification", "external audit", "certification readiness")):
        return "CERTIFICATION_PREPARATION", "MEDIUM", flags
    if any(word in text for word in ("gap assessment", "readiness assessment", "maturity assessment")):
        return "READINESS_ASSESSMENT", "MEDIUM", flags
    if any(word in text for word in ("gap remediation", "remediate gap", "corrective gap")):
        return "GAP_REMEDIATION", "MEDIUM", flags
    if any(word in text for word in (
        "quality", "process", "procedure", "risk", "context", "objective", "kpi",
        "competenc", "document", "audit", "corrective", "supplier", "customer", "control",
    )):
        return "QMS_IMPLEMENTATION", "HIGH", flags
    return "NEEDS_REVIEW", "LOW", flags + ["AMBIGUOUS_CLASSIFICATION"]


def implementation_eligibility(category: str, flags: Iterable[str]) -> str:
    if category == "QMS_IMPLEMENTATION" and not set(flags) & {
        "OTHER_STANDARD_REFERENCE", "POSSIBLE_STANDARD_TEXT", "PERSONAL_OR_USER_DATA",
    }:
        return "YES"
    if category in {
        "PROJECT_ADMINISTRATION", "READINESS_ASSESSMENT", "CERTIFICATION_PREPARATION",
        "TRANSITION", "GAP_REMEDIATION",
    }:
        return "NO"
    return "REVIEW"


def map_phase(text: str, category: str) -> str:
    rules = (
        ("P01", ("setup", "governance", "kickoff")),
        ("P02", ("context", "scope", "interested party")),
        ("P03", ("process", "workflow", "architecture")),
        ("P04", ("leadership", "responsib", "role")),
        ("P05", ("risk", "planning", "change")),
        ("P06", ("objective", "kpi", "resource")),
        ("P07", ("competenc", "training", "awareness", "communication")),
        ("P08", ("document", "record", "information")),
        ("P09", ("operation", "procedure", "control")),
        ("P10", ("customer", "supplier", "purchas")),
        ("P11", ("measure", "monitor", "performance", "metric")),
        ("P12", ("audit", "corrective", "ncr", "improvement")),
        ("P13", ("management review", "certification", "readiness")),
    )
    for phase, words in rules:
        if any(word in text for word in words):
            return phase
    if category == "PROJECT_ADMINISTRATION":
        return "P01"
    if category == "CERTIFICATION_PREPARATION":
        return "P13"
    return "REVIEW"


def classify_subtask(row: dict[str, Any]) -> tuple[str, list[str]]:
    text = search_text(row)
    flags: list[str] = []
    if other_standard_refs(text):
        flags.append("OTHER_STANDARD_REFERENCE")
    if "transition" in text or "2026" in text:
        return "IGNORE_ARCHIVE", flags + ["TRANSITION_CONTENT"]
    if any(word in text for word in ("meeting", "schedule", "logistics", "project admin", "kickoff")):
        return "PROJECT_ADMINISTRATION", flags + ["ADMINISTRATIVE_ONLY"]
    if any(word in text for word in ("evidence", "record", "proof", "retain")):
        return "EVIDENCE_EXPECTATION", flags
    if any(word in text for word in ("success criterion", "acceptance", "successful", "effectiveness")):
        return "SUCCESS_CRITERION", flags
    if any(word in text for word in ("deliverable", "output", "submit", "produce")):
        return "DELIVERABLE", flags
    if any(word in text for word in ("depends", "dependency", "prerequisite")):
        return "DEPENDENCY", flags
    if any(word in text for word in ("next action", "follow-up", "follow up", "next step")):
        return "NEXT_ACTION", flags
    if any(word in text for word in ("guidance", "explain", "how to", "consider")):
        return "GUIDANCE", flags
    if any(word in text for word in ("implement", "configure", "create", "define", "establish", "review")):
        return "IMPLEMENTATION_STEP", flags
    return "NEEDS_REVIEW", flags + ["AMBIGUOUS_CLASSIFICATION"]


def tag_dimensions(name: str) -> list[str]:
    text = name.lower()
    dimensions: list[str] = []
    if any(word in text for word in ("high", "urgent", "priority")):
        dimensions.append("priority")
    if any(word in text for word in ("evidence", "record", "document")):
        dimensions.append("evidence_type")
    if any(word in text for word in ("risk", "opportunity", "audit", "capa", "corrective")):
        dimensions.append("business_process")
    if any(word in text for word in ("owner", "leadership", "manager")):
        dimensions.append("owner_role")
    if any(word in text for word in ("readiness", "gap")):
        dimensions.append("readiness_category")
    return sorted(set(dimensions))


def candidate(kind: str, row: dict[str, Any], ordinal: int) -> dict[str, Any]:
    title = field(row, "name", "title") or f"Untitled {kind} {ordinal}"
    description = field(row, "description", "description html")
    text = search_text(row)
    flags: list[str] = []
    if other_standard_refs(text):
        flags.append("OTHER_STANDARD_REFERENCE")
    if any(marker in text.upper() for marker in ("COPYRIGHT", "REQUIREMENT TEXT", "SHALL ")):
        flags.append("POSSIBLE_STANDARD_TEXT")
    if any(
        re.search(r"(?:prompt|response|model)", str(key), re.I) and str(value).strip()
        for key, value in row.items()
    ):
        flags.append("RAW_AI_PROMPT")
    if any("@" in str(value) for value in row.values()):
        flags.append("PERSONAL_OR_USER_DATA")
    if kind == "main":
        classification, confidence, class_flags = classify_main(row)
        eligibility = implementation_eligibility(classification, class_flags + flags)
    else:
        classification, class_flags = classify_subtask(row)
        confidence = "LOW" if classification == "NEEDS_REVIEW" else "MEDIUM"
        eligibility = "REVIEW"
    flags.extend(class_flags)
    source_stage = field(row, "stage name", "stage", "parent task name")
    content_hash = hashlib.sha256(stable_json({
        "title": title, "description": description, "classification": classification,
    }).encode()).hexdigest()
    return {
        "source_record_key": source_key(kind, row, ordinal),
        "source_stage": source_stage,
        "source_title": title,
        "classification": classification,
        "initial_implementation_candidate": eligibility,
        "proposed_phase_key": map_phase(text, classification) if kind == "main" else "REVIEW",
        "title": title,
        "objective": "",
        "why_it_matters": "",
        "guidance": description if "POSSIBLE_STANDARD_TEXT" not in flags else "",
        "implementation_steps": [] if kind == "main" else [title] if classification == "IMPLEMENTATION_STEP" else [],
        "expected_output": "",
        "evidence_expectations": [title] if classification == "EVIDENCE_EXPECTATION" else [],
        "success_criteria": [title] if classification == "SUCCESS_CRITERION" else [],
        "responsible_role": "",
        "priority": field(row, "priority") or "",
        "evidence_types": [],
        "readiness_candidate": "TRUE" if classification == "QMS_IMPLEMENTATION" else (
            "FALSE" if classification in {"PROJECT_ADMINISTRATION", "TRANSITION"} else "REVIEW"
        ),
        "external_reference_metadata": {"standard": "ISO 9001"}
        if "ISO 9001" in text.upper() and not other_standard_refs(text) else {},
        "unresolved_tags": [],
        "review_status": "REVIEW_REQUIRED" if flags or confidence == "LOW" else "UNREVIEWED",
        "review_flags": sorted(set(flags)),
        "confidence": confidence,
        "provenance": {"kind": kind, "source_stage": source_stage, "source_key_basis": "safe structural hash"},
        "content_hash": content_hash,
    }


def zip_rows(zf: zipfile.ZipFile, suffix: str) -> list[dict[str, str]]:
    name = find_member(zf, suffix)
    return read_csv(zf, name) if name else []


def normalize(source: Path, output: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    actual_sha = sha256_file(source)
    if expected_sha256 and actual_sha.lower() != expected_sha256.lower():
        raise ValueError(f"source SHA256 mismatch: expected {expected_sha256}, got {actual_sha}")
    with zipfile.ZipFile(source) as zf:
        names = sorted(name for name in zf.namelist() if not name.endswith("/"))
        projects = zip_rows(zf, "/full_archive/01_project.csv")
        main_rows = zip_rows(zf, "/full_archive/04_main_tasks.csv")
        sub_rows = zip_rows(zf, "/full_archive/05_subtasks.csv")
        stages = zip_rows(zf, "/full_archive/02_stages.csv")
        tags = zip_rows(zf, "/full_archive/03_tags.csv")
        deps = zip_rows(zf, "/full_archive/06_dependencies.csv")
        chatter = zip_rows(zf, "/full_archive/08_chatter_archive.csv")
        users = zip_rows(zf, "/full_archive/07_users_map.csv")
        manifest_member = find_member(zf, "manifest.json")
        source_manifest = read_json(zf, manifest_member) if manifest_member else {}
        raw_ai_fields = 0
        for name in names:
            if not name.endswith((".json", ".jsonl", ".csv")):
                continue
            if any(term in name.lower() for term in ("message", "chatter", "user")):
                continue
            raw = zf.read(name).decode("utf-8", errors="ignore")
            raw_ai_fields += len(re.findall(
                r"(?:ai[ _]?prompt|raw[ _]?prompt|model[ _]?response|assistant[ _]?response)", raw, re.I
            ))
    mains = [candidate("main", row, i) for i, row in enumerate(main_rows, 1)]
    subtasks = [candidate("subtask", row, i) for i, row in enumerate(sub_rows, 1)]
    all_candidates = mains + subtasks
    title_groups: dict[str, list[str]] = defaultdict(list)
    for item in all_candidates:
        key = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
        if key:
            title_groups[key].append(item["source_record_key"])
    duplicate_groups = [sorted(keys) for keys in title_groups.values() if len(keys) > 1]
    tag_rows = []
    for row in tags:
        name = field(row, "name", "tag")
        dimensions = tag_dimensions(name)
        tag_rows.append({
            "tag_key": f"tag-{hashlib.sha256(name.encode()).hexdigest()[:16]}",
            "name": name, "known_mappings": dimensions,
            "status": "KNOWN" if dimensions else "UNRESOLVED",
        })
    quarantine = [item for item in all_candidates if item["review_flags"]]
    review_queue = [item for item in all_candidates if item["confidence"] == "LOW" or item["review_flags"]]
    classification_counts = Counter(item["classification"] for item in mains)
    eligibility_counts = Counter(item["initial_implementation_candidate"] for item in mains)
    subtask_counts = Counter(item["classification"] for item in subtasks)
    flag_counts = Counter(flag for item in all_candidates for flag in item["review_flags"])
    counts = {
        "projects": len(projects), "stages": len(stages), "main_tasks": len(main_rows),
        "subtasks": len(sub_rows), "total_tasks": len(main_rows) + len(sub_rows),
        "tags": len(tags), "chatter": len(chatter), "dependencies": len(deps), "attachments": 0,
    }
    inventory = {
        "source_package_sha256": actual_sha, "archive_members": names,
        "supported_source_formats": sorted({Path(name).suffix.lower() or "<none>" for name in names}),
        "manifest": {key: value for key, value in source_manifest.items()
                     if key not in {"source_database", "source_project_id", "generated_at"}},
        "source_counts": counts,
    }
    summary = {
        "source_counts": counts,
        "main_task_classification": dict(sorted(classification_counts.items())),
        "initial_implementation_eligibility": dict(sorted(eligibility_counts.items())),
        "subtask_classification": dict(sorted(subtask_counts.items())),
        "ip_review_flags": dict(sorted(flag_counts.items())),
        "other_standard_references": flag_counts["OTHER_STANDARD_REFERENCE"],
        "transition_items": flag_counts["TRANSITION_CONTENT"],
        "raw_ai_prompts_detected": raw_ai_fields,
        "personal_source_user_data_removed": len(users) + sum(
            1 for item in all_candidates if "PERSONAL_OR_USER_DATA" in item["review_flags"]
        ),
        "duplicate_groups": len(duplicate_groups),
        "unresolved_tags": sum(1 for row in tag_rows if row["status"] == "UNRESOLVED"),
        "low_confidence_items": sum(1 for item in all_candidates if item["confidence"] == "LOW"),
    }
    normalized = {
        "schema_version": "m25.2-candidate-v1", "source_derived": True,
        "final_authored_content": False, "main_tasks": mains, "subtasks": subtasks,
    }
    content_hash = hashlib.sha256(stable_json(normalized).encode()).hexdigest()
    manifest = {
        "source_package_sha256": actual_sha, "normalizer_version": VERSION, "source_counts": counts,
        "normalized_counts": {"main_tasks": len(mains), "subtasks": len(subtasks)},
        "classification_counts": dict(sorted(classification_counts.items())),
        "quarantine_counts": {"records": len(quarantine), "flags": dict(sorted(flag_counts.items()))},
        "review_queue_count": len(review_queue), "unresolved_tag_count": summary["unresolved_tags"],
        "duplicate_group_count": len(duplicate_groups), "content_hash": content_hash,
    }
    files = {
        "inventory.json": inventory, "normalized_candidates.json": normalized,
        "classification_summary.json": summary,
        "tag_normalization.json": {"tags": tag_rows},
        "review_queue.json": {"records": review_queue},
        "quarantine.json": {"records": quarantine}, "manifest.json": manifest,
    }
    output.mkdir(parents=True, exist_ok=True)
    for filename, value in files.items():
        (output / filename).write_text(
            json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    report = [
        "M25.2 HISTORICAL METHODOLOGY NORMALIZATION",
        f"source_sha256: {actual_sha}", f"normalizer_version: {VERSION}",
    ]
    report += [f"{key}: {value}" for key, value in counts.items()]
    report += [f"main_classification.{key}: {value}" for key, value in sorted(classification_counts.items())]
    report += [f"initial_implementation.{key}: {value}" for key, value in sorted(eligibility_counts.items())]
    report += [f"subtask_classification.{key}: {value}" for key, value in sorted(subtask_counts.items())]
    report += [
        f"ip_review_items: {summary['ip_review_flags'].get('POSSIBLE_STANDARD_TEXT', 0)}",
        f"other_standard_references: {summary['other_standard_references']}",
        f"transition_items: {summary['transition_items']}",
        f"raw_ai_prompts_detected: {summary['raw_ai_prompts_detected']}",
        f"personal_source_user_data_removed: {summary['personal_source_user_data_removed']}",
        f"duplicate_groups: {summary['duplicate_groups']}",
        f"unresolved_tags: {summary['unresolved_tags']}",
        f"low_confidence_items: {summary['low_confidence_items']}",
        f"normalized_content_hash: {content_hash}",
    ]
    (output / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"source_sha256": actual_sha, "source_counts": counts, "summary": summary,
            "manifest": manifest, "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    result = normalize(args.source, args.output, args.expected_sha256)
    print(json.dumps({
        "source_sha256": result["source_sha256"], "output": result["output"],
        "source_counts": result["source_counts"],
        "normalized_content_hash": result["manifest"]["content_hash"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
