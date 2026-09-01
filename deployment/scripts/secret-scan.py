#!/usr/bin/env python3
"""High-confidence repository secret scan for CI and local reviews."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_DIRS = {".git", ".security-audit", "__pycache__", ".mypy_cache", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".tgz"}
PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |)PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|api[_-]?token|access[_-]?token|password|passwd|secret)\s*[:=]\s*['\"](?!__)(?!\$)[^'\"]{12,}['\"]"),
    re.compile(r"(?i)(?:api[_-]?key|api[_-]?token|access[_-]?token|password|passwd|secret)\s*=\s*(?!__)(?!\$)[A-Za-z0-9_./+@!#$%^&*=-]{16,}"),
]


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        yield path


def main() -> int:
    findings = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append(f"{path.relative_to(ROOT)}:{number}")
    if findings:
        print("Potential secrets detected:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("No high-confidence secrets detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
