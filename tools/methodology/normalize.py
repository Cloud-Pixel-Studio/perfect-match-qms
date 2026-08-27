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
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

VERSION = "m25.2.1"
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
OTHER_STANDARDS = (
    "ISO 14001", "ISO 19011", "ISO 45001", "AS9100", "AS9120", "IATF", "CMMC",
)
TRANSITION_STAGE = "iso 9001:2026 transition readiness"
STAGE_CLASSIFICATION = {
    "project initiation": "PROJECT_ADMINISTRATION",
    "context of the organization": "QMS_IMPLEMENTATION",
    "gap assessment": "READINESS_ASSESSMENT",
    "process mapping": "QMS_IMPLEMENTATION",
    "documentation development": "QMS_IMPLEMENTATION",
    "implementation": "QMS_IMPLEMENTATION",
    "internal audit": "QMS_IMPLEMENTATION",
    "corrective actions": "GAP_REMEDIATION",
    "management review": "QMS_IMPLEMENTATION",
    "certification preparation": "CERTIFICATION_PREPARATION",
    "project closure": "PROJECT_ADMINISTRATION",
    "leadership and qms planning": "QMS_IMPLEMENTATION",
    TRANSITION_STAGE: "TRANSITION",
}
SENSITIVE_FIELD = re.compile(
    r"(?:email|author|user|login|avatar|password|token|database|server|"
    r"environment|created|updated|timestamp|date|follower|subscriber|"
    r"message|chatter|prompt|response|model|source.?id|record.?id|company|"
    r"customer|attachment|technical)", re.I,
)
HTML_TAG = re.compile(r"<[^>]+>")
SOURCE_ID = re.compile(r"\b(?:old|source|record|task|main|sub)-[\w-]+\b", re.I)


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
    text = re.sub(r"\b(?:https?://|ssh://)\S+", "[REDACTED_URI]", text, flags=re.I)
    return SOURCE_ID.sub("[REDACTED_SOURCE_KEY]", text)


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


def row_title(row: dict[str, Any]) -> str:
    return field(row, "name", "title", "task name")


def row_stage(row: dict[str, Any]) -> str:
    return field(row, "stage name", "stage")


def row_description(row: dict[str, Any]) -> str:
    return field(row, "description", "description html")


def row_tags(row: dict[str, Any]) -> str:
    return field(row, "tags", "tag")


def source_key(kind: str, row: dict[str, Any], ordinal: int) -> str:
    structural = {
        "kind": kind, "ordinal": ordinal, "stage": row_stage(row),
        "title": row_title(row), "sequence": field(row, "sequence"),
    }
    digest = hashlib.sha256(stable_json(structural).encode()).hexdigest()
    return f"src-{digest[:20]}"


def search_text(row: dict[str, Any]) -> str:
    """Return safe metadata for diagnostics, not classification precedence."""
    return " ".join(
        safe_value(value).lower()
        for key, value in row.items()
        if not SENSITIVE_FIELD.search(str(key))
    )


def authoritative_text(row: dict[str, Any]) -> str:
    return " ".join(value.lower() for value in (row_title(row), row_description(row), row_tags(row)) if value)


def other_standard_refs(text: str) -> list[str]:
    upper = text.upper()
    return [standard for standard in OTHER_STANDARDS if re.search(rf"\b{re.escape(standard)}\b", upper)]


def transition_evidence(stage: str, title: str, description: str) -> tuple[bool, str]:
    stage_key = normalize_text(stage).lower()
    title_key = normalize_text(title).lower()
    description_key = normalize_text(description).lower()
    if stage_key == TRANSITION_STAGE:
        return True, "stage_name"
    if re.search(r"\b(?:transition|migration|migrating)\b", title_key):
        return True, "title"
    if re.search(r"\b(?:edition change|revision transition|new edition|version migration)\b", title_key):
        return True, "title"
    if (
        re.search(r"\b(?:transition|migration|migrating)\b", description_key)
        and re.search(r"\b(?:from|to|edition|revision|version)\b", description_key)
        and re.search(r"\b(?:standard|edition|revision|version)\b", description_key)
        and re.search(r"\b(?:from .{0,80} to|new edition|edition change|revision change|migrat)", description_key)
    ):
        return True, "description"
    return False, ""


def classify_main(row: dict[str, Any]) -> tuple[str, str, list[str]]:
    stage = row_stage(row)
    title = row_title(row)
    description = row_description(row)
    semantic = authoritative_text(row)
    flags: list[str] = []
    if other_standard_refs(semantic):
        flags.append("OTHER_STANDARD_REFERENCE")
    is_transition, trigger = transition_evidence(stage, title, description)
    if is_transition:
        return "TRANSITION", "HIGH", flags + ["TRANSITION_CONTENT", f"TRANSITION_TRIGGER_{trigger.upper()}"]
    stage_class = STAGE_CLASSIFICATION.get(normalize_text(stage).lower())
    if stage_class:
        if stage_class == "READINESS_ASSESSMENT" and re.search(r"\bremediat|corrective gap\b", semantic):
            return "GAP_REMEDIATION", "MEDIUM", flags
        if stage_class == "QMS_IMPLEMENTATION" and re.search(r"\bcertif(?:ication|y)|external audit\b", semantic):
            return "CERTIFICATION_PREPARATION", "MEDIUM", flags
        return stage_class, "HIGH", flags
    if any(word in semantic for word in ("kickoff", "kick-off", "schedule", "meeting", "logistics", "project closure")):
        return "PROJECT_ADMINISTRATION", "MEDIUM", flags + ["ADMINISTRATIVE_ONLY"]
    if any(word in semantic for word in ("certification", "external audit", "certification readiness")):
        return "CERTIFICATION_PREPARATION", "MEDIUM", flags
    if any(word in semantic for word in ("gap assessment", "readiness assessment", "maturity assessment")):
        return "READINESS_ASSESSMENT", "MEDIUM", flags
    if any(word in semantic for word in ("gap remediation", "remediate gap", "corrective gap")):
        return "GAP_REMEDIATION", "MEDIUM", flags
    if any(word in semantic for word in ("quality", "process", "procedure", "risk", "context", "objective", "kpi", "competenc", "document", "audit", "corrective", "supplier", "customer", "control")):
        return "QMS_IMPLEMENTATION", "MEDIUM", flags
    return "NEEDS_REVIEW", "LOW", flags + ["AMBIGUOUS_CLASSIFICATION"]


def implementation_eligibility(category: str, flags: Iterable[str]) -> str:
    flag_set = set(flags)
    if category == "QMS_IMPLEMENTATION" and not flag_set & {"OTHER_STANDARD_REFERENCE", "POSSIBLE_STANDARD_TEXT"}:
        return "YES"
    if category in {"PROJECT_ADMINISTRATION", "READINESS_ASSESSMENT", "CERTIFICATION_PREPARATION", "TRANSITION", "GAP_REMEDIATION"}:
        return "NO"
    return "REVIEW"


def map_phase(text: str, category: str) -> str:
    rules = (
        ("P01", ("setup", "governance", "kickoff")), ("P02", ("context", "scope", "interested party")),
        ("P03", ("process", "workflow", "architecture")), ("P04", ("leadership", "responsib", "role")),
        ("P05", ("risk", "planning", "change")), ("P06", ("objective", "kpi", "resource")),
        ("P07", ("competenc", "training", "awareness", "communication")), ("P08", ("document", "record", "information")),
        ("P09", ("operation", "procedure", "control")), ("P10", ("customer", "supplier", "purchas")),
        ("P11", ("measure", "monitor", "performance", "metric")), ("P12", ("audit", "corrective", "ncr", "improvement")),
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


def classify_subtask(row: dict[str, Any], parent_category: str, parent_stage: str) -> tuple[str, str, list[str]]:
    title = row_title(row)
    title_key = title.lower()
    description = row_description(row)
    flags: list[str] = []
    if other_standard_refs(authoritative_text(row)):
        flags.append("OTHER_STANDARD_REFERENCE")
    if transition_evidence(parent_stage, title, description)[0]:
        flags.append("TRANSITION_CONTENT")
    if parent_category == "PROJECT_ADMINISTRATION" or any(word in title_key for word in ("meeting", "logistics", "schedule", "kickoff", "communication cadence")):
        return "PROJECT_ADMINISTRATION", "HIGH", flags + ["ADMINISTRATIVE_ONLY"]
    if re.search(r"\bdepends? on\b|\bdependency\b|\bprerequisite\b", title_key):
        return "DEPENDENCY", "MEDIUM", flags
    if re.search(r"success criterion|acceptance criteria|successful|effectiveness", title_key):
        return "SUCCESS_CRITERION", "HIGH", flags
    if re.search(r"evidence|record|proof|retain|verify|validate|confirm", title_key):
        return "EVIDENCE_EXPECTATION", "MEDIUM", flags
    if re.search(r"deliverable|output|submit|produce", title_key):
        return "DELIVERABLE", "HIGH", flags
    if re.search(r"next action|follow[- ]up|next step|action item", title_key):
        return "NEXT_ACTION", "MEDIUM", flags
    if re.search(r"guidance|explain|how to|consider|reference|note", title_key):
        return "GUIDANCE", "MEDIUM", flags
    if re.search(r"implement|configure|create|define|establish|review|identify|assess|prepare|document|develop|map|conduct|perform|collect|monitor|assign", title_key):
        return "IMPLEMENTATION_STEP", "MEDIUM", flags
    if title_key.strip():
        return "NEEDS_REVIEW", "LOW", flags + ["AMBIGUOUS_CLASSIFICATION"]
    return "IGNORE_ARCHIVE", "HIGH", flags


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
    if "iso 9001" in text:
        dimensions.append("standard_reference_metadata")
    return sorted(set(dimensions))


def candidate(kind: str, row: dict[str, Any], ordinal: int, parent: dict[str, Any] | None = None) -> dict[str, Any]:
    title = row_title(row) or f"Untitled {kind} {ordinal}"
    description = row_description(row)
    semantic = authoritative_text(row)
    flags: list[str] = []
    if other_standard_refs(semantic):
        flags.append("OTHER_STANDARD_REFERENCE")
    if any(marker in semantic.upper() for marker in ("COPYRIGHT", "REQUIREMENT TEXT", "SHALL ")):
        flags.append("POSSIBLE_STANDARD_TEXT")
    if any(re.search(r"(?:prompt|response|model)", str(key), re.I) and str(value).strip() for key, value in row.items()):
        flags.append("RAW_AI_PROMPT")
    if any("@" in str(value) for value in row.values()):
        flags.append("PERSONAL_OR_USER_DATA")
    if kind == "main":
        classification, confidence, class_flags = classify_main(row)
        eligibility = implementation_eligibility(classification, class_flags + flags)
    else:
        parent_category = parent["classification"] if parent else "NEEDS_REVIEW"
        parent_stage = parent["source_stage"] if parent else row_stage(row)
        classification, confidence, class_flags = classify_subtask(row, parent_category, parent_stage)
        useful = classification not in {"IGNORE_ARCHIVE", "PROJECT_ADMINISTRATION"}
        eligibility = "NO" if parent_category in {"PROJECT_ADMINISTRATION", "TRANSITION", "CERTIFICATION_PREPARATION"} else ("YES" if useful else "REVIEW")
    flags.extend(class_flags)
    stage = row_stage(row)
    content_hash = hashlib.sha256(stable_json({"title": title, "description": description, "classification": classification}).encode()).hexdigest()
    item = {
        "source_record_key": source_key(kind, row, ordinal), "source_stage": stage, "source_title": title,
        "classification": classification, "initial_implementation_candidate": eligibility,
        "proposed_phase_key": map_phase(semantic, classification) if kind == "main" else "REVIEW",
        "title": title, "objective": "", "why_it_matters": "",
        "guidance": description if "POSSIBLE_STANDARD_TEXT" not in flags else "",
        "implementation_steps": [title] if classification == "IMPLEMENTATION_STEP" else [],
        "expected_output": title if classification == "DELIVERABLE" else "",
        "evidence_expectations": [title] if classification == "EVIDENCE_EXPECTATION" else [],
        "success_criteria": [title] if classification == "SUCCESS_CRITERION" else [],
        "responsible_role": "", "priority": field(row, "priority") or "", "evidence_types": [],
        "readiness_candidate": (
            "FALSE" if classification in {"PROJECT_ADMINISTRATION", "TRANSITION", "IGNORE_ARCHIVE"} or (parent and parent["classification"] == "TRANSITION")
            else ("TRUE" if classification in {"QMS_IMPLEMENTATION", "IMPLEMENTATION_STEP", "EVIDENCE_EXPECTATION", "SUCCESS_CRITERION", "DELIVERABLE"} else "REVIEW")
        ),
        "external_reference_metadata": {"standard": "ISO 9001"} if "ISO 9001" in semantic.upper() and not other_standard_refs(semantic) else {},
        "unresolved_tags": [], "review_status": "REVIEW_REQUIRED" if flags or confidence == "LOW" else "UNREVIEWED",
        "review_flags": sorted(set(flags)), "confidence": confidence,
        "provenance": {"kind": kind, "source_stage": stage, "source_key_basis": "safe structural hash"},
        "content_hash": content_hash,
    }
    if parent:
        item["parent_source_record_key"] = parent["source_record_key"]
        item["parent_classification"] = parent["classification"]
        item["parent_stage"] = parent["source_stage"]
        item["provenance"]["parent_source_record_key"] = parent["source_record_key"]
    return item


def zip_rows(zf: zipfile.ZipFile, suffix: str) -> list[dict[str, str]]:
    name = find_member(zf, suffix)
    return read_csv(zf, name) if name else []


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def duplicate_groups(items: list[dict[str, Any]]) -> list[list[str]]:
    groups: set[tuple[str, ...]] = set()
    by_title: dict[str, list[str]] = defaultdict(list)
    by_content: dict[str, list[str]] = defaultdict(list)
    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_title[normalized_title(item["title"])].append(item["source_record_key"])
        by_content[item["content_hash"]].append(item["source_record_key"])
        by_stage[normalized_title(item["source_stage"])].append(item)
    for collection in (by_title, by_content):
        for keys in collection.values():
            if len(keys) > 1:
                groups.add(tuple(sorted(keys)))
    for stage_items in by_stage.values():
        for index, left in enumerate(stage_items):
            left_title = normalized_title(left["title"])
            for right in stage_items[index + 1 :]:
                right_title = normalized_title(right["title"])
                if left_title != right_title and SequenceMatcher(None, left_title, right_title).ratio() >= 0.92:
                    groups.add(tuple(sorted((left["source_record_key"], right["source_record_key"]))))
    return [list(group) for group in sorted(groups)]


def transition_trigger_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    fields = {
        "stage_name": lambda row: row_stage(row), "title": lambda row: row_title(row),
        "description": lambda row: row_description(row), "tag": lambda row: row_tags(row),
        "other": lambda row: search_text(row),
    }
    return {name: sum(bool(re.search(r"\b(?:transition|2026)\b", getter(row), re.I)) for row in rows) for name, getter in fields.items()}


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
            if not name.endswith((".json", ".jsonl", ".csv")) or any(term in name.lower() for term in ("message", "chatter", "user")):
                continue
            raw = zf.read(name).decode("utf-8", errors="ignore")
            raw_ai_fields += len(re.findall(r"(?:ai[ _]?prompt|raw[ _]?prompt|model[ _]?response|assistant[ _]?response)", raw, re.I))
    mains = [candidate("main", row, index) for index, row in enumerate(main_rows, 1)]
    parents = {(normalized_title(row_stage(row)), normalized_title(row_title(row))): item for row, item in zip(main_rows, mains)}
    subtasks = []
    for index, row in enumerate(sub_rows, 1):
        parent = parents.get((normalized_title(row_stage(row)), normalized_title(field(row, "parent task name", "parent task"))))
        subtasks.append(candidate("subtask", row, index, parent))
    all_candidates = mains + subtasks
    groups = duplicate_groups(all_candidates)
    grouped_keys = {key for group in groups for key in group}
    for item in all_candidates:
        if item["source_record_key"] in grouped_keys:
            item["review_flags"] = sorted(set(item["review_flags"]) | {"DUPLICATE_CONTENT"})
            item["review_status"] = "REVIEW_REQUIRED"
    tag_rows = []
    for row in tags:
        name = field(row, "name", "tag")
        dimensions = tag_dimensions(name)
        tag_rows.append({"tag_key": f"tag-{hashlib.sha256(name.encode()).hexdigest()[:16]}", "name": name, "known_mappings": dimensions, "status": "KNOWN" if dimensions else "UNRESOLVED"})
    quarantine = [item for item in all_candidates if item["review_flags"]]
    review_queue = [item for item in all_candidates if item["confidence"] == "LOW" or item["review_flags"]]
    classification_counts = Counter(item["classification"] for item in mains)
    eligibility_counts = Counter(item["initial_implementation_candidate"] for item in mains)
    subtask_counts = Counter(item["classification"] for item in subtasks)
    flag_counts = Counter(flag for item in all_candidates for flag in item["review_flags"])
    counts = {"projects": len(projects), "stages": len(stages), "main_tasks": len(main_rows), "subtasks": len(sub_rows), "total_tasks": len(main_rows) + len(sub_rows), "tags": len(tags), "chatter": len(chatter), "dependencies": len(deps), "attachments": 0}
    source_stage_counts = dict(sorted(Counter(row_stage(row) for row in main_rows).items()))
    inventory = {"source_package_sha256": actual_sha, "archive_members": names, "supported_source_formats": sorted({Path(name).suffix.lower() or "<none>" for name in names}), "manifest": {key: value for key, value in source_manifest.items() if key not in {"source_database", "source_project_id", "generated_at"}}, "source_counts": counts, "source_stage_counts": source_stage_counts}
    summary = {
        "source_counts": counts, "source_stage_counts": source_stage_counts,
        "main_task_classification": dict(sorted(classification_counts.items())), "initial_implementation_eligibility": dict(sorted(eligibility_counts.items())), "subtask_classification": dict(sorted(subtask_counts.items())), "ip_review_flags": dict(sorted(flag_counts.items())), "other_standard_references": flag_counts["OTHER_STANDARD_REFERENCE"], "transition_items": flag_counts["TRANSITION_CONTENT"], "transition_trigger_field_counts": {"main": transition_trigger_counts(main_rows), "subtasks": transition_trigger_counts(sub_rows)}, "raw_ai_prompts_detected": raw_ai_fields, "personal_source_user_data_removed": len(users) + sum(1 for item in all_candidates if "PERSONAL_OR_USER_DATA" in item["review_flags"]), "duplicate_groups": len(groups), "unresolved_tags": sum(1 for row in tag_rows if row["status"] == "UNRESOLVED"), "low_confidence_items": sum(1 for item in all_candidates if item["confidence"] == "LOW"),
        "distribution_warnings": {"main_category_over_80_percent": max(classification_counts.values(), default=0) > len(mains) * 0.8, "subtasks_over_90_percent_ignore_archive": subtask_counts["IGNORE_ARCHIVE"] > len(subtasks) * 0.9, "no_semantic_subtasks": not any(category in subtask_counts for category in SUBTASK_CATEGORIES if category not in {"IGNORE_ARCHIVE", "NEEDS_REVIEW"})},
    }
    normalized = {"schema_version": "m25.2-candidate-v1", "source_derived": True, "final_authored_content": False, "main_tasks": mains, "subtasks": subtasks}
    content_hash = hashlib.sha256(stable_json(normalized).encode()).hexdigest()
    manifest = {"source_package_sha256": actual_sha, "normalizer_version": VERSION, "source_counts": counts, "normalized_counts": {"main_tasks": len(mains), "subtasks": len(subtasks)}, "classification_counts": dict(sorted(classification_counts.items())), "quarantine_counts": {"records": len(quarantine), "flags": dict(sorted(flag_counts.items()))}, "review_queue_count": len(review_queue), "unresolved_tag_count": summary["unresolved_tags"], "duplicate_group_count": len(groups), "content_hash": content_hash}
    files = {"inventory.json": inventory, "normalized_candidates.json": normalized, "classification_summary.json": summary, "tag_normalization.json": {"tags": tag_rows}, "review_queue.json": {"records": review_queue}, "quarantine.json": {"records": quarantine}, "manifest.json": manifest}
    output.mkdir(parents=True, exist_ok=True)
    for filename, value in files.items():
        (output / filename).write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = ["M25.2 HISTORICAL METHODOLOGY NORMALIZATION", f"source_sha256: {actual_sha}", f"normalizer_version: {VERSION}"]
    report += [f"{key}: {value}" for key, value in counts.items()]
    report += [f"source_stage.{key}: {value}" for key, value in sorted(source_stage_counts.items())]
    report += [f"main_classification.{key}: {value}" for key, value in sorted(classification_counts.items())]
    report += [f"initial_implementation.{key}: {value}" for key, value in sorted(eligibility_counts.items())]
    report += [f"subtask_classification.{key}: {value}" for key, value in sorted(subtask_counts.items())]
    report += [f"transition_triggers.{scope}.{key}: {value}" for scope, values in summary["transition_trigger_field_counts"].items() for key, value in sorted(values.items())]
    report += [f"ip_review_items: {summary['ip_review_flags'].get('POSSIBLE_STANDARD_TEXT', 0)}", f"other_standard_references: {summary['other_standard_references']}", f"transition_items: {summary['transition_items']}", f"raw_ai_prompts_detected: {summary['raw_ai_prompts_detected']}", f"personal_source_user_data_removed: {summary['personal_source_user_data_removed']}", f"duplicate_groups: {summary['duplicate_groups']}", f"unresolved_tags: {summary['unresolved_tags']}", f"low_confidence_items: {summary['low_confidence_items']}", f"distribution_warnings: {summary['distribution_warnings']}", f"normalized_content_hash: {content_hash}"]
    (output / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return {"source_sha256": actual_sha, "source_counts": counts, "summary": summary, "manifest": manifest, "output": str(output)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    result = normalize(args.source, args.output, args.expected_sha256)
    print(json.dumps({"source_sha256": result["source_sha256"], "output": result["output"], "source_counts": result["source_counts"], "normalized_content_hash": result["manifest"]["content_hash"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
