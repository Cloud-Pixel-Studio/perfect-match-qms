#!/usr/bin/env python3
"""Accidental external-standard content safety check.

This is a project hygiene check, not a legal compliance proof. It prevents
obvious mistakes such as committing licensed standard PDFs or pasted publisher
copyright blocks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRS = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}
TEXT_SUFFIXES = {".csv", ".example", ".md", ".py", ".rst", ".txt", ".xml", ".yml", ".yaml"}
PRIVATE_STANDARD_DIRS = {"standards-private", "licensed-standards"}
STANDARD_FILE_PATTERN = re.compile(r"(?i)(iso|iatf|as9100|as9120|cmmc|sae).*\.(pdf|docx?|xlsx?)$")
SUSPICIOUS_TEXT = [
    re.compile(r"(?i)copyright\s+.*international organization for standardization"),
    re.compile(r"(?i)all rights reserved\.\s+unless otherwise specified"),
    re.compile(r"(?i)iso\s+9001:2015\s*\(en\)"),
    re.compile(r"(?i)this international standard (?:specifies|promotes|is intended)"),
    re.compile(r"(?i)permission in writing from either iso"),
]


def iter_files():
    for path in ROOT.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        yield path


def main() -> int:
    findings: list[str] = []
    for path in iter_files():
        rel = path.relative_to(ROOT)
        if path.is_dir():
            if path.name in PRIVATE_STANDARD_DIRS:
                findings.append(f"{rel}: private standards directory must stay outside Git")
            continue
        if STANDARD_FILE_PATTERN.search(path.name):
            findings.append(f"{rel}: possible licensed standards document")
            continue
        if rel.as_posix() == "deployment/scripts/qms-content-safety.py":
            continue
        suffixes = {suffix.lower() for suffix in path.suffixes}
        if not suffixes.intersection(TEXT_SUFFIXES):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in SUSPICIOUS_TEXT):
                findings.append(f"{rel}:{number}: suspicious external-standard text")
    if findings:
        print("Potential external-standard content detected:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("No obvious external-standard content detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
