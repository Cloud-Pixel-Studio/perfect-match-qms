#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$SCRIPT_DIR/customer-instance.sh"
TEST_ROOT="$(mktemp -d)"
TEST_RELEASE="v99.99.99-rc0"
SLUG="rc10-upgrade-fixture-test"
INSTANCE_ROOT="$TEST_ROOT/instances/$SLUG"
export PMQMS_CUSTOMER_INSTANCE_ROOT="$TEST_ROOT/instances"
export TMPDIR="$TEST_ROOT/tmp"
mkdir -p "$TMPDIR" "$INSTANCE_ROOT/config" "$INSTANCE_ROOT/backups"

cleanup_test() {
  git -C "$(cd "$SCRIPT_DIR/../.." && pwd)" tag -d "$TEST_RELEASE" >/dev/null 2>&1 || true
  rm -rf -- "$TEST_ROOT"
}
trap cleanup_test EXIT

printf 'INSTANCE_SLUG=%s\nENVIRONMENT_TYPE=test\nPRODUCT_VERSION=v1.0.0-rc8\nDOMAIN=customer.example.invalid\nDATABASE_NAME=pmqms_%s\nHTTP_PORT=8199\n' \
  "$SLUG" "$SLUG" > "$INSTANCE_ROOT/config/instance.env"
printf '{"product_version":"v1.0.0-rc8","deployment_state":"licensed"}\n' \
  > "$INSTANCE_ROOT/config/deployment-manifest.json"
printf 'fixture-environment\n' > "$INSTANCE_ROOT/config/environment_id"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
git -C "$REPO_ROOT" tag "$TEST_RELEASE" HEAD

# Source the real functions so the test exercises the production backup and upgrade path.
# The command dispatcher is guarded in customer-instance.sh for this purpose.
source "$SCRIPT"

require_instance() {
  [[ "$1" == "$SLUG" ]] || return 1
  printf '%s\n' "$INSTANCE_ROOT"
}
load_instance() {
  INSTANCE_SLUG="$SLUG"
  ENVIRONMENT_TYPE="test"
  PRODUCT_VERSION="v1.0.0-rc8"
  DATABASE_NAME="pmqms_${SLUG//-/_}"
}
compose() {
  case "$*" in
    *"pg_dump"*) printf 'fixture database dump\n' ;;
  esac
}
docker() {
  local arg backup_mount=""
  for arg in "$@"; do
    if [[ "$arg" == *":/backup" ]]; then
      backup_mount="${arg%:/backup}"
    fi
  done
  [[ -n "$backup_mount" ]] || return 0
  tar -czf "$backup_mount/filestore.tar.gz" --files-from /dev/null
}

upgrade "$SLUG" --to "$TEST_RELEASE"
upgrade "$SLUG" --to "$TEST_RELEASE"

backup_archive=("$INSTANCE_ROOT"/backups/*.tar.gz)
[[ -f "${backup_archive[0]}" ]] || { echo "backup artifact was not created" >&2; exit 1; }
grep -q '"product_version": "v99.99.99-rc0"' "$INSTANCE_ROOT/config/deployment-manifest.json" || {
  echo "upgrade manifest was not updated" >&2
  exit 1
}
if find "$TMPDIR" -mindepth 1 -maxdepth 1 -type d | grep -q .; then
  echo "temporary backup directory leaked" >&2
  exit 1
fi

repeat_dir="$(new_temp_dir)"
cleanup_temp_dir "$repeat_dir"
cleanup_temp_dir "$repeat_dir"
[[ ! -e "$repeat_dir" ]] || { echo "repeat-safe cleanup failed" >&2; exit 1; }

early_failure() (
  local tmp=""
  trap 'cleanup_temp_dir "$tmp"' EXIT
  tmp="$(new_temp_dir)"
  return 17
)
if early_failure; then
  echo "early failure unexpectedly succeeded" >&2
  exit 1
else
  early_status=$?
fi
[[ "$early_status" == 17 ]] || { echo "early failure status changed" >&2; exit 1; }
if find "$TMPDIR" -mindepth 1 -maxdepth 1 -type d | grep -q .; then
  echo "temporary directory leaked after early failure" >&2
  exit 1
fi

echo "customer-instance cleanup regression: PASS"
