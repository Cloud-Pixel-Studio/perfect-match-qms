#!/usr/bin/env python3
"""Permanent Mission 18 gate for the standalone QMS addon boundary."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


FORBIDDEN = {
    "sale",
    "sale_management",
    "purchase",
    "purchase_stock",
    "stock",
    "mrp",
    "hr",
    "account",
    "quality",
    "maintenance",
}


def read_manifest(path: Path) -> dict:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    value = ast.literal_eval(tree.body[-1].value)
    if not isinstance(value, dict):
        raise ValueError(f"Manifest is not a dictionary: {path}")
    return value


def main() -> int:
    addons_root = Path(__file__).resolve().parents[2] / "addons"
    violations: list[tuple[str, list[str]]] = []
    matrix: list[tuple[str, list[str], list[str]]] = []

    for manifest_path in sorted(addons_root.glob("*/__manifest__.py")):
        addon = manifest_path.parent.name
        manifest = read_manifest(manifest_path)
        dependencies = list(manifest.get("depends", []))
        functional = sorted(set(dependencies) & FORBIDDEN)
        odoo_dependencies = [item for item in dependencies if not item.startswith("pm_qms_")]
        qms_dependencies = [item for item in dependencies if item.startswith("pm_qms_")]
        matrix.append((addon, odoo_dependencies, qms_dependencies))
        if functional:
            violations.append((addon, functional))

    print("STANDALONE_DEPENDENCY_MATRIX")
    for addon, odoo_dependencies, qms_dependencies in matrix:
        print(
            f"{addon}: ODOO={','.join(odoo_dependencies) or '-'} "
            f"PERFECT_MATCH={','.join(qms_dependencies) or '-'}"
        )

    if violations:
        print("FUNCTIONAL_ERP_DEPENDENCIES=FOUND", file=sys.stderr)
        for addon, dependencies in violations:
            print(f"  {addon}: {', '.join(dependencies)}", file=sys.stderr)
        return 1

    print("FUNCTIONAL_ERP_DEPENDENCIES=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
