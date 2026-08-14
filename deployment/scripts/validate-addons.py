#!/usr/bin/env python3
"""Validate local Odoo addon manifests and XML data files."""

from __future__ import annotations

import ast
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"
REQUIRED_MANIFEST_KEYS = {"name", "version", "depends", "data", "installable"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def manifest(path: Path) -> dict:
    try:
        data = ast.literal_eval(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(f"{path}: invalid Python literal manifest: {exc}")
    missing = REQUIRED_MANIFEST_KEYS - set(data)
    if missing:
        fail(f"{path}: missing manifest keys {sorted(missing)}")
    if not isinstance(data["depends"], list):
        fail(f"{path}: depends must be a list")
    if not isinstance(data["data"], list):
        fail(f"{path}: data must be a list")
    return data


def validate_xml(path: Path) -> None:
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        fail(f"{path}: invalid XML: {exc}")


def validate_csv(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        fail(f"{path}: CSV file is empty")
    if "id" not in rows[0]:
        fail(f"{path}: CSV header must include id")


def main() -> int:
    addon_count = 0
    for addon in sorted(ADDONS.iterdir()):
        manifest_path = addon / "__manifest__.py"
        if not manifest_path.exists():
            continue
        addon_count += 1
        data = manifest(manifest_path)
        for rel_path in [*data.get("data", []), *data.get("demo", [])]:
            path = addon / rel_path
            if not path.exists():
                fail(f"{manifest_path}: referenced file does not exist: {rel_path}")
            if path.suffix == ".xml":
                validate_xml(path)
            elif path.suffix == ".csv":
                validate_csv(path)
    if not addon_count:
        fail("no installable addon manifests found")
    print(f"Validated {addon_count} addon manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
