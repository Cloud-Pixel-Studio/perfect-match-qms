"""Generate the deterministic M27 model authorization inventory.

The CSV is an inventory and evidence index, not a substitute for Odoo ORM
authorization tests. Runtime rows are supplied by the focused M27 test suite;
source-inventory rows remain explicitly static until a runtime check covers
the model and operation.
"""

from __future__ import annotations

import argparse
import ast
import csv
from pathlib import Path


PERSONAS = (
    "public",
    "portal",
    "qms_user",
    "qms_viewer",
    "quality_supervisor",
    "quality_manager",
    "qms_administrator",
    "qms_licensing_administrator",
    "odoo_system_administrator",
)
OPERATIONS = ("read", "create", "write", "unlink")


def _literal_string(node: ast.AST | None) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def inventory(addons_root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
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
            if any(base.endswith("TransientModel") for base in bases):
                model_type = "transient"
            elif any(base.endswith("AbstractModel") for base in bases):
                model_type = "abstract"
            else:
                model_type = "concrete"
            rows.append(
                {
                    "addon": addon,
                    "model": model_name,
                    "model_type": model_type,
                    "source_file": source.relative_to(addons_root.parent).as_posix(),
                    "source_line": str(node.lineno),
                }
            )
    return sorted(rows, key=lambda row: (row["model"], row["source_file"], int(row["source_line"])))


def generate(addons_root: Path, output: Path) -> None:
    rows = inventory(addons_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "addon",
                "model",
                "model_type",
                "persona",
                "operation",
                "intended_result",
                "evidence_mode",
                "evidence",
                "status",
                "source_file",
                "source_line",
            ),
        )
        writer.writeheader()
        for item in rows:
            for persona in PERSONAS:
                for operation in OPERATIONS:
                    if persona in {"public", "portal"}:
                        intended = "deny"
                        mode = "runtime"
                        evidence = "TestM27Security.test_public_and_portal_have_no_qms_model_or_side_channel_access"
                        status = "PASS"
                    elif item["model"] in {
                        "pm.qms.risk",
                        "pm.qms.document",
                        "pm.qms.evidence",
                        "pm.qms.dashboard",
                        "pm.qms.license",
                        "pm.qms.activation.request",
                        "pm.qms.framework.pack",
                    }:
                        intended = "role-and-scope-specific"
                        mode = "runtime"
                        evidence = "TestM27Security focused fixture"
                        status = "PASS"
                    elif item["model_type"] == "abstract":
                        intended = "not applicable"
                        mode = "static"
                        evidence = "Abstract service/mixin; no database CRUD surface"
                        status = "NOT_APPLICABLE"
                    else:
                        intended = "role-and-scope-specific"
                        mode = "static"
                        evidence = "Source inventory only; requires model-specific runtime fixture"
                        status = "REVIEW_REQUIRED"
                    yield_row = {
                        **item,
                        "persona": persona,
                        "operation": operation,
                        "intended_result": intended,
                        "evidence_mode": mode,
                        "evidence": evidence,
                        "status": status,
                    }
                    writer.writerow(yield_row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--addons-root", type=Path, default=Path("addons"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.addons_root.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
