#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/deployment/scripts/odoo-demo.sh"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/secrets/config" "$WORK/secrets/runtime" "$WORK/backups"
cp "$REPO_ROOT/deployment/runtime/runtime-lock.json" "$WORK/secrets/runtime/runtime-lock.json"
printf 'test-only-not-a-secret\n' > "$WORK/secrets/odoo_pg_password"
printf '[options]\n' > "$WORK/secrets/config/odoo.conf"
printf '00000000-0000-4000-8000-000000000001\n' > "$WORK/secrets/config/environment_id"

cat > "$WORK/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$TEST_DOCKER_LOG"
case "$*" in
  "image inspect "*) exit 0 ;;
  *" ps -q postgres-demo") printf '%s\n' 'demo2-postgres-id' ;;
  *" ps -q odoo-demo") printf '%s\n' 'demo2-odoo-id' ;;
  "inspect --format {{.State.Running}} demo2-postgres-id") printf '%s\n' true ;;
  "inspect --format {{.State.Health.Status}} demo2-postgres-id") printf '%s\n' "${MOCK_POSTGRES_HEALTH:-healthy}" ;;
  "inspect --format {{.State.Running}} demo2-odoo-id") printf '%s\n' true ;;
  *"psql -U odoo -d pmqms_demo2 -Atqc"*) printf '%s\n' "${MOCK_MODULE_STATE:-installed|false}" ;;
  *"run --rm --no-deps odoo-demo odoo -d pmqms_demo2 --update pm_qms_implementation --stop-after-init")
    exit "${MOCK_UPDATE_EXIT:-0}" ;;
esac
DOCKER
cat > "$WORK/bin/jq" <<'JQ'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  .odoo.image) printf 'odoo:19.0@sha256:test-pinned-odoo\n' ;;
  .postgres.image) printf 'postgres:15@sha256:test-pinned-postgres\n' ;;
  .alpine.image) printf 'alpine:3.20@sha256:test-pinned-alpine\n' ;;
  *) exit 2 ;;
esac
JQ
chmod +x "$WORK/bin/docker" "$WORK/bin/jq"
export PATH="$WORK/bin:$PATH"
export TEST_DOCKER_LOG="$WORK/docker.log"
export PMQMS_DEMO_INSTANCE=demo2
export PMQMS_DEMO_SECRETS_DIR="$WORK/secrets"
export PMQMS_DEMO_BACKUP_DIR="$WORK/backups"
export PMQMS_DEMO_RUNTIME_LOCK_FILE="$WORK/secrets/runtime/runtime-lock.json"

"$LAUNCHER" upgrade-implementation-module-demo2 > "$WORK/success.out"
grep -Fq 'implementation_module_upgrade=PASS instance=demo2 database=pmqms_demo2 module=pm_qms_implementation' "$WORK/success.out"
grep -Fq -- '--project-name pmqms-demo2' "$TEST_DOCKER_LOG"
grep -Fq 'run --rm --no-deps odoo-demo odoo -d pmqms_demo2 --update pm_qms_implementation --stop-after-init' "$TEST_DOCKER_LOG"
stop_line="$(grep -n -F 'stop odoo-demo' "$TEST_DOCKER_LOG" | cut -d: -f1)"
run_line="$(grep -n -F 'run --rm --no-deps odoo-demo' "$TEST_DOCKER_LOG" | cut -d: -f1)"
start_line="$(grep -n -F 'up -d odoo-demo' "$TEST_DOCKER_LOG" | cut -d: -f1)"
[[ "$stop_line" -lt "$run_line" && "$run_line" -lt "$start_line" ]]
! grep -Eq -- '--init|provision_license|provision-license|import_license|seed_demo|seed-demo|install_or_update|--update [^ ]+,' "$TEST_DOCKER_LOG"
! grep -Fq 'up -d postgres-demo' "$TEST_DOCKER_LOG"

run_invalid_configuration() {
  case "$1" in
    wrong-instance) PMQMS_DEMO_INSTANCE=demo "$LAUNCHER" upgrade-implementation-module-demo2 ;;
    wrong-database) PMQMS_DEMO_DB=pmqms_demo "$LAUNCHER" upgrade-implementation-module-demo2 ;;
    wrong-project) PMQMS_DEMO_COMPOSE_PROJECT=pmqms-demo "$LAUNCHER" upgrade-implementation-module-demo2 ;;
    wrong-volume) PMQMS_DEMO_POSTGRES_VOLUME=pmqms_postgres "$LAUNCHER" upgrade-implementation-module-demo2 ;;
    *) return 2 ;;
  esac
}

for invalid in wrong-instance wrong-database wrong-project wrong-volume; do
  : > "$TEST_DOCKER_LOG"
  if run_invalid_configuration "$invalid" > "$WORK/invalid.out" 2>&1; then
    echo "Unsafe implementation upgrade configuration unexpectedly accepted: $invalid" >&2
    exit 1
  fi
  [[ ! -s "$TEST_DOCKER_LOG" ]]
done

for module_state in 'to install|false' 'installed|true'; do
  : > "$TEST_DOCKER_LOG"
  if MOCK_MODULE_STATE="$module_state" "$LAUNCHER" upgrade-implementation-module-demo2 > "$WORK/module-state.out" 2>&1; then
    echo "Unexpected module/demo state accepted: $module_state" >&2
    exit 1
  fi
  ! grep -Fq 'stop odoo-demo' "$TEST_DOCKER_LOG"
  ! grep -Fq 'run --rm --no-deps odoo-demo' "$TEST_DOCKER_LOG"
done

: > "$TEST_DOCKER_LOG"
if MOCK_POSTGRES_HEALTH=unhealthy "$LAUNCHER" upgrade-implementation-module-demo2 > "$WORK/unhealthy.out" 2>&1; then
  echo 'Implementation upgrade unexpectedly ran with unhealthy PostgreSQL.' >&2
  exit 1
fi
! grep -Fq 'stop odoo-demo' "$TEST_DOCKER_LOG"

: > "$TEST_DOCKER_LOG"
if MOCK_UPDATE_EXIT=23 "$LAUNCHER" upgrade-implementation-module-demo2 > "$WORK/update-failed.out" 2>&1; then
  echo 'Targeted implementation update unexpectedly hid an Odoo failure.' >&2
  exit 1
fi
grep -Fq 'stop odoo-demo' "$TEST_DOCKER_LOG"
! grep -Fq 'up -d odoo-demo' "$TEST_DOCKER_LOG"

echo 'Demo2 implementation-module-only upgrade regressions: PASS'
