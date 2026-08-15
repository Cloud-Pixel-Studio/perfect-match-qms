#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/dev/compose.yml"
SECRETS_DIR="${PMQMS_ODOO_DEV_SECRETS_DIR:-/opt/perfect-match/secrets/odoo-dev}"
CONFIG_DIR="$SECRETS_DIR/config"
PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"
ADMIN_PASSWORD_FILE="$SECRETS_DIR/odoo_admin_password"
MISSION03_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence"
MISSION03_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence"
MISSION04_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa"
MISSION04_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa"
MISSION05_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit"
MISSION05_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit"
MISSION06_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi"
MISSION06_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi"

export ODOO_DEV_CONFIG_DIR="$CONFIG_DIR"
export ODOO_DEV_PG_PASSWORD_FILE="$PG_PASSWORD_FILE"
export ODOO_DEV_HTTP_BIND="${ODOO_DEV_HTTP_BIND:-127.0.0.1}"
export ODOO_DEV_HTTP_PORT="${ODOO_DEV_HTTP_PORT:-8069}"
export ODOO_DEV_LONGPOLLING_BIND="${ODOO_DEV_LONGPOLLING_BIND:-127.0.0.1}"
export ODOO_DEV_LONGPOLLING_PORT="${ODOO_DEV_LONGPOLLING_PORT:-8072}"

random_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
}

init_secrets() {
  mkdir -p "$CONFIG_DIR"
  chmod 755 "$SECRETS_DIR" "$CONFIG_DIR"

  if [[ ! -f "$PG_PASSWORD_FILE" ]]; then
    random_secret > "$PG_PASSWORD_FILE"
    chmod 600 "$PG_PASSWORD_FILE"
  fi

  if [[ ! -f "$ADMIN_PASSWORD_FILE" ]]; then
    random_secret > "$ADMIN_PASSWORD_FILE"
    chmod 600 "$ADMIN_PASSWORD_FILE"
  fi

  if [[ ! -f "$CONFIG_DIR/odoo.conf" ]]; then
    cat > "$CONFIG_DIR/odoo.conf" <<EOF
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
admin_passwd = $(cat "$ADMIN_PASSWORD_FILE")
list_db = True
proxy_mode = False
workers = 0
max_cron_threads = 0
EOF
    chmod 600 "$CONFIG_DIR/odoo.conf"
  fi
}

prepare_runtime_permissions() {
  init_secrets

  if docker image inspect odoo:19.0 >/dev/null 2>&1; then
    docker run --rm --user root \
      -v "$SECRETS_DIR:/secrets" \
      --entrypoint sh \
      odoo:19.0 \
      -lc "chown 100:101 /secrets/odoo_pg_password /secrets/config/odoo.conf && chmod 600 /secrets/odoo_pg_password /secrets/config/odoo.conf"
  else
    chmod 644 "$PG_PASSWORD_FILE" "$CONFIG_DIR/odoo.conf"
  fi
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

database_exists() {
  local db_name="$1"
  prepare_runtime_permissions
  compose up -d postgres-dev >/dev/null
  compose exec -T postgres-dev psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$db_name'" | grep -q 1
}

usage() {
  cat <<'EOF'
Usage: ./deployment/scripts/odoo-dev.sh <command>

Commands:
  init-secrets   Generate local DEV secrets outside Git.
  config         Validate the Docker Compose file.
  pull           Pull Odoo and PostgreSQL images.
  up             Start the Odoo DEV stack.
  down           Stop the Odoo DEV stack without removing volumes.
  restart        Restart the Odoo DEV stack.
  ps             Show stack containers.
  logs           Follow Odoo logs.
  shell          Open a shell in the Odoo container.
  db-shell       Open psql in the Postgres container.
  init-db        Initialize the pmqms_dev database with base only.
  install-core   Install pm_qms_core in pmqms_dev.
  update-core    Upgrade pm_qms_core in pmqms_dev.
  test-core      Run pm_qms_core Odoo tests in pmqms_test.
  install-mission03
                Install core, documents, and evidence addons in pmqms_dev.
  update-mission03
                Upgrade core, documents, and evidence addons in pmqms_dev.
  test-mission03
                Run Mission 03 addon tests in pmqms_test.
  install-mission04
                Install core through Risk, NCR, and CAPA addons in pmqms_dev.
  update-mission04
                Upgrade core through Risk, NCR, and CAPA addons in pmqms_dev.
  test-mission04
                Run Mission 04 addon tests in pmqms_test.
  install-mission05
                Install core through Internal Audit addons in pmqms_dev.
  update-mission05
                Upgrade core through Internal Audit addons in pmqms_dev.
  test-mission05
                Run Mission 05 addon tests in pmqms_test.
  install-mission06
                Install core through Performance KPI addons in pmqms_dev.
  update-mission06
                Upgrade core through Performance KPI addons in pmqms_dev.
  test-mission06
                Run Mission 06 addon tests in pmqms_test.
EOF
}

run_odoo_tests() {
  local modules="$1"
  local tags="$2"
  local label="$3"
  prepare_runtime_permissions
  compose up -d postgres-dev
  compose exec -T postgres-dev psql -U odoo -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'pmqms_test' AND pid <> pg_backend_pid();" >/dev/null
  compose exec -T postgres-dev dropdb -U odoo --maintenance-db=postgres --if-exists pmqms_test
  local test_log
  test_log="$(mktemp)"
  set +e
  compose run --rm odoo-dev odoo -d pmqms_test --init "$modules" --test-enable --test-tags "$tags" --stop-after-init --without-demo=all --log-level=test 2>&1 | tee "$test_log"
  local odoo_rc="${PIPESTATUS[0]}"
  set -e
  if grep -Eq "odoo\\.tests\\.result: .*([1-9][0-9]* failed|[1-9][0-9]* error\\(s\\))" "$test_log"; then
    rm -f "$test_log"
    echo "$label tests reported failures." >&2
    exit 1
  fi
  rm -f "$test_log"
  exit "$odoo_rc"
}

command="${1:-}"
case "$command" in
  init-secrets)
    init_secrets
    echo "Odoo DEV secrets initialized in $SECRETS_DIR"
    ;;
  config)
    init_secrets
    compose config >/dev/null
    echo "Odoo DEV Compose configuration is valid."
    ;;
  pull)
    init_secrets
    compose pull
    prepare_runtime_permissions
    ;;
  up)
    prepare_runtime_permissions
    compose up -d
    ;;
  down)
    init_secrets
    compose down
    ;;
  restart)
    init_secrets
    compose restart
    ;;
  ps)
    init_secrets
    compose ps
    ;;
  logs)
    init_secrets
    compose logs -f odoo-dev
    ;;
  shell)
    prepare_runtime_permissions
    compose exec odoo-dev bash
    ;;
  db-shell)
    prepare_runtime_permissions
    compose exec postgres-dev psql -U odoo -d postgres
    ;;
  init-db)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --init base --without-demo=all --stop-after-init
    ;;
  install-core)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --init pm_qms_core --without-demo=all --stop-after-init
    ;;
  update-core)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update pm_qms_core --stop-after-init
    ;;
  test-core)
    run_odoo_tests "pm_qms_core" "/pm_qms_core" "pm_qms_core"
    ;;
  install-mission03)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION03_ADDONS" --without-demo=all --stop-after-init
    ;;
  update-mission03)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION03_ADDONS" --stop-after-init
    ;;
  test-mission03)
    run_odoo_tests "$MISSION03_ADDONS" "$MISSION03_TEST_TAGS" "Mission 03"
    ;;
  install-mission04)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION03_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_risk,pm_qms_ncr,pm_qms_capa" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION04_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission04)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION04_ADDONS" --stop-after-init
    ;;
  test-mission04)
    run_odoo_tests "$MISSION04_ADDONS" "$MISSION04_TEST_TAGS" "Mission 04"
    ;;
  install-mission05)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION04_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_audit" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION05_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission05)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION05_ADDONS" --stop-after-init
    ;;
  test-mission05)
    run_odoo_tests "$MISSION05_ADDONS" "$MISSION05_TEST_TAGS" "Mission 05"
    ;;
  install-mission06)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION05_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_kpi" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION06_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission06)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION06_ADDONS" --stop-after-init
    ;;
  test-mission06)
    run_odoo_tests "$MISSION06_ADDONS" "$MISSION06_TEST_TAGS" "Mission 06"
    ;;
  ""|help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage >&2
    exit 2
    ;;
esac
