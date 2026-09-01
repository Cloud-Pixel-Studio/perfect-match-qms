#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$SCRIPT_DIR/customer-instance.sh"

grep -Fq 'status = env["pm.qms.license"].sudo().current_status()' "$SCRIPT"
grep -Fq 'current_status()["status"]' "$SCRIPT"
if grep -Fq 'license.state' "$SCRIPT"; then
  echo "customer operator path still uses stored license.state" >&2
  exit 1
fi

echo "customer-instance effective license status regression: PASS"
