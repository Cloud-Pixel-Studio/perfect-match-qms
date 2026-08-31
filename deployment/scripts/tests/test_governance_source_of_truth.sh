#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
failures=0

check() {
  if "$@"; then
    return 0
  fi
  echo "FAIL: $*" >&2
  failures=$((failures + 1))
}

check test ! -e "$ROOT/deployment/scripts/import_plane_backlog.py"
check grep -qi "GitHub is the sole active engineering Source of Truth" "$ROOT/AGENTS.md"
check grep -qi "Do not update Plane" "$ROOT/AGENTS.md"
check test -f "$ROOT/docs/GITHUB_GOVERNANCE.md"
check grep -q "Status: RETIRED" "$ROOT/plane/README.md"
check grep -q "Authority: NONE" "$ROOT/plane/README.md"
check grep -qi "Plane updates" "$ROOT/docs/GITHUB_GOVERNANCE.md"
check grep -qi "not part of the" "$ROOT/docs/GITHUB_GOVERNANCE.md"
if grep -qi "Plane" "$ROOT/.github/PULL_REQUEST_TEMPLATE.md"; then
  echo "FAIL: PR template contains a Plane requirement" >&2
  failures=$((failures + 1))
fi

if grep -RIl --include='*.sh' --include='*.py' -E 'PLANE_API_(KEY|TOKEN)|plane\.cloudpixelstudio|import_plane' "$ROOT/deployment/scripts" | grep -v 'test_governance_source_of_truth.sh'; then
  echo "FAIL: active deployment tooling still consumes Plane integration" >&2
  failures=$((failures + 1))
fi

if (( failures )); then
  echo "github-only governance regression: FAIL ($failures checks)" >&2
  exit 1
fi
echo "github-only governance regression: PASS"
