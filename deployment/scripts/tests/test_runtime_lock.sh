#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOCK="$REPO_ROOT/deployment/runtime/runtime-lock.json"
CUSTOMER_SCRIPT="$REPO_ROOT/deployment/scripts/customer-instance.sh"

jq -e '
  .schema_version == 1 and
  (.odoo.image | test("^odoo:[^@]+@sha256:[0-9a-f]{64}$")) and
  (.postgres.image | test("^postgres:[^@]+@sha256:[0-9a-f]{64}$")) and
  (.alpine.image | test("^alpine:[^@]+@sha256:[0-9a-f]{64}$"))
' "$LOCK" >/dev/null

for compose_file in \
  "$REPO_ROOT/deployment/docker/customer/compose.yml.template" \
  "$REPO_ROOT/deployment/docker/dev/compose.yml" \
  "$REPO_ROOT/deployment/docker/demo/compose.yml"; do
  grep -q 'pull_policy: never' "$compose_file"
done

if grep -RInE 'image: (odoo:19\.0|postgres:15|[^[:space:]]+:latest)$' \
  "$REPO_ROOT/deployment/docker/customer" >/dev/null; then
  echo "floating customer image reference found" >&2
  exit 1
fi
if grep -nE 'odoo:19\.0|postgres:15|alpine:3\.20' "$CUSTOMER_SCRIPT" >/dev/null; then
  echo "floating customer helper image reference found" >&2
  exit 1
fi

source "$CUSTOMER_SCRIPT"
runtime_output="$(runtime_images)"
grep -q '^odoo_image=odoo:19.0@sha256:' <<<"$runtime_output"
grep -q '^postgres_image=postgres:15@sha256:' <<<"$runtime_output"
grep -q '^alpine_image=alpine:3.20@sha256:' <<<"$runtime_output"

docker() { return 1; }
if (runtime_verify_lock "$LOCK"); then
  echo "missing approved image was accepted" >&2
  exit 1
fi
unset -f docker

pulled=""
docker() {
  [[ "${1:-}" == pull ]] || { echo "unexpected docker operation" >&2; return 1; }
  pulled+="${2}"$'\n'
}
runtime_fetch
grep -q '^odoo:19.0@sha256:' <<<"$pulled"
grep -q '^postgres:15@sha256:' <<<"$pulled"
grep -q '^alpine:3.20@sha256:' <<<"$pulled"

echo "runtime lock regression: PASS"
