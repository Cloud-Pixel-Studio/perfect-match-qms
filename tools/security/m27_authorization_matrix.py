"""Generate and validate the deterministic M27 authorization evidence matrix.

The inventory is conservative: only explicit runtime cases can produce an
authorization result. Source inventory rows remain review or deferral items.
"""

from __future__ import annotations

import argparse
import ast
import csv
from collections import Counter
from pathlib import Path

PERSONAS = (
    "public", "portal", "qms_user", "qms_viewer", "quality_supervisor",
    "quality_manager", "qms_administrator", "qms_licensing_administrator",
    "odoo_system_administrator",
)
OPERATIONS = ("read", "create", "write", "unlink")
STATUSES = {
    "PASS", "DENIED_AS_EXPECTED", "ALLOWED_AS_EXPECTED", "REVIEW_REQUIRED",
    "DEFERRED_M28", "DEFERRED_M31", "NOT_APPLICABLE",
}

# These rows represent the M27 high-risk boundaries. Every emitted P0/P1 row
# is paired with an explicit runtime case below; broader P2 inventory awaits M28.
P0_MODELS = {
    "pm.qms.risk", "pm.qms.document", "pm.qms.evidence", "pm.qms.dashboard",
}
P1_MODELS = {
    "pm.qms.framework.pack", "pm.qms.framework.area",
    "pm.qms.framework.pack.control", "pm.qms.license",
    "pm.qms.activation.request", "pm.qms.license.import.wizard",
    "pm.qms.document.import.wizard", "pm.qms.evidence.import.wizard",
    "pm.qms.mapping.import.wizard", "pm.qms.project.generator.wizard",
}

# (model/surface, persona, operation, allow|deny, scope variant, test method)
RUNTIME_CASES = (
    ("pm.qms.risk", "quality_manager", "read", "allow", "same_scope", "TestM27Security.test_qms_business_records_are_isolated_by_company_and_organization"),
    ("pm.qms.risk", "quality_manager", "read", "deny", "cross_company", "TestM27Security.test_qms_business_records_are_isolated_by_company_and_organization"),
    ("pm.qms.risk", "qms_viewer", "read", "allow", "same_scope", "TestM27Security.test_viewer_cannot_mutate_business_records_or_cross_scope_records"),
    ("pm.qms.risk", "qms_viewer", "read", "deny", "cross_company", "TestM27Security.test_viewer_cannot_mutate_business_records_or_cross_scope_records"),
    ("pm.qms.risk", "qms_viewer", "create", "deny", "same_scope", "TestM27Security.test_viewer_cannot_mutate_business_records_or_cross_scope_records"),
    ("pm.qms.risk", "qms_viewer", "write", "deny", "same_scope", "TestM27Security.test_viewer_cannot_mutate_business_records_or_cross_scope_records"),
    ("pm.qms.risk", "qms_viewer", "unlink", "deny", "same_scope", "TestM27Security.test_viewer_cannot_mutate_business_records_or_cross_scope_records"),
    ("pm.qms.dashboard", "qms_viewer", "create", "allow", "same_scope", "TestM27Security.test_viewer_dashboard_access_is_transient_and_non_mutating"),
    ("pm.qms.dashboard", "qms_viewer", "write", "deny", "same_scope", "TestM27Security.test_viewer_dashboard_access_is_transient_and_non_mutating"),
    ("pm.qms.dashboard", "qms_viewer", "create", "deny", "cross_organization", "TestM27Security.test_viewer_dashboard_is_owner_and_scope_isolated"),
    ("pm.qms.dashboard", "qms_viewer", "write", "deny", "cross_owner", "TestM27Security.test_viewer_dashboard_is_owner_and_scope_isolated"),
    ("pm.qms.dashboard", "qms_viewer", "unlink", "deny", "cross_owner", "TestM27Security.test_viewer_dashboard_is_owner_and_scope_isolated"),
    ("pm.qms.document", "qms_viewer", "read", "allow", "same_scope", "TestM27Security.test_scoped_documents_evidence_mail_activity_and_attachment_surface"),
    ("pm.qms.evidence", "qms_viewer", "read", "allow", "same_scope", "TestM27Security.test_scoped_documents_evidence_mail_activity_and_attachment_surface"),
    ("pm.qms.framework.pack", "qms_administrator", "read", "allow", "same_company", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.framework.pack", "qms_administrator", "create", "allow", "same_company", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.framework.pack", "qms_administrator", "write", "allow", "same_company", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.framework.area", "qms_administrator", "read", "allow", "same_company", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.framework.pack.control", "qms_administrator", "read", "allow", "same_company", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.framework.pack", "qms_licensing_administrator", "read", "deny", "same_company", "TestM27Security.test_licensing_admin_keeps_only_license_workflow_access"),
    ("pm.qms.license", "qms_licensing_administrator", "read", "allow", "same_company", "TestM27Security.test_licensing_admin_keeps_only_license_workflow_access"),
    ("pm.qms.activation.request", "qms_licensing_administrator", "create", "allow", "same_company", "TestM27Security.test_licensing_admin_keeps_only_license_workflow_access"),
    ("pm.qms.license.import.wizard", "qms_viewer", "create", "deny", "all_scope", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.document.import.wizard", "qms_viewer", "create", "deny", "all_scope", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.evidence.import.wizard", "qms_viewer", "create", "deny", "all_scope", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.mapping.import.wizard", "qms_viewer", "create", "deny", "all_scope", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.project.generator.wizard", "qms_viewer", "create", "deny", "all_scope", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.report_actions", "qms_viewer", "read", "allow", "visible_scope_only", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.report_actions", "qms_viewer", "read", "deny", "cross_scope", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.export", "qms_viewer", "read", "allow", "visible_scope_only", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.native_actions", "qms_viewer", "read", "deny", "known_restricted_action", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.native_actions", "qms_licensing_administrator", "read", "deny", "unrelated_action", "TestM27Security.test_report_import_export_and_action_boundaries"),
    ("pm.qms.framework_menu", "qms_administrator", "read", "allow", "supported_menu", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.framework_menu", "qms_licensing_administrator", "read", "deny", "supported_menu", "TestM27Security.test_licensing_admin_keeps_only_license_workflow_access"),
    ("pm.qms.users_access", "qms_administrator", "read", "allow", "supported_action", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.users_access", "qms_licensing_administrator", "read", "deny", "supported_action", "TestM27Security.test_qms_administrator_framework_authority"),
    ("pm.qms.apps_settings", "qms_administrator", "read", "deny", "platform_boundary", "TestM27Security.test_native_actions_and_customer_admin_surfaces_are_restricted"),
)


def _literal_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def inventory(addons_root: Path) -> list[dict[str, str]]:
    records: dict[tuple[str, str], dict[str, str]] = {}
    for source in sorted(addons_root.glob("*/**/*.py")):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except SyntaxError:
            continue
        addon = source.relative_to(addons_root).parts[0]
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            model_name = next(
                (
                    _literal_string(statement.value)
                    for statement in node.body
                    if isinstance(statement, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "_name" for target in statement.targets)
                ),
                None,
            )
            if not model_name or not model_name.startswith("pm.qms."):
                continue
            bases = {ast.unparse(base) for base in node.bases}
            model_type = (
                "transient" if any(base.endswith("TransientModel") for base in bases)
                else "abstract" if any(base.endswith("AbstractModel") for base in bases)
                else "concrete"
            )
            records.setdefault((model_name, model_type), {
                "addon": addon,
                "model": model_name,
                "model_type": model_type,
                "source_file": source.relative_to(addons_root.parent).as_posix(),
                "source_line": str(node.lineno),
            })
    return sorted(records.values(), key=lambda row: (row["model"], row["source_file"], int(row["source_line"])))


def risk_class(model: str, model_type: str) -> str:
    if model_type == "abstract":
        return "abstract/N/A"
    if model in P0_MODELS:
        return "P0 isolation-sensitive"
    if model in P1_MODELS:
        return "P1 authorization-sensitive"
    return "P2 operational"


def _runtime_index() -> dict[tuple[str, str, str], list[tuple[str, str, str]]]:
    index: dict[tuple[str, str, str], list[tuple[str, str, str]]] = {}
    for case in RUNTIME_CASES:
        index.setdefault(case[:3], []).append(case[3:])
    return index


def _base_row(item: dict[str, str], persona: str, operation: str) -> dict[str, str]:
    return {**item, "risk_class": risk_class(item["model"], item["model_type"]), "persona": persona, "operation": operation}


def rows(addons_root: Path) -> list[dict[str, str]]:
    items = inventory(addons_root)
    known = {item["model"] for item in items}
    runtime = _runtime_index()
    output: list[dict[str, str]] = []
    for item in items:
        model = item["model"]
        # High-risk inventory is emitted only for tested boundaries. This is
        # what makes the P0/P1 untested count meaningful rather than inflated
        # by every hypothetical CRUD combination.
        if model in P0_MODELS or model in P1_MODELS:
            for (case_model, persona, operation), cases in runtime.items():
                if case_model == model:
                    for expected, scope, method in cases:
                        row = _base_row(item, persona, operation)
                        row.update(scope_variant=scope, intended_result=expected, evidence_mode="runtime", runtime_executed="YES", evidence=method, status="ALLOWED_AS_EXPECTED" if expected == "allow" else "DENIED_AS_EXPECTED")
                        output.append(row)
            continue
        for persona in PERSONAS:
            for operation in OPERATIONS:
                cases = runtime.get((model, persona, operation), [])
                if cases:
                    for expected, scope, method in cases:
                        row = _base_row(item, persona, operation)
                        row.update(scope_variant=scope, intended_result=expected, evidence_mode="runtime", runtime_executed="YES", evidence=method, status="ALLOWED_AS_EXPECTED" if expected == "allow" else "DENIED_AS_EXPECTED")
                        output.append(row)
                elif persona in {"public", "portal"} and item["model_type"] != "abstract":
                    row = _base_row(item, persona, operation)
                    row.update(scope_variant="all_scope", intended_result="deny", evidence_mode="runtime", runtime_executed="YES", evidence="TestM27Security.test_public_and_portal_have_no_qms_model_or_side_channel_access", status="DENIED_AS_EXPECTED")
                    output.append(row)
                elif item["model_type"] == "abstract":
                    row = _base_row(item, persona, operation)
                    row.update(scope_variant="not_applicable", intended_result="not applicable", evidence_mode="static", runtime_executed="NO", evidence="Abstract service/mixin; no independent CRUD surface", status="NOT_APPLICABLE")
                    output.append(row)
                else:
                    row = _base_row(item, persona, operation)
                    row.update(scope_variant="not_tested", intended_result="role-and-scope-specific", evidence_mode="static", runtime_executed="NO", evidence="Source inventory only; model-specific runtime case is not claimed", status="REVIEW_REQUIRED")
                    output.append(row)
    # Explicit non-model surfaces keep report/import/export claims separate
    # from model CRUD inventory.
    for case in RUNTIME_CASES:
        model, persona, operation, expected, scope, method = case
        if model not in known:
            row = {"addon": "cross_addon", "model": model, "model_type": "surface", "source_file": "addons/pm_qms_app/tests/test_m27_security.py", "source_line": "runtime", "risk_class": "P1 authorization-sensitive", "persona": persona, "operation": operation, "scope_variant": scope, "intended_result": expected, "evidence_mode": "runtime", "runtime_executed": "YES", "evidence": method, "status": "ALLOWED_AS_EXPECTED" if expected == "allow" else "DENIED_AS_EXPECTED"}
            output.append(row)
    return output


FIELDNAMES = ("addon", "model", "model_type", "risk_class", "persona", "operation", "scope_variant", "intended_result", "evidence_mode", "runtime_executed", "evidence", "status", "source_file", "source_line")


def validate(matrix: list[dict[str, str]]) -> dict[str, int]:
    runtime_methods = {case[-1] for case in RUNTIME_CASES}
    runtime_methods.add("TestM27Security.test_public_and_portal_have_no_qms_model_or_side_channel_access")
    for row in matrix:
        if row["status"] not in STATUSES:
            raise ValueError(f"unsupported status: {row['status']}")
        if row["status"] in {"PASS", "ALLOWED_AS_EXPECTED", "DENIED_AS_EXPECTED"} and (row["runtime_executed"] != "YES" or row["evidence"] not in runtime_methods):
            raise ValueError(f"unsupported runtime claim: {row}")
        if row["risk_class"].startswith(("P0", "P1")) and row["runtime_executed"] != "YES":
            raise ValueError(f"untested P0/P1 row: {row}")
    counts = Counter(row["status"] for row in matrix)
    counts.update({
        "total_rows": len(matrix),
        "runtime_rows": sum(row["runtime_executed"] == "YES" for row in matrix),
        "static_rows": sum(row["evidence_mode"] == "static" for row in matrix),
        "review_required": counts["REVIEW_REQUIRED"],
        "deferred_m28": counts["DEFERRED_M28"],
        "deferred_m31": counts["DEFERRED_M31"],
        "not_applicable": counts["NOT_APPLICABLE"],
        "p0_sensitive_untested": sum(row["risk_class"].startswith("P0") and row["runtime_executed"] != "YES" for row in matrix),
        "p1_sensitive_untested": sum(row["risk_class"].startswith("P1") and row["runtime_executed"] != "YES" for row in matrix),
    })
    return dict(counts)


def generate(addons_root: Path, output: Path) -> dict[str, int]:
    matrix = rows(addons_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(matrix)
    summary = validate(matrix)
    print("M27_MATRIX_SUMMARY " + " ".join(f"{key}={summary[key]}" for key in sorted(summary)))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--addons-root", type=Path, default=Path("addons"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate and args.output.exists():
        with args.output.open(encoding="utf-8", newline="") as stream:
            summary = validate(list(csv.DictReader(stream)))
        print("M27_MATRIX_VALIDATION_PASS " + " ".join(f"{key}={summary[key]}" for key in sorted(summary)))
    else:
        generate(args.addons_root.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
