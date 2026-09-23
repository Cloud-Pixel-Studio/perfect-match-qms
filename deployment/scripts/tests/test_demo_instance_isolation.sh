#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/deployment/scripts/odoo-demo.sh"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/demo/compose.yml"
REAL_DOCKER="$(command -v docker || true)"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/secrets/odoo-demo" "$WORK/backups/odoo-demo"

# Sentinels model Demo1 paths. Demo2 configuration and chmod operations must
# leave these directories untouched.
chmod 711 "$WORK/secrets/odoo-demo" "$WORK/backups/odoo-demo"
cat > "$WORK/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$TEST_DOCKER_LOG"
DOCKER
chmod +x "$WORK/bin/docker"
export PATH="$WORK/bin:$PATH"
export TEST_DOCKER_LOG="$WORK/docker.log"

default_config="$("$LAUNCHER" show-config)"
grep -Fq 'demo_instance=demo' <<<"$default_config"
grep -Fq 'demo_database=pmqms_demo' <<<"$default_config"
grep -Fq 'compose_project=pmqms-demo' <<<"$default_config"
grep -Fq 'secrets_dir=/opt/perfect-match/secrets/odoo-demo' <<<"$default_config"
grep -Fq 'backup_dir=/opt/perfect-match/backups/odoo-demo' <<<"$default_config"
grep -Fq 'postgres_volume=pmqms_demo_postgres' <<<"$default_config"
grep -Fq 'odoo_volume=pmqms_demo_odoo_data' <<<"$default_config"
grep -Fq 'network=pmqms_demo_network' <<<"$default_config"

demo2_official="$(PMQMS_DEMO_INSTANCE=demo2 "$LAUNCHER" show-config)"
grep -Fxq 'demo_database=pmqms_demo2' <<<"$demo2_official"
grep -Fxq 'secrets_dir=/opt/perfect-match/secrets/odoo-demo-isolated' <<<"$demo2_official"
grep -Fxq 'backup_dir=/opt/perfect-match/backups/odoo-demo-isolated' <<<"$demo2_official"
grep -Fxq 'activation_dir=/opt/perfect-match/secrets/odoo-demo-isolated/activation' <<<"$demo2_official"
grep -Fxq 'license_file=/opt/perfect-match/secrets/odoo-demo-isolated/demo_license.pmql' <<<"$demo2_official"
! grep -Fxq 'demo_database=pmqms_demo' <<<"$demo2_official"
! grep -Fxq 'secrets_dir=/opt/perfect-match/secrets/odoo-demo' <<<"$demo2_official"
! grep -Fxq 'backup_dir=/opt/perfect-match/backups/odoo-demo' <<<"$demo2_official"

demo2_secrets="$WORK/secrets/odoo-demo-isolated"
demo2_backups="$WORK/backups/odoo-demo-isolated"
demo1_test_secrets="$WORK/runtime-demo/secrets"
demo1_test_backups="$WORK/runtime-demo/backups"
PMQMS_DEMO_INSTANCE=demo \
PMQMS_DEMO_SECRETS_DIR="$demo1_test_secrets" \
PMQMS_DEMO_BACKUP_DIR="$demo1_test_backups" \
"$LAUNCHER" config > "$WORK/demo-config-output"
demo2_config="$(PMQMS_DEMO_INSTANCE=demo2 \
  PMQMS_DEMO_SECRETS_DIR="$demo2_secrets" \
  PMQMS_DEMO_BACKUP_DIR="$demo2_backups" \
  "$LAUNCHER" show-config)"
grep -Fq 'demo_instance=demo2' <<<"$demo2_config"
grep -Fq 'demo_database=pmqms_demo2' <<<"$demo2_config"
grep -Fq 'compose_project=pmqms-demo2' <<<"$demo2_config"
grep -Fq 'postgres_volume=pmqms_demo2_postgres' <<<"$demo2_config"
grep -Fq 'odoo_volume=pmqms_demo2_odoo_data' <<<"$demo2_config"
grep -Fq 'network=pmqms_demo2_network' <<<"$demo2_config"
! grep -Fq '/opt/perfect-match/secrets/odoo-demo' <<<"$demo2_config"
! grep -Fq '/opt/perfect-match/backups/odoo-demo' <<<"$demo2_config"
! grep -Eq 'pmqms_demo([^a-zA-Z0-9_]|$)' <<<"$demo2_config"

PMQMS_DEMO_INSTANCE=demo2 \
PMQMS_DEMO_SECRETS_DIR="$demo2_secrets" \
PMQMS_DEMO_BACKUP_DIR="$demo2_backups" \
"$LAUNCHER" config > "$WORK/config-output"
grep -Fq "secrets_dir=$demo2_secrets" "$WORK/config-output"
grep -Fq "backup_dir=$demo2_backups" "$WORK/config-output"
grep -Fq -- '--project-name pmqms-demo ' "$TEST_DOCKER_LOG"
grep -Fq -- '--project-name pmqms-demo2' "$TEST_DOCKER_LOG"
! grep -Fq '/opt/perfect-match/secrets/odoo-demo' "$TEST_DOCKER_LOG"
! grep -Fq '/opt/perfect-match/backups/odoo-demo' "$TEST_DOCKER_LOG"
[[ "$(stat -c '%a' "$WORK/secrets/odoo-demo")" == 711 ]]
[[ "$(stat -c '%a' "$WORK/backups/odoo-demo")" == 711 ]]
[[ "$(stat -c '%a' "$demo2_secrets")" == 755 ]]
[[ "$(stat -c '%a' "$demo2_backups")" == 755 ]]
[[ ! -e "$WORK/secrets/odoo-demo/demo_license.pmql" ]]
[[ ! -e "$WORK/secrets/odoo-demo-isolated/demo_license.pmql" ]]
[[ -f "$demo2_secrets/runtime/runtime-lock.json" ]]
[[ "$(realpath "$demo2_secrets/runtime/runtime-lock.json")" != "$(realpath "$REPO_ROOT/deployment/runtime/runtime-lock.json")" ]]
cmp -s "$REPO_ROOT/deployment/runtime/runtime-lock.json" "$demo2_secrets/runtime/runtime-lock.json"

# Even caller-supplied relocated roots cannot be silently shared. The first
# instance claims both roots; a second instance must fail before chmod or
# creation of any nested instance files.
shared_secrets="$WORK/relocated/shared-secrets"
shared_backups="$WORK/relocated/shared-backups"
PMQMS_DEMO_INSTANCE=demo PMQMS_DEMO_SECRETS_DIR="$shared_secrets" PMQMS_DEMO_BACKUP_DIR="$shared_backups" \
  "$LAUNCHER" config > "$WORK/relocated-demo-config"
[[ "$(<"$shared_secrets/.pmqms-demo-instance-owner")" == demo ]]
[[ "$(<"$shared_backups/.pmqms-demo-instance-owner")" == demo ]]
: > "$shared_secrets/demo1-sentinel"
chmod 711 "$shared_secrets" "$shared_backups"
if PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_SECRETS_DIR="$shared_secrets" PMQMS_DEMO_BACKUP_DIR="$shared_backups" \
  "$LAUNCHER" config > "$WORK/shared-root-rejection" 2>&1; then
  echo "A relocated secrets/backup root was shared across instances." >&2
  exit 1
fi
[[ "$(stat -c '%a' "$shared_secrets")" == 711 ]]
[[ "$(stat -c '%a' "$shared_backups")" == 711 ]]
[[ -f "$shared_secrets/demo1-sentinel" ]]

expect_rejected() {
  local label="$1"; shift
  if "$@" >"$WORK/reject.out" 2>&1; then
    echo "Expected configuration rejection: $label" >&2
    exit 1
  fi
}
expect_rejected invalid-instance env PMQMS_DEMO_INSTANCE=../demo "$LAUNCHER" show-config
expect_rejected invalid-database env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_DB=pmqms_demo "$LAUNCHER" show-config
expect_rejected shared-demo-secrets env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_SECRETS_DIR=/opt/perfect-match/secrets/odoo-demo "$LAUNCHER" show-config
expect_rejected shared-demo-backups env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_BACKUP_DIR=/opt/perfect-match/backups/odoo-demo "$LAUNCHER" show-config
expect_rejected traversal-path env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_SECRETS_DIR="$WORK/../demo" "$LAUNCHER" show-config
expect_rejected shared-license env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_LICENSE_FILE=/opt/perfect-match/secrets/odoo-demo/demo_license.pmql "$LAUNCHER" show-config
expect_rejected shared-activation env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_ACTIVATION_DIR=/opt/perfect-match/secrets/odoo-demo/activation "$LAUNCHER" show-config
expect_rejected shared-project env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_COMPOSE_PROJECT=pmqms-demo "$LAUNCHER" show-config
expect_rejected shared-volume env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_ODOO_VOLUME=pmqms_demo_odoo_data "$LAUNCHER" show-config
expect_rejected external-runtime-lock env PMQMS_DEMO_INSTANCE=demo2 PMQMS_DEMO_RUNTIME_LOCK_FILE="$WORK/runtime-lock.json" "$LAUNCHER" show-config
expect_rejected demo-reuses-demo2-path env PMQMS_DEMO_INSTANCE=demo PMQMS_DEMO_SECRETS_DIR=/opt/perfect-match/secrets/odoo-demo-isolated "$LAUNCHER" show-config
expect_rejected invalid-instance-character env PMQMS_DEMO_INSTANCE='demo 2' "$LAUNCHER" show-config

# Compose's rendered resource names must stay distinct for simultaneous instances.
grep -Fq 'name: ${PMQMS_DEMO_POSTGRES_VOLUME:-pmqms_demo_postgres}' "$COMPOSE_FILE"
grep -Fq 'name: ${PMQMS_DEMO_ODOO_VOLUME:-pmqms_demo_odoo_data}' "$COMPOSE_FILE"
grep -Fq 'name: ${PMQMS_DEMO_NETWORK:-pmqms_demo_network}' "$COMPOSE_FILE"
! grep -Fq 'container_name:' "$COMPOSE_FILE"

if [[ -n "$REAL_DOCKER" ]]; then
  for instance in demo demo2; do
    suffix="${instance//-/_}"
    secret_root="$WORK/compose/$instance/secrets"
    mkdir -p "$secret_root/config"
    : > "$secret_root/odoo_pg_password"
    : > "$secret_root/config/odoo.conf"
    : > "$secret_root/config/environment_id"
    if [[ "$instance" == demo ]]; then
      db=pmqms_demo project=pmqms-demo pgvol=pmqms_demo_postgres odoo_vol=pmqms_demo_odoo_data net=pmqms_demo_network http=8170 poll=8173
    else
      db=pmqms_demo2 project=pmqms-demo2 pgvol=pmqms_demo2_postgres odoo_vol=pmqms_demo2_odoo_data net=pmqms_demo2_network http=8171 poll=8174
    fi
    export COMPOSE_PROJECT_NAME="$project"
    export PMQMS_DEMO_POSTGRES_VOLUME="$pgvol" PMQMS_DEMO_ODOO_VOLUME="$odoo_vol" PMQMS_DEMO_NETWORK="$net"
    export ODOO_DEMO_CONFIG_DIR="$secret_root/config" ODOO_DEMO_PG_PASSWORD_FILE="$secret_root/odoo_pg_password"
    export ODOO_DEMO_HTTP_PORT="$http" ODOO_DEMO_LONGPOLLING_PORT="$poll"
    export PMQMS_POSTGRES_IMAGE="$(jq -er '.postgres.image' "$REPO_ROOT/deployment/runtime/runtime-lock.json")"
    export PMQMS_ODOO_IMAGE="$(jq -er '.odoo.image' "$REPO_ROOT/deployment/runtime/runtime-lock.json")"
    compose_json="$("$REAL_DOCKER" compose --project-name "$project" -f "$COMPOSE_FILE" config --format json)"
    grep -Fq "\"name\": \"$pgvol\"" <<<"$compose_json"
    grep -Fq "\"name\": \"$odoo_vol\"" <<<"$compose_json"
    grep -Fq "\"name\": \"$net\"" <<<"$compose_json"
    ! grep -Fq 'container_name' <<<"$compose_json"
    [[ "$db" == "pmqms_${suffix}" ]]
  done
fi

echo 'DEMO_INSTANCE_ISOLATION=PASS'
