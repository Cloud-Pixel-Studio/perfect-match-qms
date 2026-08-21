#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/pilot/compose.yml"
SECRETS_DIR="${PMQMS_OLIVA_PILOT_SECRETS_DIR:-/opt/perfect-match/secrets/odoo-oliva-pilot}"
CONFIG_DIR="$SECRETS_DIR/config"
PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"
ADMIN_PASSWORD_FILE="$SECRETS_DIR/odoo_admin_password"
DB_NAME="${PMQMS_OLIVA_PILOT_DB:-pmqms_oliva_pilot}"
OLIVA_COMPANY_NAME="${PMQMS_OLIVA_COMPANY_NAME:-Oliva Torras USA, Inc.}"
OLIVA_ORG_CODE="${PMQMS_OLIVA_ORG_CODE:-OTUS}"
MISSION10_ADDONS="pm_qms_core,pm_qms_documents,pm_qms_evidence,pm_qms_risk,pm_qms_ncr,pm_qms_capa,pm_qms_audit,pm_qms_kpi,pm_qms_management_review,pm_qms_implementation,pm_qms_pack_quality,pm_qms_migration"
MISSION11_ADDONS="$MISSION10_ADDONS,pm_qms_app"
MISSION14_ADDONS="$MISSION10_ADDONS,pm_qms_people,pm_qms_app"

export ODOO_OLIVA_PILOT_CONFIG_DIR="$CONFIG_DIR"
export ODOO_OLIVA_PILOT_PG_PASSWORD_FILE="$PG_PASSWORD_FILE"
export ODOO_OLIVA_PILOT_HTTP_BIND="${ODOO_OLIVA_PILOT_HTTP_BIND:-127.0.0.1}"
export ODOO_OLIVA_PILOT_HTTP_PORT="${ODOO_OLIVA_PILOT_HTTP_PORT:-8169}"
export ODOO_OLIVA_PILOT_LONGPOLLING_BIND="${ODOO_OLIVA_PILOT_LONGPOLLING_BIND:-127.0.0.1}"
export ODOO_OLIVA_PILOT_LONGPOLLING_PORT="${ODOO_OLIVA_PILOT_LONGPOLLING_PORT:-8172}"

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
dbfilter = ^${DB_NAME}$
proxy_mode = True
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

wait_postgres() {
  for _ in {1..60}; do
    if compose exec -T postgres-oliva-pilot pg_isready -U odoo -d postgres >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Oliva pilot PostgreSQL did not become ready in time." >&2
  exit 1
}

database_exists() {
  prepare_runtime_permissions
  compose up -d postgres-oliva-pilot >/dev/null
  wait_postgres
  compose exec -T postgres-oliva-pilot psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1
}

run_odoo() {
  prepare_runtime_permissions
  compose run --rm odoo-oliva-pilot odoo "$@"
}

refresh_pilot_web() {
  prepare_runtime_permissions
  compose restart odoo-oliva-pilot >/dev/null 2>&1 || compose up -d odoo-oliva-pilot >/dev/null
}

odoo_module_state() {
  local module="$1"
  run_odoo shell -d "$DB_NAME" --log-level=error <<PY | tail -n 1
module = env["ir.module.module"].search([("name", "=", "$module")], limit=1)
print(module.state if module else "missing")
PY
}

update_qms_stack() {
  run_odoo -d "$DB_NAME" --update "$MISSION10_ADDONS" --stop-after-init
  local people_state
  people_state="$(odoo_module_state pm_qms_people)"
  if [[ "$people_state" == "installed" ]]; then
    run_odoo -d "$DB_NAME" --update pm_qms_people --stop-after-init
  else
    run_odoo -d "$DB_NAME" --init pm_qms_people --without-demo=all --stop-after-init
  fi
  local app_state
  app_state="$(odoo_module_state pm_qms_app)"
  if [[ "$app_state" == "installed" ]]; then
    run_odoo -d "$DB_NAME" --update pm_qms_app --stop-after-init
  else
    run_odoo -d "$DB_NAME" --init pm_qms_app --without-demo=all --stop-after-init
  fi
}

configure_company() {
  run_odoo shell -d "$DB_NAME" <<PY
company = env.company
company.write({"name": "$OLIVA_COMPANY_NAME"})
env.cr.commit()
PY
}

configure_client() {
  run_odoo shell -d "$DB_NAME" <<PY
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import Command, fields

company = env.company
company.write({"name": "$OLIVA_COMPANY_NAME"})
qms_manager = env.ref("pm_qms_core.group_pm_qms_manager")
qms_admin = env.ref("pm_qms_core.group_pm_qms_administrator")
env.user.write({"group_ids": [Command.link(qms_manager.id), Command.link(qms_admin.id)]})
organization = env["pm.qms.organization"].search([
    ("code", "=", "$OLIVA_ORG_CODE"),
    ("company_id", "=", company.id),
], limit=1)
if not organization:
    organization = env["pm.qms.organization"].create({
        "name": "$OLIVA_COMPANY_NAME",
        "code": "$OLIVA_ORG_CODE",
        "company_id": company.id,
        "description": "Customer organization for Oliva Torras technical pilot. Operational details pending authorized customer input.",
    })
pack = env["pm.qms.framework.pack"].search([
    ("code", "=", "PM-QMS-QUALITY"),
    ("version", "=", "1.0"),
    ("company_id", "=", company.id),
    ("state", "=", "active"),
], limit=1)
if not pack:
    raise RuntimeError("PM-QMS-QUALITY v1.0 active pack was not found for the Oliva company.")
project = env["pm.qms.implementation.project"].search([
    ("name", "=", "Oliva Torras QMS Technical Pilot"),
    ("company_id", "=", company.id),
    ("organization_id", "=", organization.id),
], limit=1)
if not project:
    target = fields.Date.context_today(env["pm.qms.implementation.project"]) + relativedelta(months=3)
    project = env["pm.qms.implementation.project"].generate_from_wizard({
        "name": "Oliva Torras QMS Technical Pilot",
        "company_id": company.id,
        "organization_id": organization.id,
        "project_manager_id": env.user.id,
        "date_start": fields.Date.context_today(env["pm.qms.implementation.project"]),
        "target_date": target,
        "implementation_type": "migration",
        "pack_ids": pack.ids,
        "create_odoo_project": True,
        "notes": "TECHNICAL PILOT. Customer process owners, users, real documents, KPIs, and mapping review pending authorized input.",
    })
else:
    project.action_sync_framework()
print(f"organization={organization.code}:{organization.name}")
print(f"project={project.code}:{project.state}")
print(f"pack={pack.code}:{pack.version}:{pack.state}")
print(f"controls={len(project.implementation_control_ids)}")
print(f"tasks={len(project.generated_task_ids.filtered('pm_generated'))}")
print(f"required_evidence={project.required_evidence}")
env.cr.commit()
PY
}

run_readiness() {
  run_odoo shell -d "$DB_NAME" <<PY
project = env["pm.qms.implementation.project"].search([
    ("name", "=", "Oliva Torras QMS Technical Pilot"),
], limit=1)
if not project:
    raise RuntimeError("Oliva pilot implementation project was not found.")
action = project.action_run_readiness_assessment()
assessment = env["pm.qms.readiness.assessment"].search([
    ("implementation_project_id", "=", project.id),
], limit=1, order="id desc")
print(f"assessment={assessment.code}:{assessment.readiness_percent:.2f}")
print(f"total={assessment.total_controls} applicable={assessment.applicable_controls} na={assessment.not_applicable_controls} ready={assessment.ready_controls} gaps={assessment.gap_controls}")
env.cr.commit()
PY
}

health() {
  prepare_runtime_permissions
  compose up -d >/dev/null
  local code="000"
  for _ in {1..60}; do
    code="$(curl -s -o /tmp/pmqms-oliva-pilot-health.html -w '%{http_code}' "http://127.0.0.1:${ODOO_OLIVA_PILOT_HTTP_PORT}/web/login?db=${DB_NAME}" || true)"
    if [[ "$code" =~ ^(200|303|302)$ ]]; then
      break
    fi
    sleep 1
  done
  echo "oliva_pilot_http=$code"
  compose ps
}

usage() {
  cat <<'EOF'
Usage: ./deployment/scripts/odoo-pilot.sh <command>

Commands:
  init-secrets       Generate pilot secrets outside Git.
  config             Validate pilot Docker Compose.
  pull               Pull runtime images.
  up                 Start pilot stack.
  down               Stop pilot stack.
  ps                 Show pilot containers.
  logs               Follow Odoo pilot logs.
  db-shell           Open psql in pilot PostgreSQL.
  shell              Open bash in pilot Odoo container.
  init-db            Initialize pilot database with base.
  configure-company  Rename initial Odoo company to Oliva Torras USA, Inc.
  install            Install full QMS stack including people and the application shell.
  update             Update full QMS stack including people and the application shell.
  configure-client   Create/verify Oliva organization and generated project.
  run-readiness      Run a historical readiness assessment.
  health             Validate local pilot HTTP and container status.
EOF
}

case "${1:-}" in
  init-secrets)
    init_secrets
    echo "Oliva pilot secrets initialized in $SECRETS_DIR"
    ;;
  config)
    init_secrets
    compose config >/dev/null
    echo "Oliva pilot Compose configuration is valid."
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
  ps)
    init_secrets
    compose ps
    ;;
  logs)
    init_secrets
    compose logs -f odoo-oliva-pilot
    ;;
  db-shell)
    prepare_runtime_permissions
    compose exec postgres-oliva-pilot psql -U odoo -d postgres
    ;;
  shell)
    prepare_runtime_permissions
    compose exec odoo-oliva-pilot bash
    ;;
  init-db)
    run_odoo -d "$DB_NAME" --init base --without-demo=all --stop-after-init
    ;;
  configure-company)
    configure_company
    ;;
  install)
    prepare_runtime_permissions
    if database_exists; then
      update_qms_stack
    else
      run_odoo -d "$DB_NAME" --init base --without-demo=all --stop-after-init
      configure_company
      run_odoo -d "$DB_NAME" --init "$MISSION14_ADDONS" --without-demo=all --stop-after-init
    fi
    ;;
  update)
    update_qms_stack
    refresh_pilot_web
    ;;
  configure-client)
    configure_client
    ;;
  run-readiness)
    run_readiness
    ;;
  health)
    health
    ;;
  ""|help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $1" >&2
    usage >&2
    exit 2
    ;;
esac
