#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/deployment/scripts/odoo-demo.sh"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/secrets/config" "$WORK/secrets/runtime" "$WORK/backups"
cp "$REPO_ROOT/deployment/runtime/runtime-lock.json" "$WORK/secrets/runtime/runtime-lock.json"
for file in odoo_pg_password; do printf 'test-only-not-a-secret\n' > "$WORK/secrets/$file"; done
printf '[options]\n' > "$WORK/secrets/config/odoo.conf"
printf '00000000-0000-4000-8000-000000000001\n' > "$WORK/secrets/config/environment_id"

cat > "$WORK/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$TEST_DOCKER_LOG"
case "$*" in
  "image inspect "*) exit 0 ;;
  *"exec -T postgres-demo pg_isready "*) exit 0 ;;
  *"psql -U odoo -d pmqms_demo2 -Atqc "*) printf '%s\n' "${MOCK_MODULE_STATE:-installed}" ;;
  *"run --rm --no-deps odoo-demo odoo "*) exit "${MOCK_ODOO_EXIT:-0}" ;;
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
chmod +x "$WORK/bin/docker"
chmod +x "$WORK/bin/jq"
export PATH="$WORK/bin:$PATH"
export TEST_DOCKER_LOG="$WORK/docker.log"
export PMQMS_DEMO_INSTANCE=demo2
export PMQMS_DEMO_SECRETS_DIR="$WORK/secrets"
export PMQMS_DEMO_BACKUP_DIR="$WORK/backups"
export PMQMS_DEMO_RUNTIME_LOCK_FILE="$WORK/secrets/runtime/runtime-lock.json"

"$LAUNCHER" upgrade-iso9001-module-demo2 > "$WORK/success.out"
grep -Fq 'iso9001_module_upgrade=PASS instance=demo2 database=pmqms_demo2 module=pm_qms_iso9001' "$WORK/success.out"
grep -Fq -- '--project-name pmqms-demo2' "$TEST_DOCKER_LOG"
grep -Fq 'run --rm --no-deps odoo-demo odoo -d pmqms_demo2 --update pm_qms_iso9001 --stop-after-init' "$TEST_DOCKER_LOG"
grep -Fq 'stop odoo-demo' "$TEST_DOCKER_LOG"
grep -Fq 'up -d odoo-demo' "$TEST_DOCKER_LOG"
! grep -Eq -- '--init|provision_license|import_license|seed_demo|seed-demo|install_or_update|--update [^ ]+,' "$TEST_DOCKER_LOG"

if PMQMS_DEMO_INSTANCE=demo "$LAUNCHER" upgrade-iso9001-module-demo2 > "$WORK/wrong-instance.out" 2>&1; then
  echo 'Targeted ISO upgrade unexpectedly accepted a non-Demo2 instance.' >&2
  exit 1
fi
if PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_DB=pmqms_demo "$LAUNCHER" upgrade-iso9001-module-demo2 > "$WORK/wrong-db.out" 2>&1; then
  echo 'Targeted ISO upgrade unexpectedly accepted the Demo1 database.' >&2
  exit 1
fi
if PMQMS_DEMO_INSTANCE=demo2 "$LAUNCHER" upgrade-iso9001-module-demo2 unexpected > "$WORK/extra-arg.out" 2>&1; then
  echo 'Targeted ISO upgrade unexpectedly accepted caller-supplied arguments.' >&2
  exit 1
fi
: > "$TEST_DOCKER_LOG"
if MOCK_MODULE_STATE='to install' "$LAUNCHER" upgrade-iso9001-module-demo2 > "$WORK/not-installed.out" 2>&1; then
  echo 'Targeted ISO upgrade unexpectedly accepted a module that is not installed.' >&2
  exit 1
fi
! grep -Fq 'run --rm --no-deps odoo-demo' "$TEST_DOCKER_LOG"
! grep -Fq 'restart odoo-demo' "$TEST_DOCKER_LOG"
: > "$TEST_DOCKER_LOG"
if MOCK_ODOO_EXIT=23 "$LAUNCHER" upgrade-iso9001-module-demo2 > "$WORK/update-failed.out" 2>&1; then
  echo 'Targeted ISO upgrade unexpectedly hid an Odoo update failure.' >&2
  exit 1
fi
grep -Fq 'stop odoo-demo' "$TEST_DOCKER_LOG"
! grep -Fq 'up -d odoo-demo' "$TEST_DOCKER_LOG"

# The historical 2015 seed XML must not be replayed by a module upgrade. Fresh
# installations still receive the initial packs from post_init_hook.
if grep -Fq 'data/initial_implementation_data.xml' "$REPO_ROOT/addons/pm_qms_iso9001/__manifest__.py"; then
  echo 'Legacy initial-pack seed remains in the module data update list.' >&2
  exit 1
fi
[[ ! -e "$REPO_ROOT/addons/pm_qms_iso9001/data/initial_implementation_data.xml" ]]
grep -Fq 'seed_iso9001_initial_implementation(env)' "$REPO_ROOT/addons/pm_qms_iso9001/hooks.py"
grep -Fq 'def post_init_hook(env):' "$REPO_ROOT/addons/pm_qms_iso9001/hooks.py"

echo 'Demo ISO module-only upgrade regressions: PASS'
