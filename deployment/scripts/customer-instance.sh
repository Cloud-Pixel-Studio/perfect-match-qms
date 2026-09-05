#!/usr/bin/env bash
set -euo pipefail

# Operator-controlled customer foundation. It never targets Demo or DEV.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
INSTANCE_ROOT_BASE="${PMQMS_CUSTOMER_INSTANCE_ROOT:-/opt/perfect-match/instances}"
OPERATOR_MODULES_FILE="$REPO_ROOT/deployment/customer/modules.txt"
OPERATOR_COMPOSE_TEMPLATE="$REPO_ROOT/deployment/docker/customer/compose.yml.template"
OPERATOR_ODOO_TEMPLATE="$REPO_ROOT/deployment/docker/customer/odoo.conf.template"
MODULES_FILE="$OPERATOR_MODULES_FILE"
COMPOSE_TEMPLATE="$OPERATOR_COMPOSE_TEMPLATE"
ODOO_TEMPLATE="$OPERATOR_ODOO_TEMPLATE"
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
release_assets_complete() {
  local release_root="$1"
  [[ -s "$release_root/deployment/customer/modules.txt" ]] &&
    [[ -s "$release_root/deployment/docker/customer/compose.yml.template" ]] &&
    [[ -s "$release_root/deployment/docker/customer/odoo.conf.template" ]]
}
load_release_assets_for_root() {
  local root="$1" release_root="$root/runtime/release"
  release_assets_complete "$release_root" ||
    die "instance release execution assets are missing: $release_root"
  INSTANCE_RELEASE_ROOT="$release_root"
  MODULES_FILE="$release_root/deployment/customer/modules.txt"
  COMPOSE_TEMPLATE="$release_root/deployment/docker/customer/compose.yml.template"
  ODOO_TEMPLATE="$release_root/deployment/docker/customer/odoo.conf.template"
}
install_release_assets() {
  local root="$1" source="$2" release_root="$root/runtime/release"
  [[ -d "$source" ]] || die "release asset source is missing"
  [[ -s "$source/deployment/customer/modules.txt" ]] ||
    die "release bundle has no modules.txt"
  [[ -s "$source/deployment/docker/customer/compose.yml.template" ]] ||
    die "release bundle has no customer compose template"
  [[ -s "$source/deployment/docker/customer/odoo.conf.template" ]] ||
    die "release bundle has no customer Odoo template"
  rm -rf -- "$release_root"
  mkdir -p "$release_root/deployment/customer" "$release_root/deployment/docker/customer"
  cp "$source/deployment/customer/modules.txt" "$release_root/deployment/customer/modules.txt"
  cp "$source/deployment/docker/customer/compose.yml.template" "$release_root/deployment/docker/customer/compose.yml.template"
  cp "$source/deployment/docker/customer/odoo.conf.template" "$release_root/deployment/docker/customer/odoo.conf.template"
  chmod 700 "$release_root" "$release_root/deployment" "$release_root/deployment/customer" "$release_root/deployment/docker" "$release_root/deployment/docker/customer"
  chmod 600 "$release_root/deployment/customer/modules.txt" "$release_root/deployment/docker/customer/compose.yml.template" "$release_root/deployment/docker/customer/odoo.conf.template"
  load_release_assets_for_root "$root"
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
  [[ -s "$manifest" && -s "$product" ]] || return 1
  local lock_sha; lock_sha="$(sha256sum "$lock" | awk '{print $1}')"
  jq -e --arg sha "$lock_sha" --arg odoo "$ODOO_IMAGE" --arg postgres "$POSTGRES_IMAGE" --arg instance_product "${PRODUCT_VERSION:-}" --arg instance_source "${SOURCE_RELEASE_SHA:-}" '(.runtime_lock_schema == 1) and (.runtime_lock_sha256 == $sha) and (.odoo_image == $odoo) and (.postgres_image == $postgres) and (.product_version == $instance_product) and (.source_release_sha == $instance_source) and (.source_release_sha | type == "string") and (.source_release_sha | test("^[0-9a-f]{40}$"))' "$manifest" >/dev/null || return 1
  jq -e --arg sha "$lock_sha" --arg odoo "$ODOO_IMAGE" --arg postgres "$POSTGRES_IMAGE" --arg expected_product "$(jq -er '.product_version' "$manifest")" --arg expected_source "$(jq -er '.source_release_sha' "$manifest")" '(.runtime_lock_sha256 == $sha) and (.odoo_image == $odoo) and (.postgres_image == $postgres) and (.product_version == $expected_product) and (.source_sha == $expected_source) and (.product_version | type == "string") and (.product_version | test("^v[0-9]+\\.[0-9]+\\.[0-9]+(-rc[0-9]+)?$")) and (.source_sha | type == "string") and (.source_sha | test("^[0-9a-f]{40}$"))' "$product" >/dev/null || return 1
  return 0
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
  docker run --rm --user root -v "$root/config:/config" -v "$root/secrets:/secrets" -v "$root/license:/license" -v "$root/activation:/activation" "$ODOO_IMAGE" sh -lc 'chown 100:101 /config/odoo.conf /config/environment_id /secrets/postgres_password /secrets/odoo_master_password /license /activation 2>/dev/null || true; chmod 600 /config/odoo.conf /secrets/postgres_password /secrets/odoo_master_password; chmod 644 /config/environment_id 2>/dev/null || true; chmod 700 /license 2>/dev/null || true; chmod 755 /activation 2>/dev/null || true'
}
prepare_operator_write_access() {
  local root="$1" host_uid="$(id -u)" host_gid="$(id -g)"
  load_runtime_for_root "$root"
  docker run --rm --user root -e HOST_UID="$host_uid" -e HOST_GID="$host_gid" \
    -v "$root/config:/config" -v "$root/runtime:/runtime" "$ALPINE_IMAGE" sh -eu -c '
      chown "$HOST_UID:$HOST_GID" /config /runtime
      chmod u+rwx /config /runtime
      find /config -maxdepth 1 -type f -exec chown "$HOST_UID:$HOST_GID" {} +
      find /runtime -maxdepth 1 -type f -exec chown "$HOST_UID:$HOST_GID" {} +
      find /runtime -mindepth 1 -maxdepth 1 -type d -exec chown "$HOST_UID:$HOST_GID" {} +
      find /runtime -mindepth 1 -maxdepth 1 -type d -exec chmod u+rwx {} +
    '
}
module_list() { paste -sd, <(sed -e 's/#.*//' -e '/^[[:space:]]*$/d' "$MODULES_FILE"); }
read_option() { local flag="$1"; shift; while [[ $# -gt 0 ]]; do [[ "$1" == "$flag" ]] && { echo "${2:-}"; return 0; }; shift; done; return 1; }
release_version_ok() { [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-rc[0-9]+)?$ ]]; }
release_version_not_older() {
  local current="$1" target="$2"
  local current_major current_minor current_patch current_rc
  local target_major target_minor target_patch target_rc
  [[ "$current" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)(-rc([0-9]+))?$ ]] || return 1
  current_major="${BASH_REMATCH[1]}"
  current_minor="${BASH_REMATCH[2]}"
  current_patch="${BASH_REMATCH[3]}"
  current_rc="${BASH_REMATCH[5]:-}"
  [[ "$target" =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)(-rc([0-9]+))?$ ]] || return 1
  target_major="${BASH_REMATCH[1]}"
  target_minor="${BASH_REMATCH[2]}"
  target_patch="${BASH_REMATCH[3]}"
  target_rc="${BASH_REMATCH[5]:-}"
  if ((10#$target_major != 10#$current_major)); then
    ((10#$target_major > 10#$current_major))
    return
  fi
  if ((10#$target_minor != 10#$current_minor)); then
    ((10#$target_minor > 10#$current_minor))
    return
  fi
  if ((10#$target_patch != 10#$current_patch)); then
    ((10#$target_patch > 10#$current_patch))
    return
  fi
  if [[ -z "$current_rc" && -n "$target_rc" ]]; then
    return 1
  fi
  if [[ -n "$current_rc" && -z "$target_rc" ]]; then
    return 0
  fi
  [[ -z "$current_rc" ]] && return 0
  ((10#$target_rc >= 10#$current_rc))
}
release_tag_sha() { local release="$1"; release_version_ok "$release" || return 1; git -C "$REPO_ROOT" show-ref --verify --quiet "refs/tags/$release" || return 1; git -C "$REPO_ROOT" rev-parse --verify "refs/tags/$release^{commit}"; }
release_execution_assets_from_tag() {
  local release="$1" destination="$2" expected_sha="${3:-}" tag_sha
  tag_sha="$(release_tag_sha "$release")" || die "approved release tag not found: $release"
  [[ -z "$expected_sha" || "$tag_sha" == "$expected_sha" ]] ||
    die "release tag/source identity mismatch: $release"
  rm -rf -- "$destination"
  mkdir -p "$destination"
  git -C "$REPO_ROOT" archive "$release" \
    deployment/customer/modules.txt \
    deployment/docker/customer/compose.yml.template \
    deployment/docker/customer/odoo.conf.template | tar -x -C "$destination"
  release_assets_complete "$destination" ||
    die "approved release tag has incomplete execution assets: $release"
}
release_addons_from_tag() {
  local release="$1" destination="$2" expected_sha="${3:-}" tag_sha
  tag_sha="$(release_tag_sha "$release")" || die "approved release tag not found: $release"
  [[ -z "$expected_sha" || "$tag_sha" == "$expected_sha" ]] ||
    die "release tag/source identity mismatch: $release"
  rm -rf -- "$destination"
  mkdir -p "$destination"
  git -C "$REPO_ROOT" archive "$release" addons | tar -x -C "$destination"
  [[ -d "$destination/addons" ]] || die "approved release tag has no addons: $release"
}

CUSTOMER_PAYLOAD_PATHS=(
  addons
  deployment/customer
  deployment/runtime/runtime-lock.json
  deployment/docker/customer
  deployment/nginx/customer.conf.example
  deployment/scripts/customer-instance.sh
)

validate_outer_checksum() {
  local bundle="$1" sidecar="$1.sha256" line actual expected
  local -a lines=()
  [[ -s "$sidecar" ]] || die "bundle checksum sidecar missing"
  mapfile -t lines < "$sidecar"
  [[ "${#lines[@]}" -eq 1 ]] || die "bundle checksum sidecar is invalid"
  line="${lines[0]}"
  if [[ "$line" =~ ^([0-9a-f]{64})[[:space:]][[:space:]]([^[:space:]]+)$ ]]; then
    expected="${BASH_REMATCH[1]}"
    [[ "${BASH_REMATCH[2]}" == "$(basename "$bundle")" ]] || die "bundle checksum sidecar filename is invalid"
  elif [[ "$line" =~ ^[0-9a-f]{64}$ ]]; then
    expected="$line"
  else
    die "bundle checksum sidecar is invalid"
  fi
  actual="$(sha256sum "$bundle" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || die "bundle outer checksum mismatch"
}

checksum_file_list_from_root() {
  local root="$1" output="$2"
  (
    cd "$root"
    {
      [[ -d addons ]] && find addons -type f -print
      [[ -d deployment ]] && find deployment -type f -print
      printf '%s\n' manifest.json
    } | sort
  ) > "$output"
}

validate_internal_checksum_coverage() {
  local root="$1" checksums="$1/checksums.sha256"
  local expected="$root/.expected-checksum-files" actual="$root/.actual-checksum-files"
  checksum_file_list_from_root "$root" "$expected"
  if ! awk '{
    if (NF != 2 || length($1) != 64 || $1 !~ /^[0-9a-f]+$/ || $2 ~ /^\// || $2 ~ /(^|\/)\.\.(\/|$)/) exit 1
    print $2
  }' "$checksums" | sort > "$actual"; then
    rm -f "$expected" "$actual"
    return 1
  fi
  if ! cmp -s "$expected" "$actual"; then
    rm -f "$expected" "$actual"
    return 1
  fi
  rm -f "$expected" "$actual"
  return 0
}

customer_payload_matches_release() {
  local release="$1" root="$2" path
  local expected="$root/.expected-release-payload" actual="$root/.actual-release-payload"
  git -C "$REPO_ROOT" ls-tree -r --name-only "refs/tags/$release" -- "${CUSTOMER_PAYLOAD_PATHS[@]}" | sort > "$expected" || return 1
  (
    cd "$root"
    {
      [[ -d addons ]] && find addons -type f -print
      [[ -d deployment/customer ]] && find deployment/customer -type f -print
      [[ -f deployment/runtime/runtime-lock.json ]] && printf '%s\n' deployment/runtime/runtime-lock.json
      [[ -d deployment/docker/customer ]] && find deployment/docker/customer -type f -print
      [[ -f deployment/nginx/customer.conf.example ]] && printf '%s\n' deployment/nginx/customer.conf.example
      [[ -f deployment/scripts/customer-instance.sh ]] && printf '%s\n' deployment/scripts/customer-instance.sh
    } | sort
  ) > "$actual"
  if ! cmp -s "$expected" "$actual"; then
    rm -f "$expected" "$actual"
    return 1
  fi
  while IFS= read -r path; do
    if ! git -C "$REPO_ROOT" show "refs/tags/$release:$path" | cmp -s - "$root/$path"; then
      rm -f "$expected" "$actual"
      return 1
    fi
  done < "$expected"
  rm -f "$expected" "$actual"
  return 0
}

validate_bundle_archive() {
  local bundle="$1" requested_type="$2" tmp="$3"
  validate_outer_checksum "$bundle"
  if tar -tzf "$bundle" | grep -Eq '(^/|(^|/)\.\.(\/|$))'; then
    die "bundle contains unsafe archive paths"
  fi
  tar -xzf "$bundle" -C "$tmp"
  [[ -d "$tmp/addons" ]] || die "bundle has no addons"
  local manifest="$tmp/manifest.json" lock="$tmp/deployment/runtime/runtime-lock.json"
  [[ -s "$manifest" && -s "$lock" && -s "$tmp/checksums.sha256" ]] || die "bundle is missing manifest, checksums, or runtime lock"
  validate_internal_checksum_coverage "$tmp" || die "bundle internal checksum coverage mismatch"
  (cd "$tmp" && sha256sum -c checksums.sha256 >/dev/null) || die "bundle internal checksum mismatch"
  validate_runtime_lock "$lock"
  BUNDLE_LOCK_SHA="$(sha256sum "$lock" | awk '{print $1}')"
  BUNDLE_ODOO_IMAGE="$(jq -er '.odoo.image' "$lock")"
  BUNDLE_POSTGRES_IMAGE="$(jq -er '.postgres.image' "$lock")"
  jq -e '(.product_version | type == "string") and (.product_version | test("^v[0-9]+\\.[0-9]+\\.[0-9]+(-rc[0-9]+)?$"))' "$manifest" >/dev/null || die "bundle manifest product_version is invalid"
  jq -e '(.source_sha | type == "string") and (.source_sha | test("^[0-9a-f]{40}$"))' "$manifest" >/dev/null || die "bundle manifest source_sha is invalid"
  jq -e --arg type "$requested_type" '(.environment_types | type == "array") and (.environment_types | index($type) != null)' "$manifest" >/dev/null || die "bundle does not authorize the requested environment type"
  jq -e '(.release_tag | type == "string") and (.release_tag == .product_version)' "$manifest" >/dev/null || die "bundle manifest release tag identity is invalid"
  jq -e --arg sha "$BUNDLE_LOCK_SHA" --arg odoo "$BUNDLE_ODOO_IMAGE" --arg postgres "$BUNDLE_POSTGRES_IMAGE" \
    '(.runtime_lock_sha256 == $sha) and (.odoo_image == $odoo) and (.postgres_image == $postgres)' "$manifest" >/dev/null || die "bundle manifest does not match runtime lock"
  jq -e '(.contains_demo_data | type == "boolean") and (.contains_demo_data == false)' "$manifest" >/dev/null || die "bundle Demo safety flag is invalid"
  jq -e '(.contains_private_signing_key | type == "boolean") and (.contains_private_signing_key == false)' "$manifest" >/dev/null || die "bundle private-key safety flag is invalid"
  if tar -tzf "$bundle" | grep -Eiq '(^|/)(\.env|id_rsa|.*private.*key.*|.*\.pem|.*\.key|.*secret.*|.*credentials.*)($|/)'; then
    die "bundle contains a secret or private-key path"
  fi
  if grep -RInaE 'Apex Precision|APEX-HQ|APEX-MFG|APEX-INS|PMQMS-DEMO-2026|odoo-demo|pmqms_demo' "$tmp/addons" >/dev/null 2>&1; then
    die "Demo content detected in bundle"
  fi
  BUNDLE_PRODUCT_VERSION="$(jq -er '.product_version' "$manifest")"
  BUNDLE_SOURCE_SHA="$(jq -er '.source_sha' "$manifest")"
  local expected_release_sha
  expected_release_sha="$(release_tag_sha "$BUNDLE_PRODUCT_VERSION")" || die "approved release tag cannot be resolved locally"
  [[ "$BUNDLE_SOURCE_SHA" == "$expected_release_sha" ]] || die "SOURCE_SHA_DOES_NOT_MATCH_RELEASE_TAG"
  customer_payload_matches_release "$BUNDLE_PRODUCT_VERSION" "$tmp" || die "PAYLOAD_DOES_NOT_MATCH_RELEASE_TAG"
}
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
  upgrade <slug> --bundle <approved-target-bundle.tar.gz> [--to <release-tag>] [--approve-runtime-change]
  customer-ready <slug>
  bundle --output file.tar.gz --release tag
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
SOURCE_RELEASE_SHA=${SOURCE_RELEASE_SHA:-}
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
  "source_release_sha": "${SOURCE_RELEASE_SHA}",
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
  load_release_assets_for_root "$root"
  load_runtime_for_root "$root"
  prepare_operator_write_access "$root"
  master="$(docker run --rm --user root -v "$root/secrets:/secrets:ro" "$ALPINE_IMAGE" sh -eu -c 'cat /secrets/odoo_master_password')"
  sed -e "s#__INSTANCE_SLUG__#$INSTANCE_SLUG#g" -e "s#__INSTANCE_ROOT__#$root#g" -e "s#__HTTP_PORT__#$HTTP_PORT#g" -e "s#__ODOO_IMAGE__#$ODOO_IMAGE#g" -e "s#__POSTGRES_IMAGE__#$POSTGRES_IMAGE#g" "$COMPOSE_TEMPLATE" > "$root/runtime/compose.yml"
  sed -e "s#__ODOO_MASTER_PASSWORD__#$master#g" -e "s#__DATABASE_NAME__#$DATABASE_NAME#g" "$ODOO_TEMPLATE" > "$root/config/odoo.conf"
  chmod 600 "$root/config/odoo.conf"
}

init_instance() {
  local slug="$1"; shift
  slug_ok "$slug" || die "slug must be lowercase, filesystem-safe, and Docker-safe"
  protected_slug "$slug" && die "protected environment slug"
  local type="customer" domain="customer.example.invalid" release="" port="8180" release_assets_source=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --type) type="${2:-}"; shift 2;;
      --domain) domain="${2:-}"; shift 2;;
      --release) release="${2:-}"; shift 2;;
      --release-assets-dir) release_assets_source="${2:-}"; shift 2;;
      --port) port="${2:-}"; shift 2;;
      *) die "unknown init option: $1";;
    esac
  done
  [[ "$type" == customer || "$type" == test ]] || die "type must be customer or test"
  [[ "$port" =~ ^[0-9]+$ && "$port" -ge 1024 && "$port" -le 65535 ]] || die "port must be 1024-65535"
  local root; root="$(instance_dir "$slug")"; [[ ! -e "$root" ]] || die "instance already exists: $slug"
  [[ -n "$release" ]] || die "--release is required"
  release_version_ok "$release" || die "release must be an approved release version"
  umask 077; mkdir -p "$root"/{config,secrets,identity,license,activation,backups,runtime/addons,runtime/release}
  if [[ -n "$release_assets_source" ]]; then
    [[ -s "$release_assets_source/deployment/runtime/runtime-lock.json" ]] ||
      die "release bundle has no runtime lock"
    cp "$release_assets_source/deployment/runtime/runtime-lock.json" "$root/config/runtime-lock.json"
  else
    cp "$RUNTIME_LOCK_FILE" "$root/config/runtime-lock.json"
    release_assets_source="$REPO_ROOT"
  fi
  chmod 600 "$root/config/runtime-lock.json"
  INSTANCE_SLUG="$slug" ENVIRONMENT_TYPE="$type" PRODUCT_VERSION="$release" SOURCE_RELEASE_SHA="${SOURCE_RELEASE_SHA:-}" DOMAIN="$domain" DATABASE_NAME="pmqms_${slug//-/_}" HTTP_PORT="$port"
  random_secret > "$root/secrets/postgres_password"
  random_secret > "$root/secrets/odoo_master_password"
  random_secret > "$root/secrets/initial_admin_password"
  if command -v uuidgen >/dev/null 2>&1; then uuidgen > "$root/config/environment_id"; else cat /proc/sys/kernel/random/uuid > "$root/config/environment_id"; fi
  chmod 755 "$root/config" "$root/secrets" "$root/license" "$root/activation"
  chmod 600 "$root/secrets"/* "$root/config/environment_id"
  install_release_assets "$root" "$release_assets_source"
  write_manifest "$root"; render_files "$root"; cp "$MODULES_FILE" "$root/runtime/modules.txt"; chmod 600 "$root/runtime/modules.txt"
  log "initialized $slug ($type) at $root"
}

credentials() {
  local root; root="$(require_instance "$1")"; load_instance "$root"
  echo "instance_slug=$INSTANCE_SLUG"; echo "environment_type=$ENVIRONMENT_TYPE"; echo "database=$DATABASE_NAME"; echo "technical_login=admin"; echo "technical_password_file=$root/secrets/initial_admin_password"; echo "environment_id_file=$root/config/environment_id"
}

provision() (
  local slug="$1"; shift; local bundle="" type="test" port="8180" tmp="" root=""
  while [[ $# -gt 0 ]]; do case "$1" in --bundle) bundle="${2:-}"; shift 2;; --type) type="${2:-}"; shift 2;; --port) port="${2:-}"; shift 2;; *) die "unknown provision option: $1";; esac; done
  [[ -n "$bundle" && -f "$bundle" ]] || die "bundle not found"
  [[ "$type" == test || "$type" == customer ]] || die "invalid type"
  trap 'provision_cleanup "${root:-}" "${tmp:-}"' EXIT
  tmp="$(new_temp_dir)"
  validate_bundle_archive "$bundle" "$type" "$tmp"
  SOURCE_RELEASE_SHA="$BUNDLE_SOURCE_SHA"
  init_instance "$slug" --type "$type" --port "$port" --release "$BUNDLE_PRODUCT_VERSION" --release-assets-dir "$tmp"
  root="$(require_instance "$slug")"; load_instance "$root"
  cp "$tmp/deployment/runtime/runtime-lock.json" "$root/config/runtime-lock.json"; chmod 600 "$root/config/runtime-lock.json"
  rm -rf "$root/runtime/addons"; mkdir -p "$root/runtime/addons"; cp -a "$tmp/addons/." "$root/runtime/addons/"; cp "$tmp/manifest.json" "$root/config/product-manifest.json"
  jq --arg product "$BUNDLE_PRODUCT_VERSION" --arg source "$BUNDLE_SOURCE_SHA" '.product_version=$product | .source_release_sha=$source' "$root/config/deployment-manifest.json" > "$root/config/deployment-manifest.json.tmp"
  mv "$root/config/deployment-manifest.json.tmp" "$root/config/deployment-manifest.json"
  update_manifest_runtime "$root" "$root/config/runtime-lock.json"
  render_files "$root"
  find "$root/runtime/addons" -type d -exec chmod 755 {} +; find "$root/runtime/addons" -type f -exec chmod 644 {} +; chmod -R a-w "$root/runtime/addons"
  log "provisioned runtime assets for $slug"
)

provision_cleanup() {
  local rc="$?" root="${1:-}" tmp="${2:-}"
  trap - EXIT
  cleanup_temp_dir "$tmp" || rc=1
  if [[ "$rc" != 0 && -n "$root" && -d "$root" ]]; then rm -rf -- "$root"; fi
  exit "$rc"
}

up() { local root; root="$(require_instance "$1")"; load_instance "$root"; compose "$root" up -d; }
down() { local root; root="$(require_instance "$1")"; load_instance "$root"; compose "$root" down; }
config() { local root; root="$(require_instance "$1")"; load_instance "$root"; compose "$root" config >/dev/null; echo "customer_compose=valid"; }
health_root() {
  local root="$1"; load_instance "$root"; compose "$root" up -d >/dev/null; local code=000
  for _ in {1..60}; do code="$(curl -s -o /tmp/pmqms-customer-health.html -w '%{http_code}' "http://127.0.0.1:$HTTP_PORT/web/login?db=$DATABASE_NAME" || true)"; [[ "$code" =~ ^(200|302|303)$ ]] && break; sleep 1; done
  echo "customer_http=$code"; [[ "$code" =~ ^(200|302|303)$ ]]
}
health() { local root; root="$(require_instance "$1")"; health_root "$root"; }

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

license_status_root() {
  local root="$1"; load_instance "$root"
  compose "$root" run --rm odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY'
license = env["pm.qms.license"].sudo().current()
status = env["pm.qms.license"].sudo().current_status()
if not license: print("license_status=missing")
else: print("license_status=%s license_id=%s company=%s/%s sites=%s/%s users=%s/%s environment=%s" % (status["status"], license.license_id, license.company_usage, license.company_limit, license.site_usage, license.site_limit, license.named_user_usage, license.named_user_limit, license.environment_short))
PY
}
license_status() { local root; root="$(require_instance "$1")"; license_status_root "$root"; }

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
user = Users.create({"name": ${user_name@Q}, "login": ${user_login@Q}, "email": ${email@Q}, "password": Path("$mount/password").read_text().strip(), "company_id": company.id, "company_ids": [(6, 0, [company.id])], "group_ids": [(4, quality_group.id)], "qms_organization_ids": [(6, 0, [organization.id])], "qms_site_ids": [(5, 0, 0)], "qms_all_sites": True, "qms_process_ids": [(5, 0, 0)], "qms_all_processes": True})
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
  local source_release_sha="$SOURCE_RELEASE_SHA"
  [[ "$source_release_sha" =~ ^[0-9a-f]{40}$ ]] || die "instance source release identity is invalid"
  [[ -s "$root/config/product-manifest.json" ]] || die "source product manifest is missing"
  jq -e --arg product "$PRODUCT_VERSION" --arg source "$source_release_sha" \
    '(.product_version == $product) and (.source_sha == $source)' \
    "$root/config/product-manifest.json" >/dev/null || die "source product manifest identity does not match instance release"
  cp "$root/config/environment_id" "$tmp/environment_id"
  cp "$root/config/runtime-lock.json" "$tmp/runtime-lock.json"
  cp "$root/config/deployment-manifest.json" "$tmp/deployment-manifest.json"
  cp "$root/config/product-manifest.json" "$tmp/product-manifest.json"
  local component_args=(--component "db.dump=$tmp/db.dump" --component "filestore.tar.gz=$tmp/filestore.tar.gz" --component "environment_id=$tmp/environment_id" --component "runtime-lock.json=$tmp/runtime-lock.json" --component "deployment-manifest.json=$tmp/deployment-manifest.json" --component "product-manifest.json=$tmp/product-manifest.json")
  if docker run --rm --user 100:101 -v "$root/license:/license:ro" "$ALPINE_IMAGE" \
    sh -eu -c 'test -r /license/active.pmql' >/dev/null 2>&1; then
    docker run --rm --user 100:101 -v "$root/license:/license:ro" "$ALPINE_IMAGE" \
      sh -eu -c 'cat /license/active.pmql' > "$tmp/active.pmql"
    chmod 600 "$tmp/active.pmql"
  fi
  if [[ -f "$tmp/active.pmql" ]]; then component_args+=(--component "active.pmql=$tmp/active.pmql"); fi
  quiesce_end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  python3 "$BACKUP_TOOL" pack --output "$archive" --recipient-file "$recipient_file" --source-instance "$INSTANCE_SLUG" --source-database "$DATABASE_NAME" --source-environment-id "$(tr -d '\n' < "$root/config/environment_id")" --product-version "$PRODUCT_VERSION" --source-release-sha "$source_release_sha" --recovery-point-class "$recovery_class" --created-utc "$quiesce_end_utc" --quiesce-start-utc "$quiesce_start_utc" --database-snapshot-utc "$database_snapshot_utc" --filestore-snapshot-utc "$filestore_snapshot_utc" --quiesce-end-utc "$quiesce_end_utc" "${component_args[@]}"
  if [[ -n "$off_host_dir" ]]; then python3 "$BACKUP_TOOL" transfer --archive "$archive" --destination "$off_host_dir"; fi
  echo "backup=$archive"; echo "checksum=$archive.sha256"; echo "manifest=$archive.manifest.json"
)

restore_validate() (
  local source_slug="$1" archive="$2"; shift 2; local identity_file="${PMQMS_BACKUP_IDENTITY_FILE:-}" verification_file=""; while [[ $# -gt 0 ]]; do case "$1" in --identity-file) identity_file="${2:-}"; shift 2;; --verification-file) verification_file="${2:-}"; shift 2;; *) die "unknown restore-validate option: $1";; esac; done
  local source_root; source_root="$(require_instance "$source_slug")"; load_instance "$source_root"; [[ "$ENVIRONMENT_TYPE" == test ]] || die "restore validation source must be test type"
  local source_database="$DATABASE_NAME" source_environment_id="" source_product_version="$PRODUCT_VERSION" source_port="$HTTP_PORT"
  source_environment_id="$(tr -d '\n' < "$ENVIRONMENT_ID_FILE")"
  [[ -n "$identity_file" ]] || die "restore identity is required via --identity-file or PMQMS_BACKUP_IDENTITY_FILE"
  [[ -z "$verification_file" || -f "$verification_file" ]] || die "restore verification file is missing"
  [[ -f "$archive" && -f "$archive.sha256" && -f "$archive.manifest.json" ]] || die "backup archive, manifest, or checksum is missing"
  local recovery="${source_slug}-recovery"; [[ ! -e "$(instance_dir "$recovery")" ]] || die "recovery instance already exists"
  local target target_database="$DATABASE_NAME" tmp="" payload="" source_release_bundle="" historical_addons=""
  local backup_product_version="" backup_release_sha="" backup_environment_id="" backup_runtime_lock_sha=""
  local product_manifest_origin="backup"
  restore_cleanup() {
    local rc=$?
    trap - EXIT
    if [[ -d "$(instance_dir "$recovery")" ]]; then destroy "$recovery" --confirm-ephemeral >/dev/null 2>&1 || rc=1; fi
    cleanup_temp_dir "$tmp" || rc=1
    exit "$rc"
  }
  trap restore_cleanup EXIT
  tmp="$(new_temp_dir)"
  payload="$tmp/payload"
  python3 "$BACKUP_TOOL" unpack --archive "$archive" --identity-file "$identity_file" --expected-instance "$source_slug" --expected-database "$source_database" --output "$payload"
  backup_product_version="$(jq -er '.source.product_version' "$payload/manifest.json")"
  backup_release_sha="$(jq -er '.source.release_sha' "$payload/manifest.json")"
  backup_environment_id="$(jq -er '.source.environment_id' "$payload/manifest.json")"
  [[ "$(jq -er '.source.instance_slug' "$payload/manifest.json")" == "$source_slug" ]] || die "backup source instance identity mismatch"
  [[ "$(jq -er '.source.database_name' "$payload/manifest.json")" == "$source_database" ]] || die "backup source database identity mismatch"
  [[ "$backup_environment_id" == "$source_environment_id" ]] || die "backup source environment identity mismatch"
  [[ "$(tr -d '\n' < "$payload/environment_id")" == "$backup_environment_id" ]] || die "backup environment identity payload mismatch"
  validate_runtime_lock "$payload/runtime-lock.json"
  backup_runtime_lock_sha="$(sha256sum "$payload/runtime-lock.json" | awk '{print $1}')"
  jq -e --arg instance "$source_slug" --arg database "$source_database" --arg product "$backup_product_version" --arg source "$backup_release_sha" \
    '(.instance_slug == $instance) and (.database_name == $database) and (.product_version == $product) and (.source_release_sha == $source)' \
    "$payload/deployment-manifest.json" >/dev/null || die "backup deployment manifest identity mismatch"
  if [[ -s "$payload/product-manifest.json" ]]; then
    cp "$payload/product-manifest.json" "$tmp/product-manifest.json"
  else
    product_manifest_origin="deterministic-backup-identity"
    jq -n --arg product "$backup_product_version" --arg source "$backup_release_sha" --arg lock "$backup_runtime_lock_sha" \
      --arg odoo "$(jq -er '.odoo.image' "$payload/runtime-lock.json")" \
      --arg postgres "$(jq -er '.postgres.image' "$payload/runtime-lock.json")" \
      '{product_version:$product,source_sha:$source,source_release_sha:$source,runtime_lock_sha256:$lock,odoo_image:$odoo,postgres_image:$postgres}' > "$tmp/product-manifest.json"
  fi
  jq -e --arg product "$backup_product_version" --arg source "$backup_release_sha" --arg lock "$backup_runtime_lock_sha" \
    '(.product_version == $product) and (.source_sha == $source) and (.runtime_lock_sha256 == $lock)' \
    "$tmp/product-manifest.json" >/dev/null || die "backup product manifest identity mismatch"
  source_release_bundle="$tmp/source-release"
  release_execution_assets_from_tag "$backup_product_version" "$source_release_bundle" "$backup_release_sha"
  historical_addons="$tmp/historical-addons"
  release_addons_from_tag "$backup_product_version" "$historical_addons" "$backup_release_sha"
  mkdir -p "$source_release_bundle/deployment/runtime"
  cp "$payload/runtime-lock.json" "$source_release_bundle/deployment/runtime/runtime-lock.json"
  SOURCE_RELEASE_SHA="$backup_release_sha" init_instance "$recovery" --type test --port "$((source_port + 1))" --release "$backup_product_version" --release-assets-dir "$source_release_bundle"
  target="$(require_instance "$recovery")"; load_instance "$target"; target_database="$DATABASE_NAME"
  cp "$payload/environment_id" "$target/config/environment_id"; chmod 600 "$target/config/environment_id"
  if [[ -f "$payload/active.pmql" ]]; then
    cp "$payload/active.pmql" "$target/license/active.pmql"
    docker run --rm --user root -v "$target/license:/license" "$ALPINE_IMAGE" sh -eu -c 'chown 100:101 /license/active.pmql && chmod 600 /license/active.pmql'
  fi
  cp "$payload/runtime-lock.json" "$target/config/runtime-lock.json"; chmod 600 "$target/config/runtime-lock.json"
  cp "$payload/deployment-manifest.json" "$target/config/deployment-manifest.json"
  jq --arg slug "$recovery" --arg type "test" --arg product "$backup_product_version" \
    '.instance_slug=$slug | .environment_type=$type | .product_version=$product | .deployment_state="restored"' \
    "$target/config/deployment-manifest.json" > "$target/config/deployment-manifest.json.tmp"
  mv "$target/config/deployment-manifest.json.tmp" "$target/config/deployment-manifest.json"
  chmod 600 "$target/config/deployment-manifest.json"
  cp "$tmp/product-manifest.json" "$target/config/product-manifest.json"
  chmod 600 "$target/config/product-manifest.json"
  PRODUCT_VERSION="$backup_product_version"
  SOURCE_RELEASE_SHA="$backup_release_sha"
  update_manifest_runtime "$target" "$target/config/runtime-lock.json"
  runtime_manifest_gate "$target" || die "recovery runtime identity is invalid"
  render_files "$target"
  rm -rf -- "$target/runtime/addons"
  mkdir -p "$target/runtime/addons"
  cp -a "$historical_addons/addons/." "$target/runtime/addons/"
  find "$target/runtime/addons" -type d -exec chmod 755 {} +
  find "$target/runtime/addons" -type f -exec chmod 644 {} +
  chmod -R a-w "$target/runtime/addons"
  local restored_modules_sha restored_compose_sha restored_odoo_sha restored_addons_sha
  restored_modules_sha="$(sha256sum "$target/runtime/release/deployment/customer/modules.txt" | awk '{print $1}')"
  restored_compose_sha="$(sha256sum "$target/runtime/release/deployment/docker/customer/compose.yml.template" | awk '{print $1}')"
  restored_odoo_sha="$(sha256sum "$target/runtime/release/deployment/docker/customer/odoo.conf.template" | awk '{print $1}')"
  restored_addons_sha="$(cd "$target/runtime" && find addons -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')"
  echo "restore_source_release_tag=$backup_product_version"
  echo "restore_source_release_sha=$backup_release_sha"
  echo "restore_release_assets_origin=approved-tag"
  echo "restore_addons_origin=approved-tag"
  echo "restore_addons_sha256=$restored_addons_sha"
  echo "restore_backup_product_manifest_origin=$product_manifest_origin"
  echo "restore_runtime_lock_sha256=$backup_runtime_lock_sha"
  echo "restore_deployment_manifest_origin=backup"
  echo "restore_modules_sha256=$restored_modules_sha"
  echo "restore_compose_template_sha256=$restored_compose_sha"
  echo "restore_odoo_template_sha256=$restored_odoo_sha"
  compose "$target" up -d postgres >/dev/null
  local postgres_ready=0; for _ in {1..30}; do if compose "$target" exec -T postgres pg_isready -U odoo -d postgres >/dev/null 2>&1; then postgres_ready=1; break; fi; sleep 1; done
  [[ "$postgres_ready" == 1 ]] || die "recovery PostgreSQL did not become ready"
  compose "$target" exec -T postgres createdb -U odoo "$target_database" >/dev/null
  compose "$target" exec -T postgres pg_restore -U odoo -d "$target_database" --no-owner --role=odoo < "$payload/db.dump"
  docker run --rm --user root -e SOURCE_DATABASE="$source_database" -e TARGET_DATABASE="$target_database" -v "pmqms_${recovery}_odoo_data:/odoo-data" -v "$payload:/backup:ro" "$ALPINE_IMAGE" sh -eu -c '
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
    chown -R 100:101 /odoo-data
  '
  if ! health_root "$target"; then
    docker logs --tail=120 "pmqms-customer-${recovery}-odoo-1" >&2 || true
    die "recovery Odoo did not become healthy"
  fi
  local license_output; license_output="$(license_status_root "$target")"; [[ "$license_output" == *"license_status=valid"* || "$license_output" == *"license_status=expiring"* ]] || die "recovery license is not valid"
  echo "restore_release_identity=PASS"
  echo "restore_runtime_identity=PASS"
  echo "restore_license=PASS"
  if [[ -n "$verification_file" ]]; then
    local verification_dir; verification_dir="$(dirname "$verification_file")"
    compose "$target" run --rm -v "$verification_file:/tmp/recovery-verification.json:ro" -v "$verification_dir:/tmp/recovery-evidence" odoo odoo shell -d "$target_database" --log-level=error <<'PY'
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
  customer_ready "$recovery" >/dev/null || die "recovery customer-ready gate failed"
  echo "restore_customer_ready=PASS"
  echo "restore_validation=pass"
)

retention() (
  local slug="$1"; shift; local root; root="$(require_instance "$slug")"; load_instance "$root"
  local args=(--directory "$root/backups"); while [[ $# -gt 0 ]]; do case "$1" in --now) args+=(--now "${2:-}"); shift 2;; --apply) args+=(--apply); shift;; *) die "unknown retention option: $1";; esac; done
  python3 "$BACKUP_TOOL" retention "${args[@]}"
)

bundle() (
  local output="" release=""
  while [[ $# -gt 0 ]]; do case "$1" in --output) output="${2:-}"; shift 2;; --release) release="${2:-}"; shift 2;; *) die "unknown bundle option: $1";; esac; done
  [[ -n "$output" ]] || die "--output is required"
  [[ -n "$release" ]] || die "--release is required"
  local sha; sha="$(release_tag_sha "$release")" || die "approved release tag not found"
  local tmp=""; trap 'cleanup_temp_dir "$tmp"' EXIT; tmp="$(new_temp_dir)"
  git -C "$REPO_ROOT" archive "$release" "${CUSTOMER_PAYLOAD_PATHS[@]}" | tar -x -C "$tmp"
  [[ -s "$tmp/deployment/runtime/runtime-lock.json" ]] || die "release has no runtime lock"
  rm -rf "$tmp/deployment/demo" "$tmp/deployment/docker/demo"; find "$tmp/addons" -type d -name __pycache__ -prune -exec rm -rf {} +; find "$tmp/addons" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
  local lock_sha odoo_image postgres_image
  lock_sha="$(sha256sum "$tmp/deployment/runtime/runtime-lock.json" | awk '{print $1}')"
  odoo_image="$(jq -r '.odoo.image' "$tmp/deployment/runtime/runtime-lock.json")"
  postgres_image="$(jq -r '.postgres.image' "$tmp/deployment/runtime/runtime-lock.json")"
  jq -n --arg product "$release" --arg source "$sha" --arg built "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg lock "$lock_sha" --arg odoo "$odoo_image" --arg postgres "$postgres_image" '{product_version:$product,release_tag:$product,source_sha:$source,built_at:$built,environment_types:["customer","test"],runtime_lock_sha256:$lock,odoo_image:$odoo,postgres_image:$postgres,contains_demo_data:false,contains_private_signing_key:false}' > "$tmp/manifest.json"
  (cd "$tmp" && { find addons deployment -type f -print0; printf 'manifest.json\0'; } | sort -z | xargs -0 sha256sum > checksums.sha256)
  if find "$tmp" -type f \( -name '.env' -o -name 'id_rsa' -o -name '*.pem' -o -name '*.key' \) -print -quit | grep -q .; then die "private key or secret path detected"; fi
  mkdir -p "$(dirname "$output")"; tar -C "$tmp" -czf "$output" .; printf '%s  %s\n' "$(sha256sum "$output" | awk '{print $1}')" "$(basename "$output")" > "$output.sha256"
  if tar -xOzf "$output" ./manifest.json 2>/dev/null | grep -Eqi 'Apex Precision|APEX-HQ|APEX-MFG|APEX-INS|PMQMS-DEMO-2026'; then die "Demo content detected in bundle"; fi
  if grep -RInaE 'Apex Precision|APEX-HQ|APEX-MFG|APEX-INS|PMQMS-DEMO-2026|odoo-demo|pmqms_demo' "$tmp/addons" >/dev/null 2>&1; then die "Demo content detected in bundle"; fi
  echo "bundle=$output"; echo "checksum=$output.sha256"; echo "product_version=$release"; echo "source_sha=$sha"
)

set_instance_identity() {
  local root="$1" product="$2" source="$3" env_file="$root/config/instance.env"
  local temp="$env_file.tmp"
  sed -e "s/^PRODUCT_VERSION=.*/PRODUCT_VERSION=$product/" \
    -e "s/^SOURCE_RELEASE_SHA=.*/SOURCE_RELEASE_SHA=$source/" \
    "$env_file" > "$temp"
  mv "$temp" "$env_file"
  chmod 600 "$env_file"
}

set_upgrade_manifest_state() {
  local root="$1" state="$2" target_product="$3" target_source="$4" \
    previous_product="$5" previous_source="$6" failure_stage="${7:-}"
  prepare_operator_write_access "$root"
  local manifest="$root/config/deployment-manifest.json"
  local temp="$manifest.tmp"
  jq --arg state "$state" --arg target "$target_product" --arg target_source "$target_source" \
    --arg previous "$previous_product" --arg previous_source "$previous_source" --arg stage "$failure_stage" \
    '.deployment_state=$state | .previous_product_version=$previous | .previous_source_release_sha=$previous_source | .product_version=$target | .source_release_sha=$target_source' \
    "$manifest" > "$temp"
  if [[ -n "$failure_stage" ]]; then
    jq --arg target "$target_product" --arg stage "$failure_stage" \
      '.last_upgrade_target=$target | .last_upgrade_result="rolled_back" | .last_upgrade_failure_stage=$stage | .deployment_state="deployed"' \
      "$temp" > "$temp.next"
    mv "$temp.next" "$temp"
  fi
  mv "$temp" "$manifest"
  chmod 600 "$manifest"
}

stage_target_bundle() {
  local bundle_root="$1" stage="$2"
  mkdir -p "$stage/release/deployment/customer" "$stage/release/deployment/docker/customer"
  mkdir -p "$stage/addons"
  cp -a "$bundle_root/addons/." "$stage/addons/"
  find "$stage/addons" -type d -exec chmod 755 {} +
  find "$stage/addons" -type f -exec chmod 644 {} +
  cp "$bundle_root/deployment/customer/modules.txt" "$stage/release/deployment/customer/modules.txt"
  cp "$bundle_root/deployment/docker/customer/compose.yml.template" "$stage/release/deployment/docker/customer/compose.yml.template"
  cp "$bundle_root/deployment/docker/customer/odoo.conf.template" "$stage/release/deployment/docker/customer/odoo.conf.template"
  cp "$bundle_root/deployment/runtime/runtime-lock.json" "$stage/runtime-lock.json"
  cp "$bundle_root/manifest.json" "$stage/product-manifest.json"
  chmod 700 "$stage/release" "$stage/release/deployment" "$stage/release/deployment/customer" "$stage/release/deployment/docker" "$stage/release/deployment/docker/customer"
  chmod 600 "$stage/release/deployment/customer/modules.txt" "$stage/release/deployment/docker/customer/compose.yml.template" "$stage/release/deployment/docker/customer/odoo.conf.template"
  chmod 600 "$stage/runtime-lock.json" "$stage/product-manifest.json"
}

create_rollback_snapshot() {
  local root="$1" snapshot="$2" current_release_root="${3:-}"
  umask 077
  mkdir -m 700 -p "$snapshot/config" "$snapshot/runtime"
  for file in instance.env deployment-manifest.json product-manifest.json runtime-lock.json environment_id; do
    local source=""
    case "$file" in
      instance.env|deployment-manifest.json|product-manifest.json|runtime-lock.json) source="$root/config/$file";;
      environment_id) source="$root/config/environment_id";;
    esac
    [[ -f "$source" ]] && cp "$source" "$snapshot/config/$(basename "$source")"
  done
  [[ -d "$root/runtime/addons" ]] && cp -R --no-preserve=mode,ownership "$root/runtime/addons" "$snapshot/addons"
  if [[ -d "$root/runtime/release" ]]; then
    release_assets_complete "$root/runtime/release" || die "instance release execution assets are incomplete"
    cp -R --no-preserve=mode,ownership "$root/runtime/release" "$snapshot/release"
  else
    [[ -n "$current_release_root" ]] || die "current release execution assets are unavailable"
    release_assets_complete "$current_release_root" || die "current release execution assets are incomplete"
    mkdir -p "$snapshot/release"
    cp -R --no-preserve=mode,ownership "$current_release_root/." "$snapshot/release/"
  fi
  if [[ -d "$root/runtime/release" ]]; then
    [[ -f "$root/runtime/modules.txt" ]] && cp --no-preserve=mode,ownership "$root/runtime/modules.txt" "$snapshot/modules.txt"
  else
    [[ -f "$current_release_root/deployment/customer/modules.txt" ]] || die "current release module list is unavailable"
    cp --no-preserve=mode,ownership "$current_release_root/deployment/customer/modules.txt" "$snapshot/modules.txt"
  fi
  if docker run --rm --user 100:101 -v "$root/license:/license:ro" "$ALPINE_IMAGE" \
    sh -eu -c 'test -r /license/active.pmql' >/dev/null 2>&1; then
    docker run --rm --user 100:101 -v "$root/license:/license:ro" "$ALPINE_IMAGE" \
      sh -eu -c 'cat /license/active.pmql' > "$snapshot/active.pmql"
    chmod 600 "$snapshot/active.pmql"
  fi
  find "$snapshot" -type d -exec chmod 700 {} +
  find "$snapshot" -type f -exec chmod 600 {} +
}

capture_rollback_data() {
  local root="$1" snapshot="$2" host_uid="$(id -u)" host_gid="$(id -g)"
  load_instance "$root"
  compose "$root" up -d postgres >/dev/null
  compose "$root" exec -T postgres pg_dump -U odoo -d "$DATABASE_NAME" --format=custom > "$snapshot/db.dump"
  [[ -s "$snapshot/db.dump" ]] || die "ephemeral database snapshot is empty"
  docker run --rm --user root -e HOST_UID="$host_uid" -e HOST_GID="$host_gid" \
    -v "pmqms_${INSTANCE_SLUG}_odoo_data:/odoo-data:ro" -v "$snapshot:/rollback" "$ALPINE_IMAGE" sh -c \
    "cd /odoo-data && if [ -d filestore/\${DATABASE_NAME} ]; then tar -czf /rollback/filestore.tar.gz filestore/\${DATABASE_NAME}; else tar -czf /rollback/filestore.tar.gz --files-from /dev/null; fi; chown \${HOST_UID}:\${HOST_GID} /rollback/filestore.tar.gz; chmod 600 /rollback/filestore.tar.gz"
  [[ -s "$snapshot/filestore.tar.gz" ]] || die "ephemeral filestore snapshot is missing"
  chmod 600 "$snapshot/db.dump" "$snapshot/filestore.tar.gz"
}

restore_rollback_data() {
  local root="$1" snapshot="$2"
  load_instance "$root"
  [[ -s "$snapshot/db.dump" && -s "$snapshot/filestore.tar.gz" ]] || die "rollback data snapshot is incomplete"
  compose "$root" up -d postgres >/dev/null || return 1
  compose "$root" exec -T postgres dropdb -U odoo --if-exists "$DATABASE_NAME" >/dev/null || return 1
  compose "$root" exec -T postgres createdb -U odoo "$DATABASE_NAME" >/dev/null || return 1
  compose "$root" exec -T postgres pg_restore -U odoo -d "$DATABASE_NAME" --no-owner --role=odoo < "$snapshot/db.dump" || return 1
  docker run --rm --user root -e DATABASE_NAME="$DATABASE_NAME" -v "pmqms_${INSTANCE_SLUG}_odoo_data:/odoo-data" -v "$snapshot:/rollback:ro" "$ALPINE_IMAGE" sh -eu -c '
    work=/tmp/filestore-rollback
    mkdir -p "$work"
    tar -tzf /rollback/filestore.tar.gz > "$work/members"
    while IFS= read -r member; do
      case "$member" in
        "filestore/"|"filestore/$DATABASE_NAME"|"filestore/$DATABASE_NAME/"*|"./filestore/"|"./filestore/$DATABASE_NAME"|"./filestore/$DATABASE_NAME/"*) ;;
        *) echo "unexpected rollback filestore member: $member" >&2; exit 1 ;;
      esac
      case "$member" in /**|*".."*) echo "unsafe rollback filestore member" >&2; exit 1 ;; esac
    done < "$work/members"
    tar -xzf /rollback/filestore.tar.gz -C "$work"
    mkdir -p /odoo-data/filestore
    rm -rf "/odoo-data/filestore/$DATABASE_NAME"
    if [ -d "$work/filestore/$DATABASE_NAME" ]; then
      mv "$work/filestore/$DATABASE_NAME" "/odoo-data/filestore/$DATABASE_NAME"
    fi
    chown -R 100:101 /odoo-data
  ' || return 1
}

restore_rollback_files() {
  local root="$1" snapshot="$2" host_uid="$(id -u)" host_gid="$(id -g)"
  docker run --rm --user root -e HOST_UID="$host_uid" -e HOST_GID="$host_gid" \
    -v "$root:/instance" -v "$snapshot:/snapshot:ro" "$ALPINE_IMAGE" sh -eu -c '
      rm -rf /instance/runtime/addons /instance/runtime/release /instance/runtime/.m30-8-previous
      mkdir -p /instance/runtime
      cp -R /snapshot/addons /instance/runtime/addons
      cp -R /snapshot/release /instance/runtime/release
      cp /snapshot/config/instance.env /instance/config/instance.env
      cp /snapshot/config/deployment-manifest.json /instance/config/deployment-manifest.json
      cp /snapshot/config/product-manifest.json /instance/config/product-manifest.json
      cp /snapshot/config/runtime-lock.json /instance/config/runtime-lock.json
      cp /snapshot/config/environment_id /instance/config/environment_id
      if [ -f /snapshot/modules.txt ]; then cp /snapshot/modules.txt /instance/runtime/modules.txt; else rm -f /instance/runtime/modules.txt; fi
      chown -R "$HOST_UID:$HOST_GID" /instance/config /instance/runtime
      find /instance/runtime/addons -type d -exec chmod 755 {} +
      find /instance/runtime/addons -type f -exec chmod 644 {} +
      find /instance/runtime/release -type d -exec chmod 700 {} +
      find /instance/runtime/release -type f -exec chmod 600 {} +
      chmod 600 /instance/runtime/modules.txt 2>/dev/null || true
      chmod 600 /instance/config/instance.env /instance/config/deployment-manifest.json /instance/config/product-manifest.json /instance/config/runtime-lock.json /instance/config/environment_id
    ' || return 1
  if [[ -f "$snapshot/active.pmql" ]]; then
    cat "$snapshot/active.pmql" | docker run --rm -i --user 100:101 -v "$root/license:/license" "$ALPINE_IMAGE" \
      sh -eu -c 'cat > /license/active.pmql && chmod 600 /license/active.pmql' || return 1
  fi
}

restore_rollback_snapshot() {
  local root="$1" snapshot="$2" slug="$3"
  compose "$root" down >/dev/null 2>&1 || true
  restore_rollback_files "$root" "$snapshot" || { echo "ROLLBACK_RESTORE_STAGE=files" >&2; return 1; }
  load_instance "$root" || { echo "ROLLBACK_RESTORE_STAGE=instance-load" >&2; return 1; }
  render_files "$root" || { echo "ROLLBACK_RESTORE_STAGE=render" >&2; return 1; }
  restore_rollback_data "$root" "$snapshot" || { echo "ROLLBACK_RESTORE_STAGE=data" >&2; return 1; }
  compose "$root" up -d >/dev/null || { echo "ROLLBACK_RESTORE_STAGE=runtime-start" >&2; return 1; }
  customer_ready "$slug" || { echo "ROLLBACK_RESTORE_STAGE=customer-ready" >&2; return 1; }
}

activate_target_release() {
  local root="$1" stage="$2" target_product="$3" target_source="$4" current_release_root="${5:-}" previous="$root/runtime/.m30-8-previous"
  prepare_operator_write_access "$root"
  [[ ! -e "$previous" ]] || die "stale upgrade replacement directory exists"
  mkdir -m 700 "$previous"
  mv "$root/runtime/addons" "$previous/addons"
  if [[ -d "$root/runtime/release" ]]; then
    mv "$root/runtime/release" "$previous/release"
  else
    [[ -n "$current_release_root" ]] || die "current release execution assets are unavailable"
    release_assets_complete "$current_release_root" || die "current release execution assets are incomplete"
    mkdir -p "$previous/release"
    cp -R --no-preserve=mode,ownership "$current_release_root/." "$previous/release/"
  fi
  mv "$stage/addons" "$root/runtime/addons"
  find "$root/runtime/addons" -type d -exec chmod 755 {} +
  find "$root/runtime/addons" -type f -exec chmod 644 {} +
  chmod -R a-w "$root/runtime/addons"
  mv "$stage/release" "$root/runtime/release"
  cp "$stage/runtime-lock.json" "$root/config/runtime-lock.json"
  cp "$stage/product-manifest.json" "$root/config/product-manifest.json"
  set_instance_identity "$root" "$target_product" "$target_source"
  set_upgrade_manifest_state "$root" upgrade-applying "$target_product" "$target_source" "$PRODUCT_VERSION" "$SOURCE_RELEASE_SHA"
  chmod 600 "$root/config/runtime-lock.json" "$root/config/product-manifest.json"
  load_instance "$root"
  render_files "$root"
  cp "$MODULES_FILE" "$root/runtime/modules.txt"
  chmod 600 "$root/runtime/modules.txt"
}

runtime_major() {
  sed -nE 's/^[^:]+:([0-9]+)(@.*)?$/\1/p' <<<"$1"
}

update_modules_from_instance() {
  local root="$1" modules
  load_instance "$root"
  modules="$(module_list)"
  [[ -n "$modules" ]] || die "target release module list is empty"
  compose "$root" up -d postgres >/dev/null
  compose "$root" run --rm odoo odoo -d "$DATABASE_NAME" -u "$modules" --without-demo=all --stop-after-init
}

upgrade_rollback() {
  local root="$1" snapshot="$2" slug="$3" target_product="$4" failure_stage="$5"
  if restore_rollback_snapshot "$root" "$snapshot" "$slug"; then
    set_upgrade_manifest_state "$root" deployed "$PRODUCT_VERSION" "$SOURCE_RELEASE_SHA" "$PRODUCT_VERSION" "$SOURCE_RELEASE_SHA" "$failure_stage"
    echo "UPGRADE_RESULT=FAILED"
    echo "ROLLBACK_RESULT=PASS"
    echo "ROLLBACK_FAILURE_STAGE=$failure_stage"
    return 0
  fi
  compose "$root" down >/dev/null 2>&1 || true
  echo "UPGRADE_RESULT=FAILED"
  echo "ROLLBACK_RESULT=FAILED"
  echo "ROLLBACK_FAILURE_STAGE=$failure_stage"
  echo "ROLLBACK_EVIDENCE_PRESERVED=$snapshot"
  return 1
}

upgrade_failure() {
  local root="$1" snapshot="$2" slug="$3" target_product="$4" failure_stage="$5"
  log "upgrade failed at $failure_stage; starting automatic rollback"
  if upgrade_rollback "$root" "$snapshot" "$slug" "$target_product" "$failure_stage"; then
    return 1
  fi
  preserve_recovery=1
  return 2
}

upgrade() (
  local slug="$1"; shift
  local target_bundle="" asserted_release="" approve_runtime_change=0
  local root target_work target_extract target_stage snapshot backup_output archive
  local current_product current_source current_tag_sha current_release_root target_product target_source current_lock_sha target_lock_sha
  local current_postgres target_postgres current_postgres_major target_postgres_major
  local previous_dir="" preserve_recovery=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --bundle) target_bundle="${2:-}"; shift 2;;
      --to) asserted_release="${2:-}"; shift 2;;
      --approve-runtime-change) approve_runtime_change=1; shift;;
      *) die "unknown upgrade option: $1";;
    esac
  done
  [[ -n "$target_bundle" && -f "$target_bundle" ]] || die "--bundle approved target bundle is required"
  root="$(require_instance "$slug")"
  load_instance "$root"
  current_product="$PRODUCT_VERSION"
  current_source="$SOURCE_RELEASE_SHA"
  [[ "$current_source" =~ ^[0-9a-f]{40}$ ]] || die "instance source release identity is invalid"
  local current_state
  current_state="$(jq -r '.deployment_state // ""' "$root/config/deployment-manifest.json")"
  [[ "$current_state" != upgrade-applying && "$current_state" != rollback-failed ]] || die "instance has an interrupted upgrade state; recover it before retrying"
  target_work="$(new_temp_dir)"; target_extract="$target_work/target"; target_stage="$target_work/stage"; snapshot="$target_work/rollback-snapshot"
  mkdir -p "$target_extract" "$target_stage"
  trap 'rc=$?; trap - EXIT; if [[ "${preserve_recovery:-0}" != 1 ]]; then cleanup_temp_dir "${target_work:-}"; fi; exit "$rc"' EXIT

  validate_bundle_archive "$target_bundle" "$ENVIRONMENT_TYPE" "$target_extract"
  target_product="$BUNDLE_PRODUCT_VERSION"
  target_source="$BUNDLE_SOURCE_SHA"
  [[ -z "$asserted_release" || "$asserted_release" == "$target_product" ]] || die "--to does not match bundle.product_version"
  [[ "$target_product" != "$current_product" ]] || die "REJECT_SAME_RELEASE"
  [[ "$target_source" != "$current_source" ]] || die "REJECT_SAME_SOURCE"
  release_version_not_older "$current_product" "$target_product" || die "REJECT_DOWNGRADE"
  current_tag_sha="$(release_tag_sha "$current_product")" || die "approved current release tag not found: $current_product"
  [[ "$current_tag_sha" == "$current_source" ]] || die "current release tag/source identity mismatch"
  git -C "$REPO_ROOT" merge-base --is-ancestor "$current_source" "$target_source" || die "REJECT_UNRELATED_OR_DOWNGRADE_LINEAGE"
  runtime_verify_lock "$target_extract/deployment/runtime/runtime-lock.json"
  current_lock_sha="$(sha256sum "$root/config/runtime-lock.json" | awk '{print $1}')"
  target_lock_sha="$(sha256sum "$target_extract/deployment/runtime/runtime-lock.json" | awk '{print $1}')"
  current_postgres="$(jq -er '.postgres.image' "$root/config/runtime-lock.json")"
  target_postgres="$(jq -er '.postgres.image' "$target_extract/deployment/runtime/runtime-lock.json")"
  current_postgres_major="$(runtime_major "$current_postgres")"
  target_postgres_major="$(runtime_major "$target_postgres")"
  [[ "$current_postgres_major" == "$target_postgres_major" ]] || die "REJECT_POSTGRES_MAJOR_CHANGE"
  if [[ "$current_lock_sha" != "$target_lock_sha" && "$approve_runtime_change" != 1 ]]; then
    die "runtime lock changes require --approve-runtime-change"
  fi
  if ! customer_ready "$slug" >/dev/null; then
    die "CURRENT_READY_PREFLIGHT_FAILED"
  fi
  current_release_root="$target_work/current-release"
  if [[ -e "$root/runtime/release" ]]; then
    release_assets_complete "$root/runtime/release" || die "instance release execution assets are incomplete"
    mkdir -p "$current_release_root"
    cp -R --no-preserve=mode,ownership "$root/runtime/release/." "$current_release_root/"
  else
    release_execution_assets_from_tag "$current_product" "$current_release_root" "$current_source"
  fi
  stage_target_bundle "$target_extract" "$target_stage"
  backup_output="$(backup "$slug")" || die "DURABLE_BACKUP_FAILED"
  archive="$(sed -n 's/^backup=//p' <<<"$backup_output")"
  [[ -s "$archive" && -s "$archive.sha256" && -s "$archive.manifest.json" ]] || die "durable backup integrity metadata is missing"
  compose "$root" stop odoo >/dev/null
  [[ "$(compose "$root" ps -q odoo 2>/dev/null | head -1)" == "" ]] || true
  create_rollback_snapshot "$root" "$snapshot" "$current_release_root"
  capture_rollback_data "$root" "$snapshot" || die "EPHEMERAL_ROLLBACK_SNAPSHOT_FAILED"
  activate_target_release "$root" "$target_stage" "$target_product" "$target_source" "$current_release_root" || upgrade_failure "$root" "$snapshot" "$slug" "$target_product" target-activation
  if ! update_modules_from_instance "$root"; then
    upgrade_failure "$root" "$snapshot" "$slug" "$target_product" module-update
    return $?
  fi
  if ! compose "$root" up -d >/dev/null; then
    upgrade_failure "$root" "$snapshot" "$slug" "$target_product" runtime-start
    return $?
  fi
  if ! health_root "$root" >/dev/null; then
    upgrade_failure "$root" "$snapshot" "$slug" "$target_product" health
    return $?
  fi
  if ! customer_ready "$slug" >/dev/null; then
    upgrade_failure "$root" "$snapshot" "$slug" "$target_product" customer-ready
    return $?
  fi
  set_upgrade_manifest_state "$root" deployed "$target_product" "$target_source" "$current_product" "$current_source"
  jq --arg target "$target_product" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '.last_upgrade_target=$target | .last_upgrade_result="success" | .upgraded_at=$now' \
    "$root/config/deployment-manifest.json" > "$root/config/deployment-manifest.json.tmp"
  mv "$root/config/deployment-manifest.json.tmp" "$root/config/deployment-manifest.json"
  chmod 600 "$root/config/deployment-manifest.json"
  previous_dir="$root/runtime/.m30-8-previous"
  if [[ -e "$previous_dir" ]]; then
    docker run --rm --user root -v "$previous_dir:/previous" "$ALPINE_IMAGE" \
      sh -eu -c 'chmod -R u+rwX /previous'
  fi
  rm -rf -- "$previous_dir"
  echo "UPGRADE_RESULT=PASS"
  echo "TARGET_PRODUCT_VERSION=$target_product"
  echo "TARGET_SOURCE_RELEASE_SHA=$target_source"
  echo "MODULE_UPDATE=PASS"
  echo "POST_UPGRADE_CUSTOMER_READY=PASS"
)

customer_ready() {
  local root; root="$(require_instance "$1")"; load_instance "$root"
  local ok=1 release_ok=0 runtime_ok=0 application_ok=0 license_ok=0 first_user_ok=0 qms_scope_ok=0
  if runtime_manifest_gate "$root"; then release_ok=1; runtime_ok=1; else ok=0; fi
  if health "$1"; then
    local odoo_id postgres_id image_ok=1
    odoo_id="$(compose "$root" ps -q odoo)"
    postgres_id="$(compose "$root" ps -q postgres)"
    [[ -n "$odoo_id" && "$(docker inspect -f '{{.Image}}' "$odoo_id")" == "$(docker image inspect -f '{{.Id}}' "$ODOO_IMAGE")" ]] || image_ok=0
    [[ -n "$postgres_id" && "$(docker inspect -f '{{.Image}}' "$postgres_id")" == "$(docker image inspect -f '{{.Id}}' "$POSTGRES_IMAGE")" ]] || image_ok=0
    if [[ "$image_ok" == 1 ]]; then application_ok=1; else ok=0; fi
  else
    ok=0
  fi
  if docker run --rm --user 100:101 -v "$root/license:/license:ro" -v "$root/config:/config:ro" -v "$root/secrets:/secrets:ro" "$ALPINE_IMAGE" sh -c 'test -r /license/active.pmql && test -r /config/environment_id && test -r /secrets/postgres_password && test -r /secrets/odoo_master_password'; then :; else
    ok=0
  fi
  local probe_output="" probe_status=0
  probe_output="$(compose "$root" run --rm odoo odoo shell -d "$DATABASE_NAME" --log-level=error <<'PY'
Organization = env["pm.qms.organization"].sudo()
Person = env["pm.qms.person"].sudo()
organization = Organization.search([("organization_kind", "=", "operational")], order="id", limit=1)
person = Person.search([("organization_id", "=", organization.id), ("user_id", "!=", False)], order="id", limit=1) if organization else Person.browse()
user = person.user_id if person else env["res.users"].browse()
try:
    license = env["pm.qms.license"].sudo().current()
    license_status = env["pm.qms.license"].sudo().current_status()["status"]
except Exception:
    license = env["pm.qms.license"].browse()
    license_status = "error"

first_user_ok = bool(person and user and user.active and user.has_group("pm_qms_core.group_qms_quality_manager") and not user.has_group("base.group_system"))
scope_ok = bool(first_user_ok and user.qms_scope_configured)
organization_ok = bool(scope_ok and organization in user.qms_organization_ids and organization in user.qms_effective_organization_ids)
sites = organization.site_ids.filtered(lambda site: site.active) if organization else env["pm.qms.site"].browse()
sites_ok = bool(scope_ok and user.qms_all_sites and all(site in user.qms_effective_site_ids for site in sites))
processes_ok = bool(scope_ok and user.qms_all_processes)
license_ok = bool(license and license_status in ("valid", "expiring"))
application_ok = bool(organization and person and user and user.active)

print("customer_ready_application=%s" % ("pass" if application_ok else "fail"))
print("CUSTOMER_READY_PROBE_FIRST_USER=%s" % ("pass" if first_user_ok else "fail"))
print("CUSTOMER_READY_PROBE_LICENSE=%s" % ("pass" if license_ok else "fail"))
print("CUSTOMER_READY_QMS_SCOPE=%s" % ("pass" if scope_ok else "fail"))
print("CUSTOMER_READY_QMS_ORGANIZATION=%s" % ("pass" if organization_ok else "fail"))
print("CUSTOMER_READY_QMS_SITES=%s" % ("pass" if sites_ok else "fail"))
print("CUSTOMER_READY_QMS_PROCESSES=%s" % ("pass" if processes_ok else "fail"))
if not (application_ok and first_user_ok and license_ok and scope_ok and organization_ok and sites_ok and processes_ok):
    raise RuntimeError("Customer QMS scope is not ready")
PY
)" || probe_status=$?

  probe_flag() {
    local key="$1"
    grep -Fqx "$key=pass" <<<"$probe_output"
  }
  if probe_flag "CUSTOMER_READY_PROBE_FIRST_USER"; then first_user_ok=1; else ok=0; fi
  if probe_flag "CUSTOMER_READY_PROBE_LICENSE"; then license_ok=1; else ok=0; fi
  if [[ "$probe_status" == 0 ]] &&
    probe_flag CUSTOMER_READY_QMS_SCOPE &&
    probe_flag CUSTOMER_READY_QMS_ORGANIZATION &&
    probe_flag CUSTOMER_READY_QMS_SITES &&
    probe_flag CUSTOMER_READY_QMS_PROCESSES
  then
    qms_scope_ok=1
  else
    ok=0
  fi
  if probe_flag "customer_ready_application"; then
    echo "customer_ready_application=pass"
  else
    echo "customer_ready_application=fail"
    ok=0
  fi
  [[ "$release_ok" == 1 ]] && echo "CUSTOMER_READY_RELEASE_IDENTITY=pass" || echo "CUSTOMER_READY_RELEASE_IDENTITY=fail"
  [[ "$runtime_ok" == 1 ]] && echo "CUSTOMER_READY_RUNTIME_IDENTITY=pass" || echo "CUSTOMER_READY_RUNTIME_IDENTITY=fail"
  [[ "$application_ok" == 1 ]] && echo "CUSTOMER_READY_APPLICATION=pass" || echo "CUSTOMER_READY_APPLICATION=fail"
  [[ "$license_ok" == 1 ]] && echo "CUSTOMER_READY_LICENSE=pass" || echo "CUSTOMER_READY_LICENSE=fail"
  [[ "$first_user_ok" == 1 ]] && echo "CUSTOMER_READY_FIRST_USER=pass" || echo "CUSTOMER_READY_FIRST_USER=fail"
  probe_flag "CUSTOMER_READY_QMS_SCOPE" && echo "CUSTOMER_READY_QMS_SCOPE=pass" || echo "CUSTOMER_READY_QMS_SCOPE=fail"
  probe_flag "CUSTOMER_READY_QMS_ORGANIZATION" && echo "CUSTOMER_READY_QMS_ORGANIZATION=pass" || echo "CUSTOMER_READY_QMS_ORGANIZATION=fail"
  probe_flag "CUSTOMER_READY_QMS_SITES" && echo "CUSTOMER_READY_QMS_SITES=pass" || echo "CUSTOMER_READY_QMS_SITES=fail"
  probe_flag "CUSTOMER_READY_QMS_PROCESSES" && echo "CUSTOMER_READY_QMS_PROCESSES=pass" || echo "CUSTOMER_READY_QMS_PROCESSES=fail"
  if [[ "$ok" == 1 && "$qms_scope_ok" == 1 && "$release_ok" == 1 && "$runtime_ok" == 1 && "$application_ok" == 1 && "$license_ok" == 1 && "$first_user_ok" == 1 ]]; then echo "CUSTOMER_READY=YES"; else echo "CUSTOMER_READY=NO"; return 1; fi
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
