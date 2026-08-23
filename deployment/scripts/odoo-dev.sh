#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/dev/compose.yml"
SECRETS_DIR="${PMQMS_ODOO_DEV_SECRETS_DIR:-/opt/perfect-match/secrets/odoo-dev}"
CONFIG_DIR="$SECRETS_DIR/config"
PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"
ADMIN_PASSWORD_FILE="$SECRETS_DIR/odoo_admin_password"
ENVIRONMENT_ID_FILE="$CONFIG_DIR/environment_id"
MISSION03_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence"
MISSION03_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence"
MISSION04_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa"
MISSION04_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa"
MISSION05_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit"
MISSION05_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit"
MISSION06_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi"
MISSION06_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi"
MISSION07_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review"
MISSION07_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review"
MISSION08_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation"
MISSION08_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation"
MISSION09_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality"
MISSION09_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation,/pm_qms_pack_quality"
MISSION10_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_migration"
MISSION10_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation,/pm_qms_pack_quality,/pm_qms_migration"
MISSION11_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_migration,pm_qms_app"
MISSION11_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation,/pm_qms_pack_quality,/pm_qms_migration,/pm_qms_app"
MISSION12_ADDONS="$MISSION11_ADDONS"
MISSION12_TEST_TAGS="$MISSION11_TEST_TAGS"
MISSION12_1_ADDONS="$MISSION12_ADDONS"
MISSION12_1_TEST_TAGS="$MISSION12_TEST_TAGS"
MISSION14_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_migration,pm_qms_people,pm_qms_app"
MISSION14_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation,/pm_qms_pack_quality,/pm_qms_migration,/pm_qms_people,/pm_qms_app"
MISSION15_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_migration,pm_qms_people,pm_qms_calibration,pm_qms_app"
MISSION15_TEST_TAGS="/pm_qms_core,/pm_qms_documents,/pm_qms_evidence,/pm_qms_risk,/pm_qms_ncr,/pm_qms_capa,/pm_qms_audit,/pm_qms_kpi,/pm_qms_management_review,/pm_qms_implementation,/pm_qms_pack_quality,/pm_qms_migration,/pm_qms_people,/pm_qms_calibration,/pm_qms_app"
MISSION16_ADDONS="$MISSION15_ADDONS,pm_qms_customer_quality"
MISSION16_TEST_TAGS="$MISSION15_TEST_TAGS,/pm_qms_customer_quality"
MISSION17_ADDONS="$MISSION16_ADDONS,pm_qms_action_center,pm_qms_cost_quality"
MISSION17_TEST_TAGS="$MISSION16_TEST_TAGS,/pm_qms_action_center,/pm_qms_cost_quality"
MISSION18_ADDONS="$MISSION17_ADDONS"
MISSION18_TEST_TAGS="$MISSION17_TEST_TAGS,/pm_qms_core"
MISSION20_ADDONS="$MISSION18_ADDONS"
MISSION20_TEST_TAGS="$MISSION18_TEST_TAGS,/pm_qms_license"

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

  if [[ ! -f "$ENVIRONMENT_ID_FILE" ]]; then
    python3 -c 'import uuid; print(uuid.uuid4())' > "$ENVIRONMENT_ID_FILE"
    chmod 600 "$ENVIRONMENT_ID_FILE"
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

postgres_exec() {
  compose exec -T postgres-dev "$@"
}

postgres_exec_interactive() {
  compose exec postgres-dev "$@"
}

wait_for_postgres() {
  for _ in {1..60}; do
    if postgres_exec pg_isready -h 127.0.0.1 -U odoo -d postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  compose logs postgres-dev >&2 || true
  echo "PostgreSQL did not become ready in time." >&2
  return 1
}

database_exists() {
  local db_name="$1"
  prepare_runtime_permissions
  compose up -d postgres-dev >/dev/null
  wait_for_postgres
  postgres_exec psql -h 127.0.0.1 -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$db_name'" | grep -q 1
}

health() {
  prepare_runtime_permissions
  compose up -d >/dev/null
  local code="000"
  for _ in {1..60}; do
    code="$(curl -s -o /tmp/pmqms-dev-health.html -w '%{http_code}' "http://127.0.0.1:${ODOO_DEV_HTTP_PORT}/web/login?db=pmqms_dev" || true)"
    if [[ "$code" =~ ^(200|303|302)$ ]]; then
      break
    fi
    sleep 1
  done
  echo "odoo_dev_http=$code"
  compose ps
}

usage() {
  cat <<'EOF'
Usage: ./deployment/scripts/odoo-dev.sh <command>

Commands:
  standalone-check
                Verify no addon depends on functional ERP modules.
  init-secrets   Generate local DEV secrets outside Git.
  config         Validate the Docker Compose file.
  pull           Pull Odoo and PostgreSQL images.
  up             Start the Odoo DEV stack.
  down           Stop the Odoo DEV stack without removing volumes.
  restart        Restart the Odoo DEV stack.
  ps             Show stack containers.
  health         Validate DEV HTTP and container status.
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
  install-mission07
                Install core through Management Review addons in pmqms_dev.
  update-mission07
                Upgrade core through Management Review addons in pmqms_dev.
  test-mission07
                Run Mission 07 addon tests in pmqms_test.
  install-mission08
                Install core through Implementation Project Generator addons in pmqms_dev.
  update-mission08
                Upgrade core through Implementation Project Generator addons in pmqms_dev.
  test-mission08
                Run Mission 08 addon tests in pmqms_test.
  install-mission09
                Install core through Quality Management Pack addons in pmqms_dev.
  update-mission09
                Upgrade core through Quality Management Pack addons in pmqms_dev.
  test-mission09
                Run Mission 09 addon tests in pmqms_test.
  install-mission10
                Install core through migration validation addons in pmqms_dev.
  update-mission10
                Upgrade core through migration validation addons in pmqms_dev.
  test-mission10
                Run Mission 10 addon tests in pmqms_test.
  install-mission11
                Install full QMS stack including the application shell in pmqms_dev.
  update-mission11
                Upgrade full QMS stack including the application shell in pmqms_dev.
  test-mission11
                Run Mission 11 addon tests in pmqms_test.
  install-mission12
                Install full QMS stack including guided readiness in pmqms_dev.
  update-mission12
                Upgrade full QMS stack including guided readiness in pmqms_dev.
  test-mission12
                Run Mission 12 addon tests in pmqms_test.
  test-mission12-1
                Run Mission 12.1 UX hardening addon tests in pmqms_test.
  install-mission14
                Install full QMS stack including People, Training, and Competency in pmqms_dev.
  update-mission14
                Upgrade full QMS stack including People, Training, and Competency in pmqms_dev.
  test-mission14
                Run Mission 14 full-stack Odoo tests in pmqms_test.
  install-mission15
                Install full QMS stack including Equipment and Calibration in pmqms_dev.
  update-mission15
                Upgrade full QMS stack including Equipment and Calibration in pmqms_dev.
  test-mission15
                Run Mission 15 full-stack Odoo tests in pmqms_test.
  install-mission16
                Install full QMS stack including Customer Quality, 8D, Supplier Quality, and SCAR in pmqms_dev.
  update-mission16
                Upgrade full QMS stack including Customer Quality, 8D, Supplier Quality, and SCAR in pmqms_dev.
  test-mission16
                Run Mission 16 full-stack Odoo tests in pmqms_test.
  install-mission17
                Install full QMS stack including Action Center and Cost of Quality in pmqms_dev.
  update-mission17
                Upgrade full QMS stack including Action Center and Cost of Quality in pmqms_dev.
  test-mission17
                Run Mission 17 full-stack Odoo tests in pmqms_test.
  install-mission18
                Upgrade/install the Mission 18 standalone foundation in pmqms_dev.
  update-mission18
                Upgrade the Mission 18 standalone foundation in pmqms_dev.
  test-mission18
    Run Mission 18 focused/full-stack Odoo tests in pmqms_test.
  install-mission20
                Install/update the full QMS stack including commercial licensing.
  update-mission20
                Upgrade the full QMS stack including commercial licensing.
  test-mission20
                Run Mission 20 licensing and full-stack Odoo tests in pmqms_test.
EOF
}

run_odoo_tests() {
  local modules="$1"
  local tags="$2"
  local label="$3"
  prepare_runtime_permissions
  compose up -d postgres-dev
  wait_for_postgres
  postgres_exec psql -h 127.0.0.1 -U odoo -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'pmqms_test' AND pid <> pg_backend_pid();" >/dev/null || true
  postgres_exec dropdb -h 127.0.0.1 -U odoo --maintenance-db=postgres --if-exists pmqms_test
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
  standalone-check)
    python3 "$REPO_ROOT/deployment/scripts/standalone-dependency-check.py"
    ;;
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
  health)
    health
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
    postgres_exec_interactive psql -h 127.0.0.1 -U odoo -d postgres
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
  install-mission07)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION06_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_management_review" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION07_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission07)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION07_ADDONS" --stop-after-init
    ;;
  test-mission07)
    run_odoo_tests "$MISSION07_ADDONS" "$MISSION07_TEST_TAGS" "Mission 07"
    ;;
  install-mission08)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION07_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_implementation" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION08_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission08)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION08_ADDONS" --stop-after-init
    ;;
  test-mission08)
    run_odoo_tests "$MISSION08_ADDONS" "$MISSION08_TEST_TAGS" "Mission 08"
    ;;
  install-mission09)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION08_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_pack_quality" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION09_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission09)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION09_ADDONS" --stop-after-init
    ;;
  test-mission09)
    run_odoo_tests "$MISSION09_ADDONS" "$MISSION09_TEST_TAGS" "Mission 09"
    ;;
  install-mission10)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION09_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_migration" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION10_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission10)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION10_ADDONS" --stop-after-init
    ;;
  test-mission10)
    run_odoo_tests "$MISSION10_ADDONS" "$MISSION10_TEST_TAGS" "Mission 10"
    ;;
  install-mission11)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION10_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_app" --without-demo=all --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION11_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission11)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION11_ADDONS" --stop-after-init
    ;;
  test-mission11)
    run_odoo_tests "$MISSION11_ADDONS" "$MISSION11_TEST_TAGS" "Mission 11"
    ;;
  install-mission12)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION12_ADDONS" --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION12_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission12)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION12_ADDONS" --stop-after-init
    ;;
  test-mission12)
    run_odoo_tests "$MISSION12_ADDONS" "$MISSION12_TEST_TAGS" "Mission 12"
    ;;
  test-mission12-1)
    run_odoo_tests "$MISSION12_1_ADDONS" "$MISSION12_1_TEST_TAGS" "Mission 12.1"
    ;;
  install-mission14)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION12_1_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_people" --without-demo=all --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --update "pm_qms_app" --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION14_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission14)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION14_ADDONS" --stop-after-init
    ;;
  test-mission14)
    run_odoo_tests "$MISSION14_ADDONS" "$MISSION14_TEST_TAGS" "Mission 14"
    ;;
  install-mission15)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION14_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_calibration" --without-demo=all --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --update "pm_qms_app" --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION15_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission15)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION15_ADDONS" --stop-after-init
    ;;
  test-mission15)
    run_odoo_tests "$MISSION15_ADDONS" "$MISSION15_TEST_TAGS" "Mission 15"
    ;;
  install-mission16)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION15_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_customer_quality" --without-demo=all --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --update "pm_qms_app" --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION16_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission16)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION16_ADDONS" --stop-after-init
    ;;
  test-mission16)
    run_odoo_tests "$MISSION16_ADDONS" "$MISSION16_TEST_TAGS" "Mission 16"
    ;;
  install-mission17)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION16_ADDONS" --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --init "pm_qms_action_center,pm_qms_cost_quality" --without-demo=all --stop-after-init
      compose run --rm odoo-dev odoo -d pmqms_dev --update "pm_qms_app" --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION17_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission17)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION17_ADDONS" --stop-after-init
    ;;
  test-mission17)
    run_odoo_tests "$MISSION17_ADDONS" "$MISSION17_TEST_TAGS" "Mission 17"
    ;;
  install-mission18)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION18_ADDONS" --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION18_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission18)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION18_ADDONS" --stop-after-init
    ;;
  test-mission18)
    run_odoo_tests "$MISSION18_ADDONS" "$MISSION18_TEST_TAGS" "Mission 18"
    ;;
  install-mission20)
    prepare_runtime_permissions
    if database_exists pmqms_dev; then
      compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION20_ADDONS" --stop-after-init
    else
      compose run --rm odoo-dev odoo -d pmqms_dev --init "$MISSION20_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update-mission20)
    prepare_runtime_permissions
    compose run --rm odoo-dev odoo -d pmqms_dev --update "$MISSION20_ADDONS" --stop-after-init
    ;;
  test-mission20)
    run_odoo_tests "$MISSION20_ADDONS" "$MISSION20_TEST_TAGS" "Mission 20"
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
