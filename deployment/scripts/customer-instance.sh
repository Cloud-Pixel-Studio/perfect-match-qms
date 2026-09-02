#!/usr/bin/env bash
set -euo pipefail

# Operator-controlled customer foundation. It never targets Demo or DEV.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTANCE_ROOT_BASE="${PMQMS_CUSTOMER_INSTANCE_ROOT:-/opt/perfect-match/instances}"
DEFAULT_RELEASE="${PMQMS_CUSTOMER_RELEASE:-v1.0.0-rc7}"
MODULES_FILE="$REPO_ROOT/deployment/customer/modules.txt"
COMPOSE_TEMPLATE="$REPO_ROOT/deployment/docker/customer/compose.yml.template"
ODOO_TEMPLATE="$REPO_ROOT/deployment/docker/customer/odoo.conf.template"
RUNTIME_LOCK_FILE="$REPO_ROOT/deployment/runtime/runtime-lock.json"
BACKUP_TOOL="$REPO_ROOT/tools/backup/m29_backup.py"

die() { echo "ERROR: $*" >&2; exit 2; }
log() { echo "CUSTOMER: $*"; }
random_secret() { openssl rand -base64 48 | tr -d '\n'; }
slug_ok() { [[ "$1" =~ ^[a-z0-9]+([a-z0-9-]*[a-z0-9])?$ ]]; }
instance_dir() { echo "$INSTANCE_ROOT_BASE/$1"; }
new_temp_dir() { mktemp -d "${TMPDIR:-/tmp}/pmqms-customer-instance.XXXXXX"; }
cleanup_temp_dir() {
  local temp_dir="${1:-}" temp_root="${TMPDIR:-/tmp}"
  [[ -n "$temp_dir" && "$temp_dir" == "$temp_root"/pmqms-customer-instance.* ]] || return 0
  [[ -d "$temp_dir" ]] || return 0
  rm -rf -- "$temp_dir"
}
validate_runtime_lock() {
  local lock="$1"
  [[ -s "$lock" ]] || die "runtime lock missing: $lock"
  jq -e '
    .schema_version == 1 and
    (.odoo.image | test("^odoo:[^@]+@sha256:[0-9a-f]{64}$")) and
    (.postgres.image | test("^postgres:[^@]+@sha256:[0-9a-f]{64}$")) and
    (.alpine.image | test("^alpine:[^@]+@sha256:[0-9a-f]{64}$")) and
    (.odoo.digest | startswith("sha256:")) and
    (.postgres.digest | startswith("sha256:")) and
    (.alpine.digest | startswith("sha256:"))
  ' "$lock" >/dev/null || die "invalid runtime lock: $lock"
}
load_runtime_for_root() {
  local root="$1"
  RUNTIME_LOCK_PATH="$root/config/runtime-lock.json"
  validate_runtime_lock "$RUNTIME_LOCK_PATH"
  ODOO_IMAGE="$(jq -er '.odoo.image' "$RUNTIME_LOCK_PATH")"
  POSTGRES_IMAGE="$(jq -er '.postgres.image' "$RUNTIME_LOCK_PATH")"
  ALPINE_IMAGE="$(jq -er '.alpine.image' "$RUNTIME_LOCK_PATH")"
}
runtime_verify_lock() {
  local lock="$1" image
  validate_runtime_lock "$lock"
  for image in "$(jq -er '.odoo.image' "$lock")" "$(jq -er '.postgres.image' "$lock")" "$(jq -er '.alpine.image' "$lock")"; do
    docker image inspect "$image" >/dev/null 2>&1 || die "approved runtime image is not available locally: $image; run runtime-fetch"
  done
}
runtime_images() {
  validate_runtime_lock "$RUNTIME_LOCK_FILE"
  jq -r 'to_entries[] | select((.value | type) == "object" and .value.image) | "\(.key)_image=\(.value.image)"' "$RUNTIME_LOCK_FILE"
}
runtime_verify() {
  local lock="$RUNTIME_LOCK_FILE"
  if [[ $# -gt 0 ]]; then
    local root; root="$(require_instance "$1")"; lock="$root/config/runtime-lock.json"
  fi
  runtime_verify_lock "$lock"
}
runtime_fetch() {
  local lock="$RUNTIME_LOCK_FILE"
  if [[ $# -gt 0 ]]; then
    local root; root="$(require_instance "$1")"; lock="$root/config/runtime-lock.json"
  fi
  validate_runtime_lock "$lock"
  docker pull "$(jq -er '.odoo.image' "$lock")"
  docker pull "$(jq -er '.postgres.image' "$lock")"
  docker pull "$(jq -er '.alpine.image' "$lock")"
}
update_manifest_runtime() {
  local root="$1" lock="$2"
  local manifest="$root/config/deployment-manifest.json"
  validate_runtime_lock "$lock"
  jq --arg schema "$(jq -r '.schema_version' "$lock")" \
    --arg lock_sha "$(sha256sum "$lock" | awk '{print $1}')" \
    --arg odoo "$(jq -r '.odoo.image' "$lock")" \
    --arg odoo_digest "$(jq -r '.odoo.digest' "$lock")" \
    --arg postgres "$(jq -r '.postgres.image' "$lock")" \
    --arg postgres_digest "$(jq -r '.postgres.digest' "$lock")" \
    '.runtime_lock_schema=($schema|tonumber) | .runtime_lock_sha256=$lock_sha | .odoo_image=$odoo | .odoo_digest=$odoo_digest | .postgres_image=$postgres | .postgres_digest=$postgres_digest' \
    "$manifest" > "$manifest.tmp"
  mv "$manifest.tmp" "$manifest"
  chmod 600 "$manifest"
}
runtime_manifest_gate() {
  local root="$1"
  local lock="$root/config/runtime-lock.json" manifest="$root/config/deployment-manifest.json" product="$root/config/product-manifest.json"
  load_runtime_for_root "$root"
  runtime_verify_lock "$lock"
  [[ -s "$manifest" && -s "$product" ]] || die "deployment/product manifests are missing"
  local lock_sha; lock_sha="$(sha256sum "$lock" | awk '{print $1}')"
  jq -e --arg sha "$lock_sha" --arg odoo "$ODOO_IMAGE" --arg postgres "$POSTGRES_IMAGE" \
    '(.runtime_lock_schema == 1) and (.runtime_lock_sha256 == $sha) and (.odoo_image == $odoo) and (.postgres_image == $postgres)' "$manifest" >/dev/null || die "deployment manifest runtime identity mismatch"
  jq -e --arg sha "$lock_sha" --arg odoo "$ODOO_IMAGE" --arg postgres "$POSTGRES_IMAGE" \
    '(.runtime_lock_sha256 == $sha) and (.odoo_image == $odoo) and (.postgres_image == $postgres)' "$product" >/dev/null || die "product bundle runtime identity mismatch"
}
protected_slug() {
  case "$1" in pmqms_demo|pmqms_dev|pmqms_test|pmqms_oliva_pilot|demo|dev|oliva*) return 0;; esac
  return 1
}
require_instance() {
  local slug="$1" root
  slug_ok "$slug" || die "invalid instance slug: $slug"
  root="$(instance_dir "$slug")"
  [[ -f "$root/config/instance.env" ]] || die "instance not initialized: $slug"
  echo "$root"
}
load_instance() {
  local root="$1"
  # shellcheck disable=SC1091
  . "$root/config/instance.env"
  [[ "${INSTANCE_SLUG:-}" == "$(basename "$root")" ]] || die "instance manifest mismatch"
  [[ "${ENVIRONMENT_TYPE:-}" == customer || "${ENVIRONMENT_TYPE:-}" == test ]] || die "unsupported environment type"
}
compose() {
  local root="$1"; shift
  load_runtime_for_root "$root"
  prepare_permissions "$root"
  docker compose --project-name "pmqms-customer-${INSTANCE_SLUG}" --env-file "$root/config/instance.env" -f "$root/runtime/compose.yml" "$@"
}
prepare_permissions() {
  local root="$1"
  load_runtime_for_root "$root"
  runtime_verify_lock "$RUNTIME_LOCK_PATH"
  docker run --rm --user root -v "$root/config:/config" -v "$root/secrets:/secrets" -v "$root/license:/license" -v "$root/activation:/activation" "$ODOO_IMAGE" sh -lc 'chown 100:101 /config/odoo.conf /config/environment_id /secrets/postgres_password /license /activation 2>/dev/null || true; chmod 600 /config/odoo.conf /secrets/postgres_password; chmod 644 /config/environment_id 2>/dev/null || true; chmod 700 /license 2>/dev/null || true; chmod 755 /activation 2>/dev/null || true'
}
module_list() { paste -sd, <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$MODULES_FILE"); }
read_option() { local flag="$1"; shift; while [[ $# -gt 0 ]]; do [[ "$1" == "$flag" ]] && { echo "${2:-}"; return 0; }; shift; done; return 1; }

usage() {
  cat <<'EOF'
Usage: customer-instance.sh <command> [arguments]
  init <slug> [--type customer|test] [--domain domain] [--release tag] [--port port]
  provision <slug> --bundle bundle.tar.gz [--type customer|test] [--port port]
  credentials|config|up|down|health <slug>
  runtime-images [<slug>]
  runtime-verify [<slug>]
  runtime-fetch [<slug>]
  bootstrap <slug>
  activation-request <slug>
  import-license <slug> <license.pmql>
  license-status <slug>
  bootstrap-customer <slug> --company-name name --company-code code --user-login login --user-name name [--user-password-file file]
  create-site <slug> --code code --name name --type site-type
  backup <slug> [--recipient-file file] [--off-host-dir dir] [--class intraday|daily|monthly]
  restore-validate <slug> <backup.tar.age> [--identity-file file] [--verification-file file]
  retention <slug> [--now utc] [--apply]
  upgrade <slug> --to <release-tag> [--approve-runtime-change]
  customer-ready <slug>
  bundle --output file.tar.gz [--release tag]
  destroy <slug> --confirm-ephemeral

All state is kept outside Git. Customer and test lifecycles are guarded by
environment type and protected-name checks.
EOF
}

write_manifest() {
  local root="$1"
  load_runtime_for_root "$root"
  cat > "$root/config/instance.env" <<EOF
INSTANCE_SLUG=$INSTANCE_SLUG
ENVIRONMENT_TYPE=$ENVIRONMENT_TYPE
PRODUCT_VERSION=$PRODUCT_VERSION
DOMAIN=$DOMAIN
DATABASE_NAME=$DATABASE_NAME
HTTP_PORT=$HTTP_PORT
ENVIRONMENT_ID_FILE=$root/config/environment_id
INSTANCE_ROOT=$root
EOF
  chmod 600 "$root/config/instance.env"
  cat > "$root/config/deployment-manifest.json" <<EOF
{
  "instance_slug": "${INSTANCE_SLUG}",
  "environment_type": "${ENVIRONMENT_TYPE}",
  "product_version": "${PRODUCT_VERSION}",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "domain": "${DOMAIN}",
  "database_name": "${DATABASE_NAME}",
  "runtime_lock_schema": $(jq -r '.schema_version' "$RUNTIME_LOCK_PATH"),
  "runtime_lock_sha256": "$(sha256sum "$RUNTIME_LOCK_PATH" | awk '{print $1}')",
  "odoo_image": "${ODOO_IMAGE}",
  "odoo_digest": "$(jq -r '.odoo.digest' "$RUNTIME_LOCK_PATH")",
  "postgres_image": "${POSTGRES_IMAGE}",
  "postgres_digest": "$(jq -r '.postgres.digest' "$RUNTIME_LOCK_PATH")",
  "environment_id_short": "$(tr -d '-' < "$root/config/environment_id" | cut -c1-8 | tr '[:lower:]' '[:upper:]')",
  "license_id": null,
  "deployment_state": "initialized"
}
EOF
  chmod 600 "$root/config/deployment-manifest.json"
}

render_files() {
  local root="$1" master
  load_runtime_for_root "$root"
  master="$(cat "$root/secrets/odoo_master_password")"
  sed -e "s#__INSTANCE_SLUG__#$INSTANCE_SLUG#g" -e "s#__INSTANCE_ROOT__#$root#g" -e "s#__HTTP_PORT__#$HTTP_PORT#g" -e "s#__ODOO_IMAGE__#$ODOO_IMAGE#g" -e "s#__POSTGRES_IMAGE__#$POSTGRES_IMAGE#g" "$COMPOSE_TEMPLATE" > "$root/runtime/compose.yml"
  sed -e "s#__ODOO_MASTER_PASSWORD__#$master#g" -e "s#__DATABASE_NAME__#$DATABASE_NAME#g" "$ODOO_TEMPLATE" > "$root/config/odoo.conf"
  chmod 600 "$root/config/odoo.conf"
}

init_instance() {
  local slug="$1"; shift
  slug_ok "$slug" || die "slug must be lowercase, filesystem-safe, and Docker-safe"
  protected_slug "$slug" && die "protected environment slug"
  local type="customer" domain="customer.example.invalid" release="$DEFAULT_RELEASE" port="8180"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --type) type="${2:-}"; shift 2;;
      --domain) domain="${2:-}"; shift 2;;
      --release) release="${2:-}"; shift 2;;
      --port) port="${2:-}"; shift 2;;
      *) die "unknown init option: $1";;
    esac
  done
  [[ "$type" == customer || "$type" == test ]] || die "type must be customer or test"
  [[ "$port" =~ ^[0-9]+$ && "$port" -ge 1024 && "$port" -le 65535 ]] || die "port must be 1024-65535"
  local root; root="$(instance_dir "$slug")"; [[ ! -e "$root" ]] || die "instance already exists: $slug"
  umask 077; mkdir -p "$root"/{config,secrets,identity,license,activation,backups,runtime/addons}
  cp "$RUNTIME_LOCK_FILE" "$root/config/runtime-lock.json"
  chmod 600 "$root/config/runtime-lock.json"
  INSTANCE_SLUG="$slug" ENVIRONMENT_TYPE="$type" PRODUCT_VERSION="$release" DOMAIN="$domain" DATABASE_NAME="pmqms_${slug//-/_}" HTTP_PORT="$port"
  random_secret > "$root/secrets/postgres_password"
  random_secret > "$root/secrets/odoo_master_password"
  random_secret > "$root/secrets/initial_admin_password"
  if command -v uuidgen >/dev/null 2>&1; then uuidgen > "$root/config/environment_id"; else cat /proc/sys/kernel/random/uuid > "$root/config/environment_id"; fi
  chmod 755 "$root/config" "$root/secrets" "$root/license" "$root/activation"
  chmod 600 "$root/secrets"/* "$root/config/environment_id"
  write_manifest "$root"; render_files "$root"; cp "$MODULES_FILE" "$root/runtime/modules.txt"; chmod 600 "$root/runtime/modules.txt"
  log "initialized $slug ($type) at $root"
}

credentials() {
  local root; root="$(require_instance "$1")"; load_instance "$root"
  echo "instance_slug=$INSTANCE_SLUG"; echo "environment_type=$ENVIRONMENT_TYPE"; echo "database=$DATABASE_NAME"; echo "technical_login=admin"; echo "technical_password_file=$root/secrets/initial_admin_password"; echo "environment_id_file=$root/config/environment_id"
}

provision() (
  local slug="$1"; shift; local bundle="" type="test" port="8180"
  while [[ $# -gt 0 ]]; do case "$1" in --bundle) bundle="${2:-}"; shift 2;; --type) type="${2:-}"; shift 2;; --port) port="${2:-}"; shift 2;; *) die "unknown provision option: $1";; esac; done
  [[ -f "$bundle" ]] || die "bundle not found"; [[ "$type" == test || "$type" == customer ]] || die "invalid type"
  init_instance "$slug" --type "$type" --port "$port"
  local root; root="$(require_instance "$slug")"; load_instance "$root"; local tmp=""; trap 'cleanup_temp_dir "$tmp"' EXIT; tmp="$(new_temp_dir)"
  tar -xzf "$bundle" -C "$tmp"; [[ -d "$tmp/addons" ]] || die "bundle has no addons"
  [[ -s "$tmp/deployment/runtime/runtime-lock.json" && -s "$tmp/manifest.json" ]] || die "bundle has no runtime lock or manifest"
  validate_runtime_lock "$tmp/deployment/runtime/runtime-lock.json"
  local bundle_lock_sha; bundle_lock_sha="$(sha256sum "$tmp/deployment/runtime/runtime-lock.json" | awk '{print $1}')"
  jq -e --arg sha "$bundle_lock_sha" --arg odoo "$(jq -r '.odoo.image' "$tmp/deployment/runtime/runtime-lock.json")" --arg postgres "$(jq -r '.postgres.image' "$tmp/deployment/runtime/runtime-lock.json")" '(.runtime_lock_sha256 == $sha) and (.odoo_image == $odoo) and (.postgres_image == $postgres)' "$tmp/manifest.json" >/dev/null || die "bundle manifest does not match runtime lock"
  cp "$tmp/deployment/runtime/runtime-lock.json" "$root/config/runtime-lock.json"; chmod 600 "$root/config/runtime-lock.json"
  rm -rf "$root/runtime/addons"; mkdir -p "$root/runtime/addons"; cp -a "$tmp/addons/." "$root/runtime/addons/"; cp "$tmp/manifest.json" "$root/config/product-manifest.json"
  update_manifest_runtime "$root" "$root/config/runtime-lock.json"
  render_files "$root"
  find "$root/runtime/addons" -type d -exec chmod 755 {} +; find "$root/runtime/addons" -type f -exec chmod 644 {} +; chmod -R a-w "$root/runtime/addons"
  log "provisioned runtime assets for $slug"
)

up() { local root; root="$(require_instance "$1")"; load_instance "$root"; compose "$root" up -d; }
down() { local root; root="$(require_instance "$1")"; load_instance "$root"; compose "$root" down; }
config() { local root; root="$(require_instance "$1")"; load_instance "$root"; compose "$root" config >/dev/null; echo "customer_compose=valid"; }
health() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; compose "$root" up -d >/dev/null; local code=000
  for _ in {1..60}; do code="$(curl -s -o /tmp/pmqms-customer-health.html -w '%{http_code}' "http://127.0.0.1:$HTTP_PORT/web/login?db=$DATABASE_NAME" || true)"; [[ "$code" =~ ^(200|302|303)$ ]] && break; sleep 1; done
  echo "customer_http=$code"; [[ "$code" =~ ^(200|302|303)$ ]]
}

bootstrap() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; local modules; modules="$(module_list)"
  [[ -d "$root/runtime/addons/pm_qms_license" ]] || die "runtime addons are missing; provision a customer bundle first"
  compose "$root" up -d postgres
  compose "$root" run --rm odoo odoo -d "$DATABASE_NAME" --init "$modules" --without-demo=all --stop-after-init
  jq '.deployment_state="installed"' "$root/config/deployment-manifest.json" > "$root/config/deployment-manifest.json.tmp"
  mv "$root/config/deployment-manifest.json.tmp" "$root/config/deployment-manifest.json"; chmod 600 "$root/config/deployment-manifest.json"
  health "$1"
}

activation_request() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; mkdir -p "$root/activation"
  compose "$root" run --rm -v "$root/activation:/var/lib/pmqms-activation" odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY'
from pathlib import Path
request = env["pm.qms.activation.request"].sudo().create({})
Path("/var/lib/pmqms-activation/activation-request.json").write_text(request.request_json + "\n", encoding="utf-8")
env.cr.commit()
print("activation_request_id=%s" % request.id)
PY
  docker run --rm --user root -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" -v "$root/activation:/activation" "$ALPINE_IMAGE" sh -c 'chown "$HOST_UID:$HOST_GID" /activation/activation-request.json && chmod 600 /activation/activation-request.json'
  echo "activation_request=$root/activation/activation-request.json"
}

import_license() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; load_runtime_for_root "$root"; local license="$2"
  [[ -f "$license" ]] || die "license not found"; local license_id; license_id="$(jq -r '.payload.license_id' "$license")"
  [[ -n "$license_id" && "$license_id" != null ]] || die "license payload has no license_id"
  docker run --rm --user root -e LICENSE_NAME="$(basename "$license")" -v "$root/license:/license" -v "$(dirname "$license"):/input:ro" "$ALPINE_IMAGE" sh -lc 'cp "/input/$LICENSE_NAME" /license/active.pmql && chown 100:101 /license/active.pmql && chmod 600 /license/active.pmql'
  compose "$root" run --rm -v "$root/license:/var/lib/pmqms-license:ro" odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY'
from pathlib import Path
record = env["pm.qms.license"].sudo().import_document(Path("/var/lib/pmqms-license/active.pmql").read_bytes())
env.cr.commit()
print("license_id=%s revision=%s state=%s environment=%s" % (record.license_id, record.license_revision, record.effective_state, record.environment_short))
PY
  jq --arg id "$license_id" '.license_id=$id | .deployment_state="licensed"' "$root/config/deployment-manifest.json" > "$root/config/deployment-manifest.json.tmp"
  mv "$root/config/deployment-manifest.json.tmp" "$root/config/deployment-manifest.json"; chmod 600 "$root/config/deployment-manifest.json"
}

license_status() {
  local root; root="$(require_instance "$1")"; load_instance "$root"
  compose "$root" run --rm odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY'
license = env["pm.qms.license"].sudo().current()
status = env["pm.qms.license"].sudo().current_status()
if not license: print("license_status=missing")
else: print("license_status=%s license_id=%s company=%s/%s sites=%s/%s users=%s/%s environment=%s" % (status["status"], license.license_id, license.company_usage, license.company_limit, license.site_usage, license.site_limit, license.named_user_usage, license.named_user_limit, license.environment_short))
PY
}

bootstrap_customer() {
  local slug="$1"; shift; local company_name="" company_code="" user_login="" user_name="" password_file="" email=""
  while [[ $# -gt 0 ]]; do case "$1" in --company-name) company_name="${2:-}"; shift 2;; --company-code) company_code="${2:-}"; shift 2;; --user-login) user_login="${2:-}"; shift 2;; --user-name) user_name="${2:-}"; shift 2;; --user-email) email="${2:-}"; shift 2;; --user-password-file) password_file="${2:-}"; shift 2;; *) die "unknown bootstrap-customer option: $1";; esac; done
  [[ -n "$company_name" && -n "$company_code" && -n "$user_login" && -n "$user_name" ]] || die "company and first user fields are required"
  local root; root="$(require_instance "$slug")"; load_instance "$root"; load_runtime_for_root "$root"; runtime_verify_lock "$RUNTIME_LOCK_PATH"
  docker run --rm --user 100:101 -v "$root/license:/license:ro" "$ALPINE_IMAGE" test -f /license/active.pmql || die "import a signed license before customer bootstrap"
  if [[ -z "$password_file" ]]; then password_file="$root/secrets/quality_manager_password"; [[ -f "$password_file" ]] || random_secret > "$password_file"; chmod 600 "$password_file"; fi
  [[ -f "$password_file" ]] || die "quality manager password file not found"
  local mount="/var/lib/pmqms-bootstrap"; local staged_password="$root/activation/bootstrap-password"
  docker run --rm --user root -v "$password_file:/input/password:ro" -v "$root/activation:/activation" "$ALPINE_IMAGE" sh -lc 'cp /input/password /activation/bootstrap-password && chown 100:101 /activation/bootstrap-password && chmod 600 /activation/bootstrap-password'
  local bootstrap_status=0
  compose "$root" run --rm -v "$staged_password:$mount/password:ro" odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<PY || bootstrap_status=$?
from pathlib import Path
company = env.company
Organization = env["pm.qms.organization"].sudo()
if Organization.search([("organization_kind", "=", "operational")], limit=1):
    raise RuntimeError("An operational customer organization already exists.")
organization = Organization.create({"name": ${company_name@Q}, "code": ${company_code@Q}, "organization_kind": "operational", "company_id": company.id})
quality_group = env.ref("pm_qms_core.group_qms_quality_manager")
Users = env["res.users"].sudo()
if Users.search([("login", "=", ${user_login@Q})], limit=1):
    raise RuntimeError("The Quality Manager login already exists.")
user = Users.create({"name": ${user_name@Q}, "login": ${user_login@Q}, "email": ${email@Q}, "password": Path("$mount/password").read_text().strip(), "company_id": company.id, "company_ids": [(6, 0, [company.id])], "group_ids": [(4, quality_group.id)]})
env["pm.qms.person"].sudo().create({"name": ${user_name@Q}, "user_id": user.id, "organization_id": organization.id})
organization.write({"quality_contact_id": user.id})
env.cr.commit()
print("operational_organization=%s quality_manager=%s system_admin=%s" % (organization.code, user.login, bool(user.has_group("base.group_system"))))
PY
  docker run --rm --user root -v "$root/activation:/activation" "$ALPINE_IMAGE" rm -f /activation/bootstrap-password || true
  (( bootstrap_status == 0 )) || return "$bootstrap_status"
  log "customer bootstrap complete for $slug; retrieve credentials with credentials"
}

create_site() {
  local slug="$1"; shift; local code="" name="" type="other"
  while [[ $# -gt 0 ]]; do case "$1" in --code) code="${2:-}"; shift 2;; --name) name="${2:-}"; shift 2;; --type) type="${2:-}"; shift 2;; *) die "unknown create-site option: $1";; esac; done
  [[ -n "$code" && -n "$name" ]] || die "site code and name are required"
  local root; root="$(require_instance "$slug")"; load_instance "$root"
  compose "$root" run --rm odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<PY
organization = env["pm.qms.organization"].sudo().search([("organization_kind", "=", "operational")], limit=1)
if not organization: raise RuntimeError("Create the operational organization first.")
site = env["pm.qms.site"].sudo().create({"code": ${code@Q}, "name": ${name@Q}, "site_type": ${type@Q}, "organization_id": organization.id, "is_primary": not bool(organization.site_ids)})
env.cr.commit()
print("site=%s" % site.code)
PY
}

backup() (
  local slug="$1"; shift; local recipient_file="${PMQMS_BACKUP_RECIPIENT_FILE:-}" off_host_dir="" recovery_class="daily"
  while [[ $# -gt 0 ]]; do case "$1" in --recipient-file) recipient_file="${2:-}"; shift 2;; --off-host-dir) off_host_dir="${2:-}"; shift 2;; --class) recovery_class="${2:-}"; shift 2;; *) die "unknown backup option: $1";; esac; done
  local root; root="$(require_instance "$slug")"; load_instance "$root"; mkdir -p "$root/backups"; chmod 700 "$root/backups"
  touch "$root/backups/.pmqms-recovery-repository"
  [[ -n "$recipient_file" ]] || die "encrypted backup recipient is required via --recipient-file or PMQMS_BACKUP_RECIPIENT_FILE"
  [[ -f "$recipient_file" ]] || die "encrypted backup recipient file is missing"
  local odoo_id="" was_running=0 tmp="" archive="" stamp="" quiesce_start_utc="" database_snapshot_utc="" filestore_snapshot_utc="" quiesce_end_utc=""
  backup_cleanup() {
    local rc=$?
    trap - EXIT
    if [[ "${was_running:-0}" == 1 && -n "${root:-}" ]]; then compose "$root" start odoo >/dev/null 2>&1 || rc=1; fi
    cleanup_temp_dir "${tmp:-}" || rc=1
    exit "$rc"
  }
  trap backup_cleanup EXIT
  tmp="$(new_temp_dir)"
  quiesce_start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  odoo_id="$(compose "$root" ps -q odoo 2>/dev/null || true)"
  if [[ -n "$odoo_id" && "$(docker inspect -f '{{.State.Running}}' "$odoo_id" 2>/dev/null || true)" == true ]]; then
    was_running=1
    compose "$root" stop odoo >/dev/null
    [[ "$(docker inspect -f '{{.State.Running}}' "$odoo_id" 2>/dev/null || true)" == false ]] || die "Odoo service did not stop for the consistency window"
  fi
  compose "$root" up -d postgres >/dev/null
  stamp="$(date -u +%Y%m%dT%H%M%S%NZ)"; archive="$root/backups/${INSTANCE_SLUG}-${stamp}.tar.age"
  compose "$root" exec -T postgres pg_dump -U odoo -d "$DATABASE_NAME" --format=custom > "$tmp/db.dump"
  database_snapshot_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  docker run --rm -v "pmqms_${INSTANCE_SLUG}_odoo_data:/odoo-data:ro" -v "$tmp:/backup" "$ALPINE_IMAGE" sh -c "cd /odoo-data && if [ -d filestore/$DATABASE_NAME ]; then tar -czf /backup/filestore.tar.gz filestore/$DATABASE_NAME; else tar -czf /backup/filestore.tar.gz --files-from /dev/null; fi"
  filestore_snapshot_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  cp "$root/config/environment_id" "$tmp/environment_id"
  cp "$root/config/runtime-lock.json" "$tmp/runtime-lock.json"
  cp "$root/config/deployment-manifest.json" "$tmp/deployment-manifest.json"
  local source_release_sha; source_release_sha="$(git -C "$REPO_ROOT" rev-parse HEAD)"
  local component_args=(--component "db.dump=$tmp/db.dump" --component "filestore.tar.gz=$tmp/filestore.tar.gz" --component "environment_id=$tmp/environment_id" --component "runtime-lock.json=$tmp/runtime-lock.json" --component "deployment-manifest.json=$tmp/deployment-manifest.json")
  if [[ -f "$root/license/active.pmql" ]]; then cp "$root/license/active.pmql" "$tmp/active.pmql"; component_args+=(--component "active.pmql=$tmp/active.pmql"); fi
  quiesce_end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 "$BACKUP_TOOL" pack --output "$archive" --recipient-file "$recipient_file" --source-instance "$INSTANCE_SLUG" --source-database "$DATABASE_NAME" --source-environment-id "$(tr -d '\n' < "$root/config/environment_id")" --product-version "$PRODUCT_VERSION" --source-release-sha "$source_release_sha" --recovery-point-class "$recovery_class" --created-utc "$quiesce_end_utc" --quiesce-start-utc "$quiesce_start_utc" --database-snapshot-utc "$database_snapshot_utc" --filestore-snapshot-utc "$filestore_snapshot_utc" --quiesce-end-utc "$quiesce_end_utc" "${component_args[@]}"
  if [[ -n "$off_host_dir" ]]; then python3 "$BACKUP_TOOL" transfer --archive "$archive" --destination "$off_host_dir"; fi
  echo "backup=$archive"; echo "checksum=$archive.sha256"; echo "manifest=$archive.manifest.json"
)

restore_validate() (
  local source_slug="$1" archive="$2"; shift 2; local identity_file="${PMQMS_BACKUP_IDENTITY_FILE:-}" verification_file=""; while [[ $# -gt 0 ]]; do case "$1" in --identity-file) identity_file="${2:-}"; shift 2;; --verification-file) verification_file="${2:-}"; shift 2;; *) die "unknown restore-validate option: $1";; esac; done
  local source_root; source_root="$(require_instance "$source_slug")"; load_instance "$source_root"; [[ "$ENVIRONMENT_TYPE" == test ]] || die "restore validation source must be test type"
  local source_database="$DATABASE_NAME" source_environment_id="$ENVIRONMENT_ID_FILE" source_product_version="$PRODUCT_VERSION" source_port="$HTTP_PORT"
  [[ -n "$identity_file" ]] || die "restore identity is required via --identity-file or PMQMS_BACKUP_IDENTITY_FILE"
  [[ -z "$verification_file" || -f "$verification_file" ]] || die "restore verification file is missing"
  [[ -f "$archive" && -f "$archive.sha256" && -f "$archive.manifest.json" ]] || die "backup archive, manifest, or checksum is missing"
  local recovery="${source_slug}-recovery"; [[ ! -e "$(instance_dir "$recovery")" ]] || die "recovery instance already exists"
  init_instance "$recovery" --type test --port "$((source_port + 1))" --release "$source_product_version"
  local target; target="$(require_instance "$recovery")"; load_instance "$target"; local target_database="$DATABASE_NAME" tmp="" payload=""
  restore_cleanup() {
    local rc=$?
    trap - EXIT
    if [[ -d "$(instance_dir "$recovery")" ]]; then destroy "$recovery" --confirm-ephemeral >/dev/null 2>&1 || rc=1; fi
    cleanup_temp_dir "$tmp" || rc=1
    exit "$rc"
  }
  trap restore_cleanup EXIT
  tmp="$(new_temp_dir)"; payload="$tmp/payload"; python3 "$BACKUP_TOOL" unpack --archive "$archive" --identity-file "$identity_file" --expected-instance "$source_slug" --expected-database "$source_database" --output "$payload"
  cp "$payload/environment_id" "$target/config/environment_id"; chmod 600 "$target/config/environment_id"; [[ -f "$payload/active.pmql" ]] && cp "$payload/active.pmql" "$target/license/active.pmql" && chmod 600 "$target/license/active.pmql"
  cp "$payload/runtime-lock.json" "$target/config/runtime-lock.json"; chmod 600 "$target/config/runtime-lock.json"
  cp "$payload/deployment-manifest.json" "$target/config/deployment-manifest.json"
  jq --arg slug "$recovery" --arg type "test" --arg product "$source_product_version" \
    '.instance_slug=$slug | .environment_type=$type | .product_version=$product | .deployment_state="restored"' \
    "$target/config/deployment-manifest.json" > "$target/config/deployment-manifest.json.tmp"
  mv "$target/config/deployment-manifest.json.tmp" "$target/config/deployment-manifest.json"
  chmod 600 "$target/config/deployment-manifest.json"
  update_manifest_runtime "$target" "$target/config/runtime-lock.json"
  render_files "$target"
  cp -a "$source_root/runtime/addons/." "$target/runtime/addons/"; compose "$target" up -d postgres >/dev/null
  local postgres_ready=0; for _ in {1..30}; do if compose "$target" exec -T postgres pg_isready -U odoo -d postgres >/dev/null 2>&1; then postgres_ready=1; break; fi; sleep 1; done
  [[ "$postgres_ready" == 1 ]] || die "recovery PostgreSQL did not become ready"
  compose "$target" exec -T postgres createdb -U odoo "$target_database" >/dev/null
  compose "$target" exec -T postgres pg_restore -U odoo -d "$target_database" --no-owner --role=odoo < "$payload/db.dump"
  docker run --rm -e SOURCE_DATABASE="$source_database" -e TARGET_DATABASE="$target_database" -v "pmqms_${recovery}_odoo_data:/odoo-data" -v "$payload:/backup:ro" "$ALPINE_IMAGE" sh -eu -c '
    work=/tmp/filestore-restore
    mkdir -p "$work"
    tar -tzf /backup/filestore.tar.gz > "$work/members"
    while IFS= read -r member; do
      case "$member" in
        "filestore/$SOURCE_DATABASE"|"filestore/$SOURCE_DATABASE/"*) ;;
        *) echo "unexpected filestore member" >&2; exit 1;;
      esac
      case "$member" in /**|*".."*) echo "unsafe filestore member" >&2; exit 1;; esac
    done < "$work/members"
    tar -xzf /backup/filestore.tar.gz -C "$work"
    if [ -d "$work/filestore/$SOURCE_DATABASE" ]; then
      mkdir -p /odoo-data/filestore
      rm -rf "/odoo-data/filestore/$TARGET_DATABASE"
      mv "$work/filestore/$SOURCE_DATABASE" "/odoo-data/filestore/$TARGET_DATABASE"
    fi
  '
  if ! health "$recovery"; then
    printf 'recovery_root=%s\n' "$target" >&2
    printf 'recovery_runtime_lock=%s\n' "$target/config/runtime-lock.json" >&2
    ls -la "$target/config" >&2 || true
    docker logs --tail=120 "pmqms-customer-${recovery}-odoo-1" >&2 || true
    die "recovery Odoo did not become healthy"
  fi
  local license_output; license_output="$(license_status "$recovery")"; [[ "$license_output" == *"license_status=valid"* || "$license_output" == *"license_status=expiring"* ]] || die "recovery license is not valid"
  if [[ -n "$verification_file" ]]; then
    local verification_dir; verification_dir="$(dirname "$verification_file")"
    compose "$recovery" run --rm -v "$verification_file:/tmp/recovery-verification.json:ro" -v "$verification_dir:/tmp/recovery-evidence" odoo odoo shell -d "$target_database" --log-level=error <<'PY'
from pathlib import Path
import base64, hashlib, json

expected = json.loads(Path("/tmp/recovery-verification.json").read_text(encoding="utf-8"))
Organization = env["pm.qms.organization"].sudo()
organization = Organization.search([("code", "=", expected["organization_code"])], limit=1)
project = env["pm.qms.implementation.project"].sudo().search(
    [("name", "=", expected["implementation_name"]), ("organization_id", "=", organization.id)], limit=1
)
attachment = env["ir.attachment"].sudo().search(
    [("name", "=", expected["attachment_name"]), ("res_model", "=", "pm.qms.organization"), ("res_id", "=", organization.id)], limit=1
)
if not organization or not project or not attachment:
    raise RuntimeError("fictional recovery fixture is missing")
attachment_sha256 = hashlib.sha256(base64.b64decode(attachment.datas)).hexdigest()
if attachment_sha256 != expected["attachment_sha256"]:
    raise RuntimeError("restored attachment checksum mismatch")
counts = {model: env[model].sudo().search_count([]) for model in expected["counts"]}
if counts != expected["counts"]:
    raise RuntimeError("restored selected record counts differ")
if env["mail.mail"].sudo().search_count([("state", "=", "outgoing")]):
    raise RuntimeError("restored environment has outgoing email")
result = dict(expected)
result.update({"organization_id": organization.id, "implementation_id": project.id, "attachment_sha256": attachment_sha256, "counts": counts})
Path("/tmp/recovery-evidence/restored.json").write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
print("recovery_record_validation=pass")
PY
  fi
  echo "restore_validation=pass"
)

retention() (
  local slug="$1"; shift; local root; root="$(require_instance "$slug")"; load_instance "$root"
  local args=(--directory "$root/backups"); while [[ $# -gt 0 ]]; do case "$1" in --now) args+=(--now "${2:-}"); shift 2;; --apply) args+=(--apply); shift;; *) die "unknown retention option: $1";; esac; done
  python3 "$BACKUP_TOOL" retention "${args[@]}"
)

bundle() (
  local output="" release="$DEFAULT_RELEASE"
  while [[ $# -gt 0 ]]; do case "$1" in --output) output="${2:-}"; shift 2;; --release) release="${2:-}"; shift 2;; *) die "unknown bundle option: $1";; esac; done
  [[ -n "$output" ]] || die "--output is required"; git -C "$REPO_ROOT" rev-parse "$release^{commit}" >/dev/null 2>&1 || die "release tag not found"
  local tmp=""; trap 'cleanup_temp_dir "$tmp"' EXIT; tmp="$(new_temp_dir)"
  git -C "$REPO_ROOT" archive "$release" addons deployment/customer deployment/runtime/runtime-lock.json deployment/docker/customer deployment/nginx/customer.conf.example deployment/scripts/customer-instance.sh | tar -x -C "$tmp"
  [[ -s "$tmp/deployment/runtime/runtime-lock.json" ]] || die "release has no runtime lock"
  rm -rf "$tmp/deployment/demo" "$tmp/deployment/docker/demo"; find "$tmp/addons" -type d -name __pycache__ -prune -exec rm -rf {} +; find "$tmp/addons" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
  local sha; sha="$(git -C "$REPO_ROOT" rev-parse "$release^{commit}")"
  local lock_sha odoo_image postgres_image
  lock_sha="$(sha256sum "$tmp/deployment/runtime/runtime-lock.json" | awk '{print $1}')"
  odoo_image="$(jq -r '.odoo.image' "$tmp/deployment/runtime/runtime-lock.json")"
  postgres_image="$(jq -r '.postgres.image' "$tmp/deployment/runtime/runtime-lock.json")"
  jq -n --arg product "$release" --arg source "$sha" --arg built "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg lock "$lock_sha" --arg odoo "$odoo_image" --arg postgres "$postgres_image" '{product_version:$product,source_sha:$source,built_at:$built,environment_types:["customer","test"],runtime_lock_sha256:$lock,odoo_image:$odoo,postgres_image:$postgres,contains_demo_data:false,contains_private_signing_key:false}' > "$tmp/manifest.json"
  (cd "$tmp" && find addons deployment -type f -print0 | sort -z | xargs -0 sha256sum > checksums.sha256)
  mkdir -p "$(dirname "$output")"; tar -C "$tmp" -czf "$output" .; sha256sum "$output" > "$output.sha256"
  if tar -xOzf "$output" ./manifest.json 2>/dev/null | grep -Eqi 'Apex Precision|APEX-HQ|APEX-MFG|APEX-INS|PMQMS-DEMO-2026'; then die "Demo content detected in bundle"; fi
  if grep -RInaE --exclude='customer-instance.sh' 'Apex Precision|APEX-HQ|APEX-MFG|APEX-INS|PMQMS-DEMO-2026|odoo-demo|pmqms_demo' "$tmp/addons" "$tmp/deployment" >/dev/null 2>&1; then die "Demo content detected in bundle"; fi
  echo "bundle=$output"; echo "checksum=$output.sha256"; echo "source_sha=$sha"
)

upgrade() {
  local slug="$1"; shift; local target_release="" approve_runtime_change=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --to) target_release="${2:-}"; shift 2;;
      --approve-runtime-change) approve_runtime_change=1; shift;;
      *) die "unknown upgrade option: $1";;
    esac
  done
  [[ -n "$target_release" ]] || die "--to release tag is required"
  [[ "$target_release" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]] || die "upgrade target must be an approved release tag"
  git -C "$REPO_ROOT" rev-parse "$target_release^{commit}" >/dev/null 2>&1 || die "release tag not found locally"
  local root target_lock current_lock_sha target_lock_sha target_tmp
  root="$(require_instance "$slug")"; load_instance "$root"; load_runtime_for_root "$root"
  target_tmp="$(mktemp)"
  if ! git -C "$REPO_ROOT" show "$target_release:deployment/runtime/runtime-lock.json" > "$target_tmp" 2>/dev/null; then
    rm -f "$target_tmp"; die "target release has no runtime lock: $target_release"
  fi
  target_lock="$target_tmp"
  validate_runtime_lock "$target_lock"
  current_lock_sha="$(sha256sum "$RUNTIME_LOCK_PATH" | awk '{print $1}')"
  target_lock_sha="$(sha256sum "$target_lock" | awk '{print $1}')"
  log "OLD ODOO=$ODOO_IMAGE"
  log "NEW ODOO=$(jq -r '.odoo.image' "$target_lock")"
  log "OLD POSTGRES=$POSTGRES_IMAGE"
  log "NEW POSTGRES=$(jq -r '.postgres.image' "$target_lock")"
  if [[ "$current_lock_sha" != "$target_lock_sha" && "$approve_runtime_change" != 1 ]]; then
    rm -f "$target_tmp"
    die "runtime lock changes require --approve-runtime-change"
  fi
  backup "$slug" >/dev/null
  jq --arg v "$target_release" --arg schema "$(jq -r '.schema_version' "$target_lock")" \
    --arg lock_sha "$target_lock_sha" --arg odoo "$(jq -r '.odoo.image' "$target_lock")" \
    --arg odoo_digest "$(jq -r '.odoo.digest' "$target_lock")" --arg postgres "$(jq -r '.postgres.image' "$target_lock")" \
    --arg postgres_digest "$(jq -r '.postgres.digest' "$target_lock")" \
    '.previous_product_version=.product_version | .product_version=$v | .deployment_state="upgrade-ready" | .runtime_lock_schema=($schema|tonumber) | .runtime_lock_sha256=$lock_sha | .odoo_image=$odoo | .odoo_digest=$odoo_digest | .postgres_image=$postgres | .postgres_digest=$postgres_digest' \
    "$root/config/deployment-manifest.json" > "$root/config/deployment-manifest.json.tmp"
  mv "$root/config/deployment-manifest.json.tmp" "$root/config/deployment-manifest.json"; chmod 600 "$root/config/deployment-manifest.json"
  rm -f "$target_tmp"
  log "preflight and backup passed; deploy the approved bundle for $target_release, then run bootstrap/health"
}

customer_ready() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; local ok=1
  runtime_manifest_gate "$root" || ok=0
  health "$1" >/dev/null || ok=0
  local odoo_id postgres_id
  odoo_id="$(compose "$root" ps -q odoo)"
  postgres_id="$(compose "$root" ps -q postgres)"
  [[ -n "$odoo_id" && "$(docker inspect -f '{{.Image}}' "$odoo_id")" == "$(docker image inspect -f '{{.Id}}' "$ODOO_IMAGE")" ]] || ok=0
  [[ -n "$postgres_id" && "$(docker inspect -f '{{.Image}}' "$postgres_id")" == "$(docker image inspect -f '{{.Id}}' "$POSTGRES_IMAGE")" ]] || ok=0
  docker run --rm --user 100:101 -v "$root/license:/license:ro" -v "$root/config:/config:ro" -v "$root/secrets:/secrets:ro" "$ALPINE_IMAGE" sh -c 'test -f /license/active.pmql && test -f /config/environment_id && test -f /secrets/postgres_password && test -f /secrets/odoo_master_password' || ok=0
  compose "$root" run --rm odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY' || ok=0
organization = env["pm.qms.organization"].sudo().search([("organization_kind", "=", "operational")], limit=1)
if not organization: raise RuntimeError("No operational organization")
if not env["pm.qms.person"].sudo().search_count([("organization_id", "=", organization.id), ("user_id", "!=", False)]): raise RuntimeError("No licensed first user")
license = env["pm.qms.license"].sudo().current()
status = env["pm.qms.license"].sudo().current_status()["status"]
if not license or status not in ("valid", "expiring"): raise RuntimeError("License is not usable")
print("customer_ready_application=pass")
PY
  if [[ "$ok" == 1 ]]; then echo "CUSTOMER_READY=YES"; else echo "CUSTOMER_READY=NO"; return 1; fi
}

destroy() {
  local slug="$1"; shift; [[ "${1:-}" == --confirm-ephemeral ]] || die "destroy requires --confirm-ephemeral"
  local root; root="$(require_instance "$slug")"; load_instance "$root"; [[ "$ENVIRONMENT_TYPE" == test ]] || die "destroy only accepts environment_type=test"
  [[ "$slug" == *test* || "$slug" == *recovery* ]] || die "destroy requires an explicit ephemeral slug"
  compose "$root" down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker run --rm --user root -v "$root:/data" "$ALPINE_IMAGE" sh -c 'rm -rf /data/* /data/.[!.]* /data/..?*' >/dev/null
  rmdir -- "$root"; log "ephemeral instance removed: $slug"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  command="${1:-}"; shift || true
  case "$command" in
    init) init_instance "$@";; provision) provision "$@";; credentials) credentials "$@";; config) config "$@";; runtime-images) runtime_images "$@";; runtime-verify) runtime_verify "$@";; runtime-fetch) runtime_fetch "$@";; up) up "$@";; down) down "$@";; health) health "$@";; bootstrap) bootstrap "$@";; activation-request) activation_request "$@";; import-license) import_license "$@";; license-status) license_status "$@";; bootstrap-customer) bootstrap_customer "$@";; create-site) create_site "$@";; backup) backup "$@";; restore-validate) restore_validate "$@";; retention) retention "$@";; upgrade) upgrade "$@";; customer-ready) customer_ready "$@";; bundle) bundle "$@";; destroy) destroy "$@";; help|-h|--help) usage;; *) usage; exit 2;; esac
fi
