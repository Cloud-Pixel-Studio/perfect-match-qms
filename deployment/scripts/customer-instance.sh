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

die() { echo "ERROR: $*" >&2; exit 2; }
log() { echo "CUSTOMER: $*"; }
random_secret() { openssl rand -base64 48 | tr -d '\n'; }
slug_ok() { [[ "$1" =~ ^[a-z0-9]+([a-z0-9-]*[a-z0-9])?$ ]]; }
instance_dir() { echo "$INSTANCE_ROOT_BASE/$1"; }
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
  prepare_permissions "$root"
  docker compose --project-name "pmqms-customer-${INSTANCE_SLUG}" --env-file "$root/config/instance.env" -f "$root/runtime/compose.yml" "$@"
}
prepare_permissions() {
  local root="$1"
  docker run --rm --user root -v "$root/config:/config" -v "$root/secrets:/secrets" -v "$root/license:/license" -v "$root/activation:/activation" odoo:19.0 sh -lc 'chown 100:101 /config/odoo.conf /config/environment_id /secrets/postgres_password /license /activation 2>/dev/null || true; chmod 600 /config/odoo.conf /secrets/postgres_password; chmod 644 /config/environment_id 2>/dev/null || true; chmod 700 /license 2>/dev/null || true; chmod 755 /activation 2>/dev/null || true'
}
module_list() { paste -sd, <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$MODULES_FILE"); }
read_option() { local flag="$1"; shift; while [[ $# -gt 0 ]]; do [[ "$1" == "$flag" ]] && { echo "${2:-}"; return 0; }; shift; done; return 1; }

usage() {
  cat <<'EOF'
Usage: customer-instance.sh <command> [arguments]
  init <slug> [--type customer|test] [--domain domain] [--release tag] [--port port]
  provision <slug> --bundle bundle.tar.gz [--type customer|test]
  credentials|config|up|down|health <slug>
  bootstrap <slug>
  activation-request <slug>
  import-license <slug> <license.pmql>
  license-status <slug>
  bootstrap-customer <slug> --company-name name --company-code code --user-login login --user-name name [--user-password-file file]
  create-site <slug> --code code --name name --type site-type
  backup <slug>
  restore-validate <slug> <backup.tar.gz>
  upgrade <slug> --to <release-tag>
  customer-ready <slug>
  bundle --output file.tar.gz [--release tag]
  destroy <slug> --confirm-ephemeral

All state is kept outside Git. Customer and test lifecycles are guarded by
environment type and protected-name checks.
EOF
}

write_manifest() {
  local root="$1"
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
  "environment_id_short": "$(tr -d '-' < "$root/config/environment_id" | cut -c1-8 | tr '[:lower:]' '[:upper:]')",
  "license_id": null,
  "deployment_state": "initialized"
}
EOF
  chmod 600 "$root/config/deployment-manifest.json"
}

render_files() {
  local root="$1" master
  master="$(cat "$root/secrets/odoo_master_password")"
  sed -e "s#__INSTANCE_SLUG__#$INSTANCE_SLUG#g" -e "s#__INSTANCE_ROOT__#$root#g" -e "s#__HTTP_PORT__#$HTTP_PORT#g" "$COMPOSE_TEMPLATE" > "$root/runtime/compose.yml"
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

provision() {
  local slug="$1"; shift; local bundle="" type="test"
  while [[ $# -gt 0 ]]; do case "$1" in --bundle) bundle="${2:-}"; shift 2;; --type) type="${2:-}"; shift 2;; *) die "unknown provision option: $1";; esac; done
  [[ -f "$bundle" ]] || die "bundle not found"; [[ "$type" == test || "$type" == customer ]] || die "invalid type"
  init_instance "$slug" --type "$type"
  local root; root="$(require_instance "$slug")"; load_instance "$root"; local tmp; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  tar -xzf "$bundle" -C "$tmp"; [[ -d "$tmp/addons" ]] || die "bundle has no addons"
  rm -rf "$root/runtime/addons"; mkdir -p "$root/runtime/addons"; cp -a "$tmp/addons/." "$root/runtime/addons/"; cp "$tmp/manifest.json" "$root/config/product-manifest.json"
  find "$root/runtime/addons" -type d -exec chmod 755 {} +; find "$root/runtime/addons" -type f -exec chmod 644 {} +; chmod -R a-w "$root/runtime/addons"
  log "provisioned runtime assets for $slug"
}

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
  docker run --rm --user root -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" -v "$root/activation:/activation" alpine:3.20 sh -c 'chown "$HOST_UID:$HOST_GID" /activation/activation-request.json && chmod 600 /activation/activation-request.json'
  echo "activation_request=$root/activation/activation-request.json"
}

import_license() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; local license="$2"
  [[ -f "$license" ]] || die "license not found"; local license_id; license_id="$(jq -r '.payload.license_id' "$license")"
  [[ -n "$license_id" && "$license_id" != null ]] || die "license payload has no license_id"
  docker run --rm --user root -e LICENSE_NAME="$(basename "$license")" -v "$root/license:/license" -v "$(dirname "$license"):/input:ro" alpine:3.20 sh -lc 'cp "/input/$LICENSE_NAME" /license/active.pmql && chown 100:101 /license/active.pmql && chmod 600 /license/active.pmql'
  compose "$root" run --rm -v "$root/license:/var/lib/pmqms-license:ro" odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY'
from pathlib import Path
record = env["pm.qms.license"].sudo().import_document(Path("/var/lib/pmqms-license/active.pmql").read_bytes())
env.cr.commit()
print("license_id=%s revision=%s state=%s environment=%s" % (record.license_id, record.license_revision, record.state, record.environment_short))
PY
  jq --arg id "$license_id" '.license_id=$id | .deployment_state="licensed"' "$root/config/deployment-manifest.json" > "$root/config/deployment-manifest.json.tmp"
  mv "$root/config/deployment-manifest.json.tmp" "$root/config/deployment-manifest.json"; chmod 600 "$root/config/deployment-manifest.json"
}

license_status() {
  local root; root="$(require_instance "$1")"; load_instance "$root"
  compose "$root" run --rm odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY'
license = env["pm.qms.license"].sudo().current()
if not license: print("license_status=missing")
else: print("license_status=%s license_id=%s company=%s/%s sites=%s/%s users=%s/%s environment=%s" % (license.state, license.license_id, license.company_usage, license.company_limit, license.site_usage, license.site_limit, license.named_user_usage, license.named_user_limit, license.environment_short))
PY
}

bootstrap_customer() {
  local slug="$1"; shift; local company_name="" company_code="" user_login="" user_name="" password_file="" email=""
  while [[ $# -gt 0 ]]; do case "$1" in --company-name) company_name="${2:-}"; shift 2;; --company-code) company_code="${2:-}"; shift 2;; --user-login) user_login="${2:-}"; shift 2;; --user-name) user_name="${2:-}"; shift 2;; --user-email) email="${2:-}"; shift 2;; --user-password-file) password_file="${2:-}"; shift 2;; *) die "unknown bootstrap-customer option: $1";; esac; done
  [[ -n "$company_name" && -n "$company_code" && -n "$user_login" && -n "$user_name" ]] || die "company and first user fields are required"
  local root; root="$(require_instance "$slug")"; load_instance "$root"
  docker run --rm --user 100:101 -v "$root/license:/license:ro" alpine:3.20 test -f /license/active.pmql || die "import a signed license before customer bootstrap"
  if [[ -z "$password_file" ]]; then password_file="$root/secrets/quality_manager_password"; [[ -f "$password_file" ]] || random_secret > "$password_file"; chmod 600 "$password_file"; fi
  [[ -f "$password_file" ]] || die "quality manager password file not found"
  local mount="/var/lib/pmqms-bootstrap"; local staged_password="$root/activation/bootstrap-password"
  docker run --rm --user root -v "$password_file:/input/password:ro" -v "$root/activation:/activation" alpine:3.20 sh -lc 'cp /input/password /activation/bootstrap-password && chown 100:101 /activation/bootstrap-password && chmod 600 /activation/bootstrap-password'
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
  docker run --rm --user root -v "$root/activation:/activation" alpine:3.20 rm -f /activation/bootstrap-password || true
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

backup() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; mkdir -p "$root/backups"; chmod 700 "$root/backups"
  compose "$root" up -d postgres >/dev/null
  local stamp archive tmp; stamp="$(date -u +%Y%m%dT%H%M%SZ)"; archive="$root/backups/${INSTANCE_SLUG}-${stamp}.tar.gz"; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  compose "$root" exec -T postgres pg_dump -U odoo -d "$DATABASE_NAME" --format=custom > "$tmp/db.dump"
  docker run --rm -v "pmqms_${INSTANCE_SLUG}_odoo_data:/odoo-data:ro" -v "$tmp:/backup" alpine:3.20 sh -c "cd /odoo-data && if [ -d filestore/$DATABASE_NAME ]; then tar -czf /backup/filestore.tar.gz filestore/$DATABASE_NAME; else tar -czf /backup/filestore.tar.gz --files-from /dev/null; fi"
  cp "$root/config/environment_id" "$tmp/environment_id"; [[ -f "$root/license/active.pmql" ]] && cp "$root/license/active.pmql" "$tmp/active.pmql" || true
  printf 'instance_slug=%s\nproduct_version=%s\ndatabase=%s\nbackup_created_utc=%s\n' "$INSTANCE_SLUG" "$PRODUCT_VERSION" "$DATABASE_NAME" "$stamp" > "$tmp/manifest.txt"
  tar -C "$tmp" -czf "$archive" .; sha256sum "$archive" > "$archive.sha256"; tar -tzf "$archive" >/dev/null
  echo "backup=$archive"; echo "checksum=$archive.sha256"
}

restore_validate() {
  local source_slug="$1" archive="$2"; local source; source="$(require_instance "$source_slug")"; load_instance "$source"; [[ "$ENVIRONMENT_TYPE" == test ]] || die "restore validation source must be test type"
  [[ -f "$archive" && -f "$archive.sha256" ]] || die "backup archive/checksum not found"; sha256sum -c "$archive.sha256" >/dev/null 2>&1 || die "backup checksum failed"
  local recovery="${source_slug}-recovery"; [[ ! -e "$(instance_dir "$recovery")" ]] || die "recovery instance already exists"
  init_instance "$recovery" --type test --port "$((HTTP_PORT + 1))" --release "$PRODUCT_VERSION"
  local target; target="$(require_instance "$recovery")"; load_instance "$target"; local tmp; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN; tar -xzf "$archive" -C "$tmp"
  cp "$tmp/environment_id" "$target/config/environment_id"; chmod 600 "$target/config/environment_id"; [[ -f "$tmp/active.pmql" ]] && cp "$tmp/active.pmql" "$target/license/active.pmql" && chmod 600 "$target/license/active.pmql"
  cp -a "$source/runtime/addons/." "$target/runtime/addons/"; compose "$target" up -d postgres >/dev/null
  for _ in {1..30}; do compose "$target" exec -T postgres pg_isready -U odoo -d postgres >/dev/null 2>&1 && break; sleep 1; done
  compose "$target" exec -T postgres createdb -U odoo "$DATABASE_NAME" 2>/dev/null || true
  compose "$target" exec -T postgres pg_restore -U odoo -d "$DATABASE_NAME" --no-owner --role=odoo < "$tmp/db.dump"
  health "$recovery"; license_status "$recovery"; destroy "$recovery" --confirm-ephemeral
  echo "restore_validation=pass"
}

bundle() {
  local output="" release="$DEFAULT_RELEASE"
  while [[ $# -gt 0 ]]; do case "$1" in --output) output="${2:-}"; shift 2;; --release) release="${2:-}"; shift 2;; *) die "unknown bundle option: $1";; esac; done
  [[ -n "$output" ]] || die "--output is required"; git -C "$REPO_ROOT" rev-parse "$release^{commit}" >/dev/null 2>&1 || die "release tag not found"
  local tmp; tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' RETURN
  git -C "$REPO_ROOT" archive "$release" addons deployment/customer deployment/docker/customer deployment/nginx/customer.conf.example deployment/scripts/customer-instance.sh | tar -x -C "$tmp"
  rm -rf "$tmp/deployment/demo" "$tmp/deployment/docker/demo"; find "$tmp/addons" -type d -name __pycache__ -prune -exec rm -rf {} +; find "$tmp/addons" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
  local sha; sha="$(git -C "$REPO_ROOT" rev-parse "$release^{commit}")"
  printf '{\n  "product_version": "%s",\n  "source_sha": "%s",\n  "built_at": "%s",\n  "environment_types": ["customer", "test"],\n  "contains_demo_data": false,\n  "contains_private_signing_key": false\n}\n' "$release" "$sha" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$tmp/manifest.json"
  (cd "$tmp" && find addons deployment -type f -print0 | sort -z | xargs -0 sha256sum > checksums.sha256)
  mkdir -p "$(dirname "$output")"; tar -C "$tmp" -czf "$output" .; sha256sum "$output" > "$output.sha256"
  if tar -xOzf "$output" ./manifest.json 2>/dev/null | grep -Eqi 'Apex Precision|APEX-HQ|APEX-MFG|APEX-INS|PMQMS-DEMO-2026'; then die "Demo content detected in bundle"; fi
  if grep -RInaE --exclude='customer-instance.sh' 'Apex Precision|APEX-HQ|APEX-MFG|APEX-INS|PMQMS-DEMO-2026|odoo-demo|pmqms_demo' "$tmp/addons" "$tmp/deployment" >/dev/null 2>&1; then die "Demo content detected in bundle"; fi
  echo "bundle=$output"; echo "checksum=$output.sha256"; echo "source_sha=$sha"
}

upgrade() {
  local slug="$1"; shift; local target_release="$(read_option --to "$@" || true)"
  [[ -n "$target_release" ]] || die "--to release tag is required"; [[ "$target_release" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]] || die "upgrade target must be an approved release tag"
  local root; root="$(require_instance "$slug")"; load_instance "$root"; backup "$slug" >/dev/null; git -C "$REPO_ROOT" rev-parse "$target_release^{commit}" >/dev/null 2>&1 || die "release tag not found locally"
  jq --arg v "$target_release" '.previous_product_version=.product_version | .product_version=$v | .deployment_state="upgrade-ready"' "$root/config/deployment-manifest.json" > "$root/config/deployment-manifest.json.tmp"; mv "$root/config/deployment-manifest.json.tmp" "$root/config/deployment-manifest.json"; chmod 600 "$root/config/deployment-manifest.json"
  log "preflight and backup passed; deploy the approved bundle for $target_release, then run bootstrap/health"
}

customer_ready() {
  local root; root="$(require_instance "$1")"; load_instance "$root"; local ok=1
  health "$1" >/dev/null || ok=0
  docker run --rm --user 100:101 -v "$root/license:/license:ro" -v "$root/config:/config:ro" -v "$root/secrets:/secrets:ro" alpine:3.20 sh -c 'test -f /license/active.pmql && test -f /config/environment_id && test -f /secrets/postgres_password && test -f /secrets/odoo_master_password' || ok=0
  compose "$root" run --rm odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY' || ok=0
organization = env["pm.qms.organization"].sudo().search([("organization_kind", "=", "operational")], limit=1)
if not organization: raise RuntimeError("No operational organization")
if not env["pm.qms.person"].sudo().search_count([("organization_id", "=", organization.id), ("user_id", "!=", False)]): raise RuntimeError("No licensed first user")
license = env["pm.qms.license"].sudo().current()
if not license or license.state not in ("valid", "expiring"): raise RuntimeError("License is not usable")
print("customer_ready_application=pass")
PY
  if [[ "$ok" == 1 ]]; then echo "CUSTOMER_READY=YES"; else echo "CUSTOMER_READY=NO"; return 1; fi
}

destroy() {
  local slug="$1"; shift; [[ "${1:-}" == --confirm-ephemeral ]] || die "destroy requires --confirm-ephemeral"
  local root; root="$(require_instance "$slug")"; load_instance "$root"; [[ "$ENVIRONMENT_TYPE" == test ]] || die "destroy only accepts environment_type=test"
  [[ "$slug" == *test* || "$slug" == *recovery* ]] || die "destroy requires an explicit ephemeral slug"
  compose "$root" down --volumes --remove-orphans >/dev/null 2>&1 || true
  docker run --rm --user root -v "$root:/data" alpine:3.20 sh -c 'rm -rf /data/* /data/.[!.]* /data/..?*' >/dev/null
  rmdir -- "$root"; log "ephemeral instance removed: $slug"
}

command="${1:-}"; shift || true
case "$command" in
  init) init_instance "$@";; provision) provision "$@";; credentials) credentials "$@";; config) config "$@";; up) up "$@";; down) down "$@";; health) health "$@";; bootstrap) bootstrap "$@";; activation-request) activation_request "$@";; import-license) import_license "$@";; license-status) license_status "$@";; bootstrap-customer) bootstrap_customer "$@";; create-site) create_site "$@";; backup) backup "$@";; restore-validate) restore_validate "$@";; upgrade) upgrade "$@";; customer-ready) customer_ready "$@";; bundle) bundle "$@";; destroy) destroy "$@";; help|-h|--help) usage;; *) usage; exit 2;; esac
