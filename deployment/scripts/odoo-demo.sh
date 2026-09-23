#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/demo/compose.yml"
MODULES_FILE="$REPO_ROOT/deployment/customer/modules.txt"
PMQMS_DEMO_INSTANCE="${PMQMS_DEMO_INSTANCE:-demo}"
validate_instance_name() {
  [[ "$PMQMS_DEMO_INSTANCE" =~ ^[a-z][a-z0-9-]{0,23}$ ]] || {
    echo "Invalid PMQMS_DEMO_INSTANCE; use 1-24 lowercase letters, digits, or hyphens, starting with a letter." >&2
    return 2
  }
  [[ "$PMQMS_DEMO_INSTANCE" != *..* ]] || { echo "Invalid instance traversal sequence." >&2; return 2; }
}
validate_instance_name || exit $?
INSTANCE_SUFFIX="${PMQMS_DEMO_INSTANCE//-/_}"
EXPECTED_DB_NAME="pmqms_${INSTANCE_SUFFIX}"
EXPECTED_PROJECT_NAME="pmqms-${PMQMS_DEMO_INSTANCE}"
EXPECTED_POSTGRES_VOLUME="pmqms_${INSTANCE_SUFFIX}_postgres"
EXPECTED_ODOO_VOLUME="pmqms_${INSTANCE_SUFFIX}_odoo_data"
EXPECTED_NETWORK="pmqms_${INSTANCE_SUFFIX}_network"
if [[ "$PMQMS_DEMO_INSTANCE" == demo ]]; then
  DEFAULT_SECRETS_DIR="/opt/perfect-match/secrets/odoo-demo"
  DEFAULT_BACKUP_DIR="/opt/perfect-match/backups/odoo-demo"
  DEFAULT_HTTP_PORT=8170
  DEFAULT_LONGPOLLING_PORT=8173
elif [[ "$PMQMS_DEMO_INSTANCE" == demo2 ]]; then
  DEFAULT_SECRETS_DIR="/opt/perfect-match/secrets/odoo-demo-isolated"
  DEFAULT_BACKUP_DIR="/opt/perfect-match/backups/odoo-demo-isolated"
  DEFAULT_HTTP_PORT=8171
  DEFAULT_LONGPOLLING_PORT=8174
else
  DEFAULT_SECRETS_DIR="/opt/perfect-match/secrets/odoo-${PMQMS_DEMO_INSTANCE}"
  DEFAULT_BACKUP_DIR="/opt/perfect-match/backups/odoo-${PMQMS_DEMO_INSTANCE}"
  DEFAULT_HTTP_PORT=8170
  DEFAULT_LONGPOLLING_PORT=8173
fi
SECRETS_DIR="${PMQMS_DEMO_SECRETS_DIR:-$DEFAULT_SECRETS_DIR}"
if [[ "$PMQMS_DEMO_INSTANCE" == demo ]]; then
  DEFAULT_RUNTIME_LOCK_FILE="$REPO_ROOT/deployment/runtime/runtime-lock.json"
else
  DEFAULT_RUNTIME_LOCK_FILE="$SECRETS_DIR/runtime/runtime-lock.json"
fi
RUNTIME_LOCK_FILE="${PMQMS_DEMO_RUNTIME_LOCK_FILE:-$DEFAULT_RUNTIME_LOCK_FILE}"
CONFIG_DIR="$SECRETS_DIR/config"
PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"
ADMIN_PASSWORD_FILE="$SECRETS_DIR/odoo_admin_password"
DEMO_ADMIN_PASSWORD_FILE="$SECRETS_DIR/demo_admin_password"
PERSONA_PASSWORD_DIR="$SECRETS_DIR/personas"
ENVIRONMENT_ID_FILE="$CONFIG_DIR/environment_id"
ACTIVATION_DIR="${PMQMS_DEMO_ACTIVATION_DIR:-$SECRETS_DIR/activation}"
DEMO_LICENSE_FILE="${PMQMS_DEMO_LICENSE_FILE:-$SECRETS_DIR/demo_license.pmql}"
BACKUP_DIR="${PMQMS_DEMO_BACKUP_DIR:-$DEFAULT_BACKUP_DIR}"
DB_NAME="${PMQMS_DEMO_DB:-$EXPECTED_DB_NAME}"
COMPOSE_PROJECT_NAME="${PMQMS_DEMO_COMPOSE_PROJECT:-$EXPECTED_PROJECT_NAME}"
POSTGRES_VOLUME="${PMQMS_DEMO_POSTGRES_VOLUME:-$EXPECTED_POSTGRES_VOLUME}"
ODOO_DATA_VOLUME="${PMQMS_DEMO_ODOO_VOLUME:-$EXPECTED_ODOO_VOLUME}"
DEMO_NETWORK="${PMQMS_DEMO_NETWORK:-$EXPECTED_NETWORK}"
DEMO_COMPANY_NAME="${PMQMS_DEMO_COMPANY_NAME:-Apex Precision Systems, Inc.}"
DEMO_ADMIN_LOGIN="${PMQMS_DEMO_ADMIN_LOGIN:-admin}"
DEMO_QUALITY_MANAGER_LOGIN="${PMQMS_DEMO_QUALITY_MANAGER_LOGIN:-olivia.parker.demo@perfectmatch.local}"

runtime_image() { jq -er ".${1}.image" "$RUNTIME_LOCK_FILE"; }
load_runtime_lock() {
  [[ -s "$RUNTIME_LOCK_FILE" ]] || { echo "Runtime lock is missing: $RUNTIME_LOCK_FILE" >&2; return 1; }
  export PMQMS_ODOO_IMAGE="$(runtime_image odoo)"
  export PMQMS_POSTGRES_IMAGE="$(runtime_image postgres)"
  export PMQMS_ALPINE_IMAGE="$(runtime_image alpine)"
}
runtime_verify() {
  load_runtime_lock
  for image in "$PMQMS_ODOO_IMAGE" "$PMQMS_POSTGRES_IMAGE" "$PMQMS_ALPINE_IMAGE"; do
    docker image inspect "$image" >/dev/null 2>&1 || {
      echo "ERROR: approved runtime image is not available locally: $image" >&2
      echo "Run: $0 runtime-fetch" >&2
      return 1
    }
  done
}
module_list() { paste -sd, <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$MODULES_FILE"); }
DEMO_ADDONS="${PMQMS_DEMO_ADDONS:-$(module_list)}"

export ODOO_DEMO_CONFIG_DIR="$CONFIG_DIR"
export ODOO_DEMO_PG_PASSWORD_FILE="$PG_PASSWORD_FILE"
export ODOO_DEMO_HTTP_BIND="${ODOO_DEMO_HTTP_BIND:-0.0.0.0}"
export ODOO_DEMO_HTTP_PORT="${ODOO_DEMO_HTTP_PORT:-$DEFAULT_HTTP_PORT}"
export ODOO_DEMO_LONGPOLLING_BIND="${ODOO_DEMO_LONGPOLLING_BIND:-0.0.0.0}"
export ODOO_DEMO_LONGPOLLING_PORT="${ODOO_DEMO_LONGPOLLING_PORT:-$DEFAULT_LONGPOLLING_PORT}"

safe_absolute_path() {
  local label="$1" value="$2"
  [[ "$value" == /* && "$value" =~ ^/[A-Za-z0-9_./-]+$ ]] || {
    echo "Invalid $label path; an absolute path using only letters, digits, dot, underscore, slash, and hyphen is required." >&2
    return 2
  }
  [[ ! "/$value/" == *"/../"* ]] || { echo "Invalid $label path traversal." >&2; return 2; }
}

path_is_within() {
  local child parent
  child="$(realpath -m -- "$1")"
  parent="$(realpath -m -- "$2")"
  [[ "$child" == "$parent" || "$child" == "$parent"/* ]]
}

validate_effective_configuration() {
  local canonical_secrets canonical_backups canonical_activation canonical_license canonical_lock
  safe_absolute_path secrets "$SECRETS_DIR"
  safe_absolute_path backups "$BACKUP_DIR"
  safe_absolute_path activation "$ACTIVATION_DIR"
  safe_absolute_path license "$DEMO_LICENSE_FILE"
  safe_absolute_path runtime-lock "$RUNTIME_LOCK_FILE"
  [[ "$DB_NAME" =~ ^[a-z][a-z0-9_]{0,62}$ && "$DB_NAME" == "$EXPECTED_DB_NAME" ]] || {
    echo "Database must be the unique instance database '$EXPECTED_DB_NAME'." >&2; return 2;
  }
  [[ "$COMPOSE_PROJECT_NAME" == "$EXPECTED_PROJECT_NAME" ]] || { echo "Compose project must be '$EXPECTED_PROJECT_NAME'." >&2; return 2; }
  [[ "$POSTGRES_VOLUME" == "$EXPECTED_POSTGRES_VOLUME" && "$ODOO_DATA_VOLUME" == "$EXPECTED_ODOO_VOLUME" && "$DEMO_NETWORK" == "$EXPECTED_NETWORK" ]] || {
    echo "Volumes and network must use names derived from instance '$PMQMS_DEMO_INSTANCE'." >&2; return 2;
  }
  [[ "$ODOO_DEMO_HTTP_PORT" =~ ^[0-9]{1,5}$ && "$ODOO_DEMO_HTTP_PORT" -ge 1 && "$ODOO_DEMO_HTTP_PORT" -le 65535 ]] || { echo "Invalid Demo HTTP port." >&2; return 2; }
  [[ "$ODOO_DEMO_LONGPOLLING_PORT" =~ ^[0-9]{1,5}$ && "$ODOO_DEMO_LONGPOLLING_PORT" -ge 1 && "$ODOO_DEMO_LONGPOLLING_PORT" -le 65535 && "$ODOO_DEMO_LONGPOLLING_PORT" != "$ODOO_DEMO_HTTP_PORT" ]] || { echo "Invalid Demo longpolling port." >&2; return 2; }
  canonical_secrets="$(realpath -m -- "$SECRETS_DIR")"
  canonical_backups="$(realpath -m -- "$BACKUP_DIR")"
  canonical_activation="$(realpath -m -- "$ACTIVATION_DIR")"
  canonical_license="$(realpath -m -- "$DEMO_LICENSE_FILE")"
  canonical_lock="$(realpath -m -- "$RUNTIME_LOCK_FILE")"
  path_is_within "$canonical_activation" "$canonical_secrets" || { echo "Activation path must remain inside the instance secrets directory." >&2; return 2; }
  path_is_within "$canonical_license" "$canonical_secrets" || { echo "License path must remain inside the instance secrets directory." >&2; return 2; }
  [[ "$canonical_secrets" != "$canonical_backups" && "$canonical_secrets" != "$canonical_backups"/* && "$canonical_backups" != "$canonical_secrets"/* ]] || {
    echo "Secrets and backup paths must be separate, non-overlapping roots." >&2; return 2;
  }
  if [[ "$PMQMS_DEMO_INSTANCE" != demo ]]; then
    if path_is_within "$canonical_secrets" /opt/perfect-match/secrets/odoo-demo || path_is_within /opt/perfect-match/secrets/odoo-demo "$canonical_secrets"; then
      echo "Non-default instances cannot overlap the original Demo secrets path." >&2; return 2
    fi
    if path_is_within "$canonical_backups" /opt/perfect-match/backups/odoo-demo || path_is_within /opt/perfect-match/backups/odoo-demo "$canonical_backups"; then
      echo "Non-default instances cannot overlap the original Demo backup path." >&2; return 2
    fi
    [[ "$DB_NAME" != pmqms_demo ]] || { echo "Non-default instances cannot use pmqms_demo." >&2; return 2; }
  fi
  if [[ "$PMQMS_DEMO_INSTANCE" != demo2 ]]; then
    if path_is_within "$canonical_secrets" /opt/perfect-match/secrets/odoo-demo-isolated || path_is_within /opt/perfect-match/secrets/odoo-demo-isolated "$canonical_secrets"; then
      echo "Instances other than demo2 cannot overlap the Demo2 secrets path." >&2; return 2
    fi
    if path_is_within "$canonical_backups" /opt/perfect-match/backups/odoo-demo-isolated || path_is_within /opt/perfect-match/backups/odoo-demo-isolated "$canonical_backups"; then
      echo "Instances other than demo2 cannot overlap the Demo2 backup path." >&2; return 2
    fi
  fi
  if [[ "$PMQMS_DEMO_INSTANCE" == demo ]]; then
    [[ "$canonical_lock" == "$REPO_ROOT"/* ]] || { echo "Demo runtime lock must remain inside this checkout." >&2; return 2; }
  else
    path_is_within "$canonical_lock" "$canonical_secrets" || { echo "Runtime lock must remain inside the selected instance secrets directory." >&2; return 2; }
  fi
  export PMQMS_DEMO_INSTANCE PMQMS_DEMO_DB="$DB_NAME" PMQMS_DEMO_COMPOSE_PROJECT="$COMPOSE_PROJECT_NAME"
  export PMQMS_DEMO_POSTGRES_VOLUME="$POSTGRES_VOLUME" PMQMS_DEMO_ODOO_VOLUME="$ODOO_DATA_VOLUME" PMQMS_DEMO_NETWORK="$DEMO_NETWORK"
  export COMPOSE_PROJECT_NAME ODOO_DEMO_CONFIG_DIR="$CONFIG_DIR" ODOO_DEMO_PG_PASSWORD_FILE="$PG_PASSWORD_FILE"
}

show_effective_configuration() {
  printf 'demo_instance=%s\ndemo_database=%s\ncompose_project=%s\nsecrets_dir=%s\nactivation_dir=%s\nlicense_file=%s\nbackup_dir=%s\nruntime_lock=%s\npostgres_volume=%s\nodoo_volume=%s\nnetwork=%s\nhttp_port=%s\nlongpolling_port=%s\n' \
    "$PMQMS_DEMO_INSTANCE" "$DB_NAME" "$COMPOSE_PROJECT_NAME" "$SECRETS_DIR" "$ACTIVATION_DIR" "$DEMO_LICENSE_FILE" "$BACKUP_DIR" "$RUNTIME_LOCK_FILE" "$POSTGRES_VOLUME" "$ODOO_DATA_VOLUME" "$DEMO_NETWORK" "$ODOO_DEMO_HTTP_PORT" "$ODOO_DEMO_LONGPOLLING_PORT"
}

validate_instance_root_owner() {
  local root="$1" default_root="$2" label="$3" marker="$1/.pmqms-demo-instance-owner" owner
  if [[ -e "$marker" || -L "$marker" ]]; then
    [[ -f "$marker" && ! -L "$marker" ]] || { echo "$label ownership marker is not a regular file." >&2; return 2; }
    IFS= read -r owner < "$marker" || owner=""
    [[ "$owner" == "$PMQMS_DEMO_INSTANCE" ]] || {
      echo "$label path is already owned by a different Demo instance." >&2; return 2;
    }
    return 0
  fi
  if [[ "$(realpath -m -- "$root")" != "$(realpath -m -- "$default_root")" ]] &&
      find "$root" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    echo "$label custom path is non-empty and has no PMQMS instance ownership marker." >&2
    return 2
  fi
}

claim_instance_root() {
  local root="$1" label="$2" marker="$1/.pmqms-demo-instance-owner" owner
  if [[ ! -e "$marker" ]]; then
    if ! (set -o noclobber; printf '%s\n' "$PMQMS_DEMO_INSTANCE" > "$marker") 2>/dev/null; then
      [[ -f "$marker" && ! -L "$marker" ]] || { echo "Could not atomically claim $label path." >&2; return 2; }
      IFS= read -r owner < "$marker" || owner=""
      [[ "$owner" == "$PMQMS_DEMO_INSTANCE" ]] || { echo "$label path was concurrently claimed by another instance." >&2; return 2; }
    fi
    chmod 600 "$marker"
  fi
}

random_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
}

assert_demo_database() {
  validate_effective_configuration
}

init_secrets() {
  assert_demo_database
  show_effective_configuration
  mkdir -p "$SECRETS_DIR" "$BACKUP_DIR"
  validate_instance_root_owner "$SECRETS_DIR" "$DEFAULT_SECRETS_DIR" "Secrets"
  validate_instance_root_owner "$BACKUP_DIR" "$DEFAULT_BACKUP_DIR" "Backup"
  claim_instance_root "$SECRETS_DIR" "secrets"
  claim_instance_root "$BACKUP_DIR" "backup"
  mkdir -p "$CONFIG_DIR" "$ACTIVATION_DIR"
  if [[ "$PMQMS_DEMO_INSTANCE" != demo && ! -f "$RUNTIME_LOCK_FILE" ]]; then
    mkdir -p "$(dirname "$RUNTIME_LOCK_FILE")"
    cp "$REPO_ROOT/deployment/runtime/runtime-lock.json" "$RUNTIME_LOCK_FILE"
    chmod 644 "$RUNTIME_LOCK_FILE"
  fi
  chmod 755 "$SECRETS_DIR" "$CONFIG_DIR" "$BACKUP_DIR" "$ACTIVATION_DIR"
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
  runtime_verify
  chmod 644 "$PG_PASSWORD_FILE" "$CONFIG_DIR/odoo.conf" "$ENVIRONMENT_ID_FILE"
}

compose() {
  validate_effective_configuration
  load_runtime_lock
  docker compose --project-name "$COMPOSE_PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
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
    # --init is idempotent for installed modules and also installs new modules
    # added to the canonical manifest during a release upgrade.
    run_odoo -d "$DB_NAME" --init "$DEMO_ADDONS" --update "$DEMO_ADDONS" --stop-after-init
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
  # Persona files remain operator-owned (0700/0600). The one-shot seed runs
  # as container root only to read the read-only secret mount; Odoo itself
  # continues to run as its normal unprivileged container user.
  compose run --rm --user root \
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
  docker run --rm -v "$ODOO_DATA_VOLUME:/var/lib/odoo:ro" -v "$dump:/backup" "$PMQMS_ALPINE_IMAGE" sh -lc "cd /var/lib/odoo && tar -czf /backup/filestore.tar.gz filestore || true"
  tar -czf "$archive" -C "$dump" .
  rm -rf "$dump"
  echo "demo_backup=$archive"
}

reset_demo() {
  assert_demo_database
  prepare_runtime_permissions
  local expected_volumes="$POSTGRES_VOLUME $ODOO_DATA_VOLUME"
  [[ "$COMPOSE_FILE" == "$REPO_ROOT/deployment/docker/demo/compose.yml" ]] || { echo "Refusing reset: unexpected compose file." >&2; exit 2; }
  compose down --remove-orphans >/dev/null || true
  for volume in $expected_volumes; do
    case "$volume" in
      "$POSTGRES_VOLUME"|"$ODOO_DATA_VOLUME") docker volume rm "$volume" >/dev/null 2>&1 || true ;;
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
    code="$(curl -s -o "${TMPDIR:-/tmp}/pmqms-${PMQMS_DEMO_INSTANCE}-health.html" -w '%{http_code}' "http://127.0.0.1:${ODOO_DEMO_HTTP_PORT}/web/login?db=${DB_NAME}" || true)"
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
  show-config    Print validated effective instance paths and resource names without modifying them.
  init-secrets   Generate local Demo secrets outside Git.
  config         Validate the Docker Compose file for the selected instance.
  pull           Explicitly fetch the exact locked runtime images.
  runtime-images
                Print the approved immutable runtime references.
  runtime-verify
                Verify locked runtime images locally without registry access.
  runtime-fetch
                Explicitly fetch the exact locked runtime images.
  up             Start the DEMO stack.
  down           Stop the DEMO stack without removing volumes.
  ps             Show stack containers.
  logs           Follow Odoo logs.
  db-shell       Open psql in the demo Postgres container.
  shell          Open a shell in the demo Odoo container.
  init-db        Initialize the selected instance database with base only.
  install        Install/update the full Perfect Match QMS demo stack and seed data.
  update         Update addons and reseed idempotently.
  reset-demo     Delete only the selected instance volumes, reinstall, and seed.
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
  show-config) validate_effective_configuration; show_effective_configuration ;;
  init-secrets) init_secrets ;;
  config) init_secrets; load_runtime_lock; compose config >/dev/null; echo "demo_compose=valid" ;;
  pull) init_secrets; load_runtime_lock; docker pull "$PMQMS_ODOO_IMAGE"; docker pull "$PMQMS_POSTGRES_IMAGE"; docker pull "$PMQMS_ALPINE_IMAGE"; prepare_runtime_permissions ;;
  runtime-images) load_runtime_lock; printf 'odoo_image=%s\npostgres_image=%s\nalpine_image=%s\n' "$PMQMS_ODOO_IMAGE" "$PMQMS_POSTGRES_IMAGE" "$PMQMS_ALPINE_IMAGE" ;;
  runtime-verify) runtime_verify; echo "DEMO_RUNTIME_VERIFY=PASS" ;;
  runtime-fetch) init_secrets; load_runtime_lock; docker pull "$PMQMS_ODOO_IMAGE"; docker pull "$PMQMS_POSTGRES_IMAGE"; docker pull "$PMQMS_ALPINE_IMAGE"; prepare_runtime_permissions ;;
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
