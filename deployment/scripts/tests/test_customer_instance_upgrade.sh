#!/usr/bin/env bash
set -euo pipefail

# Unit-style M30.8 contract coverage. External Docker/backup operations are
# replaced with deterministic fakes; no real customer or protected instance is
# addressed by this test.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$SCRIPT_DIR/customer-instance.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORK="$(mktemp -d)"
export PMQMS_CUSTOMER_INSTANCE_ROOT="$WORK/instances"
export TMPDIR="$WORK/tmp"
mkdir -p "$PMQMS_CUSTOMER_INSTANCE_ROOT" "$TMPDIR" "$WORK/bundle/deployment/customer" \
  "$WORK/bundle/deployment/docker/customer" "$WORK/bundle/deployment/runtime" "$WORK/bundle/addons/example"

CURRENT_SOURCE="41bef38bbb2287ca18a8dbefab30784f17011cb4"
TARGET_SOURCE="c0e263e06261fb3f1aaf2a51561e6510be31b84b"
CURRENT_PRODUCT="v1.0.0-rc11"
TARGET_PRODUCT="v99.99.99-rc0"
TARGET_BUNDLE="$WORK/target.tar.gz"
touch "$TARGET_BUNDLE"

fail() { echo "FAIL: $*" >&2; exit 1; }
cleanup() {
  local rc=$?
  trap - EXIT
  chmod -R u+w "$WORK" 2>/dev/null || true
  rm -rf -- "$WORK"
  exit "$rc"
}
trap cleanup EXIT

cp "$REPO_ROOT/deployment/runtime/runtime-lock.json" "$WORK/bundle/deployment/runtime/runtime-lock.json"
printf 'bundle_pm_qms_core\n' > "$WORK/bundle/deployment/customer/modules.txt"
cat > "$WORK/bundle/deployment/docker/customer/compose.yml.template" <<'EOF'
services:
  x-release-asset-marker: bundle-compose
  odoo:
    image: __ODOO_IMAGE__
    environment:
      INSTANCE: __INSTANCE_SLUG__
      ROOT: __INSTANCE_ROOT__
      PORT: __HTTP_PORT__
      MASTER: __ODOO_MASTER_PASSWORD__
  postgres:
    image: __POSTGRES_IMAGE__
EOF
cat > "$WORK/bundle/deployment/docker/customer/odoo.conf.template" <<'EOF'
[options]
admin_passwd = __ODOO_MASTER_PASSWORD__
db_name = __DATABASE_NAME__
EOF
printf 'bundle addon marker\n' > "$WORK/bundle/addons/example/marker.txt"
jq -n --arg product "$TARGET_PRODUCT" --arg source "$TARGET_SOURCE" \
  '{product_version:$product,release_tag:$product,source_sha:$source,environment_types:["customer","test"],runtime_lock_sha256:"fixture",odoo_image:"fixture",postgres_image:"fixture",contains_demo_data:false,contains_private_signing_key:false}' \
  > "$WORK/bundle/manifest.json"

source "$SCRIPT"

make_instance() {
  local slug="$1" product="${2:-$CURRENT_PRODUCT}" source="${3:-$CURRENT_SOURCE}" root
  root="$PMQMS_CUSTOMER_INSTANCE_ROOT/$slug"
  rm -rf -- "$root"
  mkdir -p "$root/config" "$root/secrets" "$root/license" "$root/activation" "$root/runtime/addons" "$root/runtime/release/deployment/customer" "$root/runtime/release/deployment/docker/customer"
  cp "$REPO_ROOT/deployment/runtime/runtime-lock.json" "$root/config/runtime-lock.json"
  printf 'INSTANCE_SLUG=%s\nENVIRONMENT_TYPE=test\nPRODUCT_VERSION=%s\nSOURCE_RELEASE_SHA=%s\nDOMAIN=test.invalid\nDATABASE_NAME=pmqms_%s\nHTTP_PORT=19180\n' \
    "$slug" "$product" "$source" "$slug" > "$root/config/instance.env"
  printf 'old-master\n' > "$root/secrets/odoo_master_password"
  printf 'old-password\n' > "$root/secrets/postgres_password"
  printf 'fictional-license\n' > "$root/license/active.pmql"
  printf 'old_module\n' > "$root/runtime/release/deployment/customer/modules.txt"
  printf 'old-compose __ODOO_IMAGE__ __POSTGRES_IMAGE__ __INSTANCE_SLUG__ __INSTANCE_ROOT__ __HTTP_PORT__\n' > "$root/runtime/release/deployment/docker/customer/compose.yml.template"
  printf 'old-odoo __ODOO_MASTER_PASSWORD__ __DATABASE_NAME__\n' > "$root/runtime/release/deployment/docker/customer/odoo.conf.template"
  printf 'old addon\n' > "$root/runtime/addons/old.txt"
  printf 'customer sentinel\n' > "$root/runtime/sentinel.txt"
  jq -n --arg product "$product" --arg source "$source" \
    '{product_version:$product,source_sha:$source,source_release_sha:$source,deployment_state:"deployed"}' > "$root/config/product-manifest.json"
  jq -n --arg product "$product" --arg source "$source" \
    '{product_version:$product,source_release_sha:$source,deployment_state:"deployed"}' > "$root/config/deployment-manifest.json"
}

# These overrides isolate the shell contract from Docker and the durable
# backup implementation while retaining the real activation and rollback code.
runtime_verify_lock() { :; }
validate_bundle_archive() {
  local bundle="$1" requested_type="$2" destination="$3"
  [[ -f "$bundle" ]] || return 17
  [[ "${TARGET_MODE:-}" != invalid ]] || return 17
  rm -rf -- "$destination"
  mkdir -p "$destination"
  cp -a "$WORK/bundle/." "$destination/"
  if [[ "${TARGET_MODE:-}" == runtime-different ]]; then
    jq '.odoo.image = "odoo:19.0@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' \
      "$destination/deployment/runtime/runtime-lock.json" > "$destination/runtime-lock.tmp"
    mv "$destination/runtime-lock.tmp" "$destination/deployment/runtime/runtime-lock.json"
  elif [[ "${TARGET_MODE:-}" == postgres-major ]]; then
    jq '.postgres.image = "postgres:16@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" | .postgres.digest = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"' \
      "$destination/deployment/runtime/runtime-lock.json" > "$destination/runtime-lock.tmp"
    mv "$destination/runtime-lock.tmp" "$destination/deployment/runtime/runtime-lock.json"
  fi
  BUNDLE_PRODUCT_VERSION="$TARGET_PRODUCT"
  BUNDLE_SOURCE_SHA="${TARGET_SOURCE_OVERRIDE:-$TARGET_SOURCE}"
}
runtime_major() { sed -nE 's/^[^:]+:([0-9]+)(@.*)?$/\1/p' <<<"$1"; }
backup() {
  [[ "${FAIL_BACKUP:-0}" == 1 ]] && return 17
  local slug="$1" root="$PMQMS_CUSTOMER_INSTANCE_ROOT/$1" archive="$root/backups/m30-8-test.tar.age"
  mkdir -p "$root/backups"
  printf 'encrypted fictional backup\n' > "$archive"
  printf 'checksum\n' > "$archive.sha256"
  printf '{}\n' > "$archive.manifest.json"
  printf 'backup=%s\nchecksum=%s\nmanifest=%s\n' "$archive" "$archive.sha256" "$archive.manifest.json"
}
capture_rollback_data() {
  local root="$1" snapshot="$2"
  printf 'fictional rollback database\n' > "$snapshot/db.dump"
  tar -czf "$snapshot/filestore.tar.gz" --files-from /dev/null
}
restore_rollback_data() { :; }
compose() {
  case "$*" in
    *" -u "*) [[ "${FAIL_MODULE_UPDATE:-0}" != 1 ]] || return 23;;
  esac
  return 0
}
health_root() { [[ "${FAIL_HEALTH:-0}" != 1 ]]; }
CUSTOMER_READY_CALLS=0
test_customer_ready() {
  CUSTOMER_READY_CALLS=$((CUSTOMER_READY_CALLS + 1))
  [[ "${FAIL_TARGET_READY_CALL:-0}" != 1 || "$CUSTOMER_READY_CALLS" != 2 ]] || return 19
  echo 'CUSTOMER_READY=YES'
}
customer_ready() { test_customer_ready "$@"; }

assert_file_contains() { grep -Fq "$2" "$1" || fail "$3"; }
expect_fail() {
  local label="$1"; shift
  local output
  if output="$("$@" 2>&1)"; then fail "$label unexpectedly succeeded"; fi
  printf '%s\n' "$output" > "$WORK/$label.out"
}

# Initial provisioning must persist bundle assets even when a deliberately
# different operator fixture exists.
ASSET_SLUG="m30-8-asset-provenance"
SOURCE_RELEASE_SHA="$TARGET_SOURCE" init_instance "$ASSET_SLUG" --type test --release "$TARGET_PRODUCT" --port 19181 --release-assets-dir "$WORK/bundle" >/dev/null
ASSET_ROOT="$PMQMS_CUSTOMER_INSTANCE_ROOT/$ASSET_SLUG"
assert_file_contains "$ASSET_ROOT/runtime/release/deployment/customer/modules.txt" bundle_pm_qms_core "bundle module list was not persisted"
assert_file_contains "$ASSET_ROOT/runtime/compose.yml" bundle-compose "rendered compose did not use bundle assets"
rm -rf -- "$ASSET_ROOT"

reset_case() {
  make_instance m30-8-upgrade-test
  TARGET_PRODUCT="v99.99.99-rc0"
  TARGET_MODE=""
  TARGET_SOURCE_OVERRIDE=""
  FAIL_BACKUP=0
  FAIL_MODULE_UPDATE=0
  FAIL_HEALTH=0
  FAIL_TARGET_READY_CALL=0
  CUSTOMER_READY_CALLS=0
}

# Invalid target, current readiness, interrupted state, same release, lineage,
# runtime approval and durable-backup gates all fail before activation.
reset_case; TARGET_MODE=invalid; expect_fail invalid-bundle upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"
assert_file_contains "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/runtime/release/deployment/customer/modules.txt" old_module "invalid bundle mutated instance"

reset_case; customer_ready() { return 1; }; expect_fail current-not-ready upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"
assert_file_contains "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/runtime/release/deployment/customer/modules.txt" old_module "current-ready failure mutated instance"
customer_ready() { test_customer_ready "$@"; }

reset_case; jq '.deployment_state="upgrade-applying"' "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/config/deployment-manifest.json" > "$WORK/state.tmp"; mv "$WORK/state.tmp" "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/config/deployment-manifest.json"; expect_fail interrupted-state upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"

reset_case; TARGET_PRODUCT="$CURRENT_PRODUCT"; expect_fail same-release upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"

reset_case; TARGET_PRODUCT="v0.99.99-rc0"; expect_fail downgrade upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"

reset_case; TARGET_SOURCE_OVERRIDE="0000000000000000000000000000000000000000"; expect_fail unrelated-lineage upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"

reset_case; TARGET_MODE=runtime-different; expect_fail runtime-approval upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"

reset_case; TARGET_MODE=postgres-major; expect_fail postgres-major upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE" --approve-runtime-change

reset_case; FAIL_BACKUP=1; expect_fail durable-backup upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"

# Successful upgrade applies the target module list and release assets while
# preserving the fictional customer sentinel.
reset_case
upgrade_output="$(upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE" --to "$TARGET_PRODUCT" 2>&1)" || fail "successful upgrade failed: $upgrade_output"
assert_file_contains "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/runtime/release/deployment/customer/modules.txt" bundle_pm_qms_core "target module list was not activated"
assert_file_contains "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/runtime/sentinel.txt" 'customer sentinel' "successful upgrade lost sentinel"
jq -e --arg product "$TARGET_PRODUCT" --arg source "$TARGET_SOURCE" '.deployment_state == "deployed" and .product_version == $product and .source_release_sha == $source and .last_upgrade_result == "success"' \
  "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/config/deployment-manifest.json" >/dev/null || fail "successful upgrade identity was not committed"
[[ ! -e "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/runtime/.m30-8-previous" ]] || fail "successful upgrade leaked previous runtime"
grep -Fq 'UPGRADE_RESULT=PASS' <<<"$upgrade_output" || fail "successful upgrade result was not reported"

# Same-target re-entry is rejected without a second backup or migration.
expect_fail same-target-reentry upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE"
grep -Fq 'REJECT_SAME_RELEASE' "$WORK/same-target-reentry.out" || fail "same-target re-entry was not rejected"

run_failed_upgrade() {
  local label="$1" variable="$2"
  reset_case
  eval "$variable=1"
  local output
  if output="$(upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE" 2>&1)"; then fail "$label unexpectedly succeeded"; fi
  printf '%s\n' "$output" > "$WORK/$label.out"
  grep -Fq 'UPGRADE_RESULT=FAILED' "$WORK/$label.out" || fail "$label did not report failed upgrade"
  grep -Fq 'ROLLBACK_RESULT=PASS' "$WORK/$label.out" || fail "$label did not report rollback pass"
  assert_file_contains "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/runtime/release/deployment/customer/modules.txt" old_module "$label did not restore old release assets"
  jq -e --arg product "$CURRENT_PRODUCT" --arg source "$CURRENT_SOURCE" '.deployment_state == "deployed" and .product_version == $product and .source_release_sha == $source and .last_upgrade_result == "rolled_back"' \
    "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/config/deployment-manifest.json" >/dev/null || fail "$label did not restore release identity"
  assert_file_contains "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-8-upgrade-test/runtime/sentinel.txt" 'customer sentinel' "$label lost sentinel"
}
run_failed_upgrade module-update FAIL_MODULE_UPDATE
run_failed_upgrade health FAIL_HEALTH
run_failed_upgrade customer-ready FAIL_TARGET_READY_CALL

# A rollback failure is fail-closed and preserves the ephemeral evidence path.
reset_case
restore_rollback_snapshot() { return 31; }
FAIL_MODULE_UPDATE=1
if rollback_failure_output="$(upgrade m30-8-upgrade-test --bundle "$TARGET_BUNDLE" 2>&1)"; then fail "rollback failure unexpectedly succeeded"; fi
grep -Fq 'ROLLBACK_RESULT=FAILED' <<<"$rollback_failure_output" || fail "rollback failure was not reported"
PRESERVED_SNAPSHOT="$(sed -n 's/^ROLLBACK_EVIDENCE_PRESERVED=//p' <<<"$rollback_failure_output")"
[[ -d "$PRESERVED_SNAPSHOT" ]] || fail "rollback evidence was not preserved"
rm -rf -- "$(dirname "$PRESERVED_SNAPSHOT")"

echo "m30.8 customer-instance upgrade tests: PASS (asset authority, preflight, runtime gate, backup, success, rollback, re-entry, fail-closed evidence)"
