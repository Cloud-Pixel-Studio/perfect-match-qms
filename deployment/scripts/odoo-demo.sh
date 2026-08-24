#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/demo/compose.yml"
SECRETS_DIR="${PMQMS_DEMO_SECRETS_DIR:-/opt/perfect-match/secrets/odoo-demo}"
CONFIG_DIR="$SECRETS_DIR/config"
PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"
ADMIN_PASSWORD_FILE="$SECRETS_DIR/odoo_admin_password"
DEMO_ADMIN_PASSWORD_FILE="$SECRETS_DIR/demo_admin_password"
PERSONA_PASSWORD_DIR="$SECRETS_DIR/personas"
ENVIRONMENT_ID_FILE="$CONFIG_DIR/environment_id"
DEMO_LICENSE_FILE="${PMQMS_DEMO_LICENSE_FILE:-$SECRETS_DIR/demo_license.pmql}"
BACKUP_DIR="${PMQMS_DEMO_BACKUP_DIR:-/opt/perfect-match/backups/odoo-demo}"
DB_NAME="${PMQMS_DEMO_DB:-pmqms_demo}"
DEMO_COMPANY_NAME="${PMQMS_DEMO_COMPANY_NAME:-Apex Precision Systems, Inc.}"
DEMO_ADMIN_LOGIN="${PMQMS_DEMO_ADMIN_LOGIN:-admin}"
DEMO_QUALITY_MANAGER_LOGIN="${PMQMS_DEMO_QUALITY_MANAGER_LOGIN:-olivia.parker.demo@perfectmatch.local}"
DEMO_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_migration,pm_qms_people,pm_qms_calibration,pm_qms_license,pm_qms_app,pm_qms_customer_quality,pm_qms_action_center,pm_qms_cost_quality"

export ODOO_DEMO_CONFIG_DIR="$CONFIG_DIR"
export ODOO_DEMO_PG_PASSWORD_FILE="$PG_PASSWORD_FILE"
export ODOO_DEMO_HTTP_BIND="${ODOO_DEMO_HTTP_BIND:-0.0.0.0}"
export ODOO_DEMO_HTTP_PORT="${ODOO_DEMO_HTTP_PORT:-8170}"
export ODOO_DEMO_LONGPOLLING_BIND="${ODOO_DEMO_LONGPOLLING_BIND:-0.0.0.0}"
export ODOO_DEMO_LONGPOLLING_PORT="${ODOO_DEMO_LONGPOLLING_PORT:-8173}"

random_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
}

assert_demo_database() {
  case "$DB_NAME" in
    pmqms_demo) ;;
    pmqms_oliva_pilot|pmqms_dev|pmqms_test|postgres|template0|template1)
      echo "Refusing to operate on protected non-demo database: $DB_NAME" >&2
      exit 2
      ;;
    *)
      echo "Refusing to operate on unknown database '$DB_NAME'. This script only targets pmqms_demo." >&2
      exit 2
      ;;
  esac
}

init_secrets() {
  assert_demo_database
  mkdir -p "$CONFIG_DIR" "$BACKUP_DIR"
  chmod 755 "$SECRETS_DIR" "$CONFIG_DIR" "$BACKUP_DIR"
  if [[ ! -f "$PG_PASSWORD_FILE" ]]; then
    random_secret > "$PG_PASSWORD_FILE"
    chmod 600 "$PG_PASSWORD_FILE"
  fi
  if [[ ! -f "$ADMIN_PASSWORD_FILE" ]]; then
    random_secret > "$ADMIN_PASSWORD_FILE"
    chmod 600 "$ADMIN_PASSWORD_FILE"
  fi
  if [[ ! -f "$DEMO_ADMIN_PASSWORD_FILE" ]]; then
    random_secret > "$DEMO_ADMIN_PASSWORD_FILE"
    chmod 600 "$DEMO_ADMIN_PASSWORD_FILE"
  fi
  if [[ ! -f "$ENVIRONMENT_ID_FILE" ]]; then
    python3 -c 'import uuid; print(uuid.uuid4())' > "$ENVIRONMENT_ID_FILE"
    chmod 600 "$ENVIRONMENT_ID_FILE"
  fi
  mkdir -p "$PERSONA_PASSWORD_DIR"
  chmod 700 "$PERSONA_PASSWORD_DIR"
  declare -A persona_logins=(
    [quality-manager]="$DEMO_QUALITY_MANAGER_LOGIN"
    [quality-supervisor]="daniel.brooks.demo@perfectmatch.local"
    [document-controller]="maria.lewis.demo@perfectmatch.local"
    [internal-auditor]="james.carter.demo@perfectmatch.local"
    [process-owner]="emma.reed.demo@perfectmatch.local"
    [management-user]="michael.stone.demo@perfectmatch.local"
    [qms-viewer]="qms.viewer.demo@perfectmatch.local"
  )
  for persona in "${!persona_logins[@]}"; do
    if [[ ! -f "$PERSONA_PASSWORD_DIR/$persona" ]]; then
      random_secret > "$PERSONA_PASSWORD_DIR/$persona"
    fi
    chmod 600 "$PERSONA_PASSWORD_DIR/$persona"
  done
  cat > "$CONFIG_DIR/odoo.conf" <<EOF
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
admin_passwd = $(cat "$ADMIN_PASSWORD_FILE")
list_db = False
dbfilter = ^${DB_NAME}$
proxy_mode = True
workers = 0
max_cron_threads = 0
EOF
  chmod 600 "$CONFIG_DIR/odoo.conf"
}

prepare_runtime_permissions() {
  init_secrets
  chmod 644 "$PG_PASSWORD_FILE" "$CONFIG_DIR/odoo.conf" "$ENVIRONMENT_ID_FILE"
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

wait_postgres() {
  for _ in {1..60}; do
    if compose exec -T postgres-demo pg_isready -U odoo -d postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  compose logs postgres-demo >&2 || true
  echo "Demo PostgreSQL did not become ready in time." >&2
  exit 1
}

database_exists() {
  assert_demo_database
  prepare_runtime_permissions
  compose up -d postgres-demo >/dev/null
  wait_postgres
  compose exec -T postgres-demo psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1
}

run_odoo() {
  assert_demo_database
  prepare_runtime_permissions
  compose run --rm odoo-demo odoo "$@"
}

install_or_update() {
  assert_demo_database
  prepare_runtime_permissions
  compose up -d postgres-demo >/dev/null
  wait_postgres
  if database_exists; then
    run_odoo -d "$DB_NAME" --update "$DEMO_ADDONS" --stop-after-init
  else
    run_odoo -d "$DB_NAME" --init "$DEMO_ADDONS" --stop-after-init
  fi
  if [[ -f "$DEMO_LICENSE_FILE" ]]; then
    provision_license
  fi
  seed_demo
}

seed_demo() {
  assert_demo_database
  prepare_runtime_permissions
  local password
  password="$(cat "$DEMO_ADMIN_PASSWORD_FILE")"
  compose up -d postgres-demo >/dev/null
  wait_postgres
  compose run --rm \
    -e PMQMS_DEMO_DB="$DB_NAME" \
    -e PMQMS_DEMO_COMPANY_NAME="$DEMO_COMPANY_NAME" \
    -e PMQMS_DEMO_ADMIN_LOGIN="$DEMO_ADMIN_LOGIN" \
    -e PMQMS_DEMO_QUALITY_MANAGER_LOGIN="$DEMO_QUALITY_MANAGER_LOGIN" \
    -e PMQMS_DEMO_PERSONA_PASSWORD_DIR=/run/pmqms-demo-persona-passwords \
    -v "$PERSONA_PASSWORD_DIR:/run/pmqms-demo-persona-passwords:ro" \
    -e PMQMS_DEMO_ADMIN_PASSWORD="$password" \
    odoo-demo odoo shell -d "$DB_NAME" --log-level=error < "$REPO_ROOT/deployment/demo/seed_demo.py"
}

provision_license() {
  assert_demo_database
  prepare_runtime_permissions
  [[ -f "$DEMO_LICENSE_FILE" ]] || { echo "Demo license file not found: $DEMO_LICENSE_FILE" >&2; exit 1; }
  compose up -d postgres-demo >/dev/null
  wait_postgres
  chmod 644 "$DEMO_LICENSE_FILE"
  set +e
  compose run --rm -v "$DEMO_LICENSE_FILE:/run/pmqms-demo-license.pmql:ro" \
    odoo-demo odoo shell -d "$DB_NAME" --log-level=error < "$REPO_ROOT/deployment/demo/import_license.py"
  local rc=$?
  set -e
  chmod 600 "$DEMO_LICENSE_FILE"
  return "$rc"
}

validate_demo() {
  assert_demo_database
  prepare_runtime_permissions
  compose run --rm \
    -e PMQMS_DEMO_DB="$DB_NAME" \
    odoo-demo odoo shell -d "$DB_NAME" --log-level=error < "$REPO_ROOT/deployment/demo/validate_demo.py"
}

backup_demo() {
  assert_demo_database
  prepare_runtime_permissions
  compose up -d postgres-demo >/dev/null
  wait_postgres
  local stamp archive dump
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  archive="$BACKUP_DIR/${DB_NAME}-${stamp}.tar.gz"
  dump="$(mktemp -d)"
  compose exec -T postgres-demo pg_dump -U odoo -d "$DB_NAME" --format=custom > "$dump/database.dump"
  docker run --rm -v pmqms_demo_odoo_data:/var/lib/odoo:ro -v "$dump:/backup" alpine:3.20 sh -lc "cd /var/lib/odoo && tar -czf /backup/filestore.tar.gz filestore || true"
  tar -czf "$archive" -C "$dump" .
  rm -rf "$dump"
  echo "demo_backup=$archive"
}

reset_demo() {
  assert_demo_database
  prepare_runtime_permissions
  local expected_volumes="pmqms_demo_postgres pmqms_demo_odoo_data"
  [[ "$COMPOSE_FILE" == "$REPO_ROOT/deployment/docker/demo/compose.yml" ]] || { echo "Refusing reset: unexpected compose file." >&2; exit 2; }
  compose down --remove-orphans >/dev/null || true
  for volume in $expected_volumes; do
    case "$volume" in
      pmqms_demo_postgres|pmqms_demo_odoo_data) docker volume rm "$volume" >/dev/null 2>&1 || true ;;
      *) echo "Refusing reset: unexpected volume '$volume'." >&2; exit 2 ;;
    esac
  done
  install_or_update
}

health() {
  assert_demo_database
  prepare_runtime_permissions
  compose up -d >/dev/null
  local code="000"
  for _ in {1..60}; do
    code="$(curl -s -o /tmp/pmqms-demo-health.html -w '%{http_code}' "http://127.0.0.1:${ODOO_DEMO_HTTP_PORT}/web/login?db=${DB_NAME}" || true)"
    if [[ "$code" =~ ^(200|303|302)$ ]]; then
      break
    fi
    sleep 1
  done
  echo "demo_http=$code"
  echo "demo_url=http://192.168.68.151:${ODOO_DEMO_HTTP_PORT}/web/login?db=${DB_NAME}"
  compose ps
}

credentials() {
  init_secrets
  echo "demo_url=http://192.168.68.151:${ODOO_DEMO_HTTP_PORT}/web/login?db=${DB_NAME}"
  echo "demo_database=$DB_NAME"
  echo "demo_login=$DEMO_ADMIN_LOGIN"
  echo "demo_password_file=$DEMO_ADMIN_PASSWORD_FILE"
  echo "technical_admin_login=$DEMO_ADMIN_LOGIN"
  echo "quality_manager_login=$DEMO_QUALITY_MANAGER_LOGIN"
  echo "persona_password_dir=$PERSONA_PASSWORD_DIR"
  echo "quality_supervisor_login=daniel.brooks.demo@perfectmatch.local"
  echo "internal_auditor_login=james.carter.demo@perfectmatch.local"
  echo "process_owner_login=emma.reed.demo@perfectmatch.local"
  echo "management_user_login=michael.stone.demo@perfectmatch.local"
  echo "qms_viewer_login=qms.viewer.demo@perfectmatch.local"
}

usage() {
  cat <<'EOF'
Usage: ./deployment/scripts/odoo-demo.sh <command>

Commands:
  init-secrets   Generate local DEMO secrets outside Git.
  config         Validate the Docker Compose file.
  pull           Pull Odoo and PostgreSQL images.
  up             Start the DEMO stack.
  down           Stop the DEMO stack without removing volumes.
  ps             Show stack containers.
  logs           Follow Odoo logs.
  db-shell       Open psql in the demo Postgres container.
  shell          Open a shell in the demo Odoo container.
  init-db        Initialize pmqms_demo with base only.
  install        Install/update the full Perfect Match QMS demo stack and seed data.
  update         Update addons and reseed idempotently.
  reset-demo     Delete only demo volumes, rebuild pmqms_demo, install, and seed.
  seed-demo      Reseed fictional demo data idempotently.
  validate-demo  Validate expected fictional demo records and metrics.
  provision-license
                Import the externally issued Demo license from the secrets directory.
  backup         Create a demo-only backup archive.
  health         Validate demo HTTP and container status.
  credentials    Print demo URL/login and local password file path.
EOF
}

case "${1:-}" in
  init-secrets) init_secrets ;;
  config) prepare_runtime_permissions; compose config >/dev/null; echo "demo_compose=valid" ;;
  pull) prepare_runtime_permissions; compose pull ;;
  up) prepare_runtime_permissions; compose up -d ;;
  down) prepare_runtime_permissions; compose down ;;
  ps) prepare_runtime_permissions; compose ps ;;
  logs) prepare_runtime_permissions; compose logs -f odoo-demo ;;
  db-shell) prepare_runtime_permissions; compose up -d postgres-demo >/dev/null; wait_postgres; compose exec postgres-demo psql -U odoo -d "$DB_NAME" ;;
  shell) prepare_runtime_permissions; compose run --rm odoo-demo bash ;;
  init-db) run_odoo -d "$DB_NAME" --init base --stop-after-init ;;
  install) install_or_update ;;
  update) install_or_update ;;
  reset-demo) reset_demo ;;
  seed-demo) seed_demo ;;
  provision-license) provision_license ;;
  validate-demo) validate_demo ;;
  backup) backup_demo ;;
  health) health ;;
  credentials) credentials ;;
  *) usage; exit 1 ;;
esac
