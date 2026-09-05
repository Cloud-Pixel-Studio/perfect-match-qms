#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$SCRIPT_DIR/customer-instance.sh"
MODEL="$SCRIPT_DIR/../../addons/pm_qms_app/models/user_access.py"
WORK="$(mktemp -d)"
export PMQMS_CUSTOMER_INSTANCE_ROOT="$WORK/instances"
export TMPDIR="$WORK/tmp"
mkdir -p "$PMQMS_CUSTOMER_INSTANCE_ROOT" "$TMPDIR" "$PMQMS_CUSTOMER_INSTANCE_ROOT/m31-scope-test/config"

fail() { echo "FAIL: $*" >&2; exit 1; }
cleanup() { rm -rf -- "$WORK"; }
trap cleanup EXIT

ROOT="$PMQMS_CUSTOMER_INSTANCE_ROOT/m31-scope-test"
printf 'INSTANCE_SLUG=m31-scope-test\nENVIRONMENT_TYPE=test\nDATABASE_NAME=pmqms_m31_scope_test\n' > "$ROOT/config/instance.env"
printf 'temporary password\n' > "$WORK/password"

source "$SCRIPT"
require_instance() { printf '%s\n' "$ROOT"; }
load_instance() { :; }
load_runtime_for_root() { :; }
runtime_verify_lock() { :; }
DATABASE_NAME=pmqms_m31_scope_test
RUNTIME_LOCK_PATH="$WORK/runtime-lock.json"
runtime_manifest_gate() { return 0; }
health() { return 0; }
ALPINE_IMAGE=alpine:fixture
ODOO_IMAGE=odoo:fixture
POSTGRES_IMAGE=postgres:fixture

docker() {
  case "$1" in
    inspect|image) printf '%s\n' image-id ;;
    *) return 0 ;;
  esac
}

emit_ready_fixture() {
  case "$1" in
    unscoped|system-admin|non-qm)
      printf '%s\n' \
        'customer_ready_application=pass' \
        'CUSTOMER_READY_PROBE_FIRST_USER=fail' \
        'CUSTOMER_READY_PROBE_LICENSE=pass' \
        'CUSTOMER_READY_QMS_SCOPE=fail' \
        'CUSTOMER_READY_QMS_ORGANIZATION=fail' \
        'CUSTOMER_READY_QMS_SITES=fail' \
        'CUSTOMER_READY_QMS_PROCESSES=fail'
      ;;
    wrong-org)
      printf '%s\n' \
        'customer_ready_application=pass' \
        'CUSTOMER_READY_PROBE_FIRST_USER=pass' \
        'CUSTOMER_READY_PROBE_LICENSE=pass' \
        'CUSTOMER_READY_QMS_SCOPE=pass' \
        'CUSTOMER_READY_QMS_ORGANIZATION=fail' \
        'CUSTOMER_READY_QMS_SITES=pass' \
        'CUSTOMER_READY_QMS_PROCESSES=pass'
      ;;
    all-sites-false)
      printf '%s\n' \
        'customer_ready_application=pass' \
        'CUSTOMER_READY_PROBE_FIRST_USER=pass' \
        'CUSTOMER_READY_PROBE_LICENSE=pass' \
        'CUSTOMER_READY_QMS_SCOPE=pass' \
        'CUSTOMER_READY_QMS_ORGANIZATION=pass' \
        'CUSTOMER_READY_QMS_SITES=fail' \
        'CUSTOMER_READY_QMS_PROCESSES=pass'
      ;;
    all-processes-false)
      printf '%s\n' \
        'customer_ready_application=pass' \
        'CUSTOMER_READY_PROBE_FIRST_USER=pass' \
        'CUSTOMER_READY_PROBE_LICENSE=pass' \
        'CUSTOMER_READY_QMS_SCOPE=pass' \
        'CUSTOMER_READY_QMS_ORGANIZATION=pass' \
        'CUSTOMER_READY_QMS_SITES=pass' \
        'CUSTOMER_READY_QMS_PROCESSES=fail'
      ;;
    valid|zero-process)
      printf '%s\n' \
        'customer_ready_application=pass' \
        'CUSTOMER_READY_PROBE_FIRST_USER=pass' \
        'CUSTOMER_READY_PROBE_LICENSE=pass' \
        'CUSTOMER_READY_QMS_SCOPE=pass' \
        'CUSTOMER_READY_QMS_ORGANIZATION=pass' \
        'CUSTOMER_READY_QMS_SITES=pass' \
        'CUSTOMER_READY_QMS_PROCESSES=pass'
      ;;
    *) return 42 ;;
  esac
}

compose() {
  case "$*" in
    *"ps -q odoo"*) printf '%s\n' odoo-id ;;
    *"ps -q postgres"*) printf '%s\n' postgres-id ;;
    *"odoo shell"*)
      local payload
      payload="$(cat)"
      if [[ "${BOOTSTRAP_MODE:-0}" == 1 ]]; then
        grep -Fq '"qms_organization_ids": [(6, 0, [organization.id])]' <<<"$payload" || return 43
        grep -Fq '"qms_site_ids": [(5, 0, 0)]' <<<"$payload" || return 44
        grep -Fq '"qms_all_sites": True' <<<"$payload" || return 45
        grep -Fq '"qms_process_ids": [(5, 0, 0)]' <<<"$payload" || return 46
        grep -Fq '"qms_all_processes": True' <<<"$payload" || return 47
        BOOTSTRAP_SEEN=1
      elif [[ "${CREATE_SITE_MODE:-0}" == 1 ]]; then
        grep -Fq '"organization_id": organization.id' <<<"$payload" || return 46
        CREATE_SITE_SEEN=1
        printf '%s\n' 'site=M31-SITE'
      else
        emit_ready_fixture "${CUSTOMER_READY_SCENARIO:-valid}"
      fi
      ;;
    *) return 0 ;;
  esac
}

for scenario in unscoped wrong-org all-sites-false all-processes-false system-admin non-qm; do
  output=""
  status=0
  output="$(CUSTOMER_READY_SCENARIO="$scenario" customer_ready m31-scope-test 2>&1)" || status=$?
  [[ "$status" -ne 0 ]] || fail "$scenario was accepted"
  grep -Fxq 'CUSTOMER_READY=NO' <<<"$output" || fail "$scenario did not report CUSTOMER_READY=NO"
done

for scenario in valid zero-process; do
  output=""
  status=0
  output="$(CUSTOMER_READY_SCENARIO="$scenario" customer_ready m31-scope-test 2>&1)" || status=$?
  [[ "$status" -eq 0 ]] || fail "$scenario was rejected"
  grep -Fxq 'CUSTOMER_READY=YES' <<<"$output" || fail "$scenario did not report CUSTOMER_READY=YES"
  grep -Fxq 'CUSTOMER_READY_QMS_SCOPE=pass' <<<"$output" || fail "$scenario did not report scope pass"
  grep -Fxq 'CUSTOMER_READY_QMS_SITES=pass' <<<"$output" || fail "$scenario did not report site pass"
  grep -Fxq 'CUSTOMER_READY_QMS_PROCESSES=pass' <<<"$output" || fail "$scenario did not report process pass"
done

grep -Fq '"qms_organization_ids": [(6, 0, [organization.id])]' "$SCRIPT" || fail "bootstrap organization scope missing"
grep -Fq '"qms_site_ids": [(5, 0, 0)]' "$SCRIPT" || fail "bootstrap site scope reset missing"
grep -Fq '"qms_all_sites": True' "$SCRIPT" || fail "bootstrap all-sites scope missing"
grep -Fq '"qms_process_ids": [(5, 0, 0)]' "$SCRIPT" || fail "bootstrap process scope reset missing"
grep -Fq '"qms_all_processes": True' "$SCRIPT" || fail "bootstrap all-processes scope missing"
grep -Fq 'organization in user.qms_effective_organization_ids' "$SCRIPT" || fail "effective organization check missing"
grep -Fq 'all(site in user.qms_effective_site_ids for site in sites)' "$SCRIPT" || fail "effective site check missing"
grep -Fq 'bool(scope_ok and user.qms_all_processes)' "$SCRIPT" || fail "zero-process-safe process check missing"
grep -Fq 'vals["qms_scope_configured"] = True' "$MODEL" || fail "model scope configuration behavior missing"

BOOTSTRAP_MODE=1
BOOTSTRAP_SEEN=0
bootstrap_customer m31-scope-test \
  --company-name "M31 Scope Fixture" \
  --company-code M31SCOPE \
  --user-login qm@m31.invalid \
  --user-name "M31 Quality Manager" \
  --user-email qm@m31.invalid \
  --user-password-file "$WORK/password" >/dev/null
[[ "$BOOTSTRAP_SEEN" == 1 ]] || fail "bootstrap scope payload was not exercised"

BOOTSTRAP_MODE=0
CREATE_SITE_MODE=1
CREATE_SITE_SEEN=0
create_site m31-scope-test --code M31-SITE --name "M31 Scope Site" --type site >/dev/null
[[ "$CREATE_SITE_SEEN" == 1 ]] || fail "site-after-bootstrap payload was not exercised"

echo "customer bootstrap scope regressions: PASS"
