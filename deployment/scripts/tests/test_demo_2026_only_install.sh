#!/usr/bin/env bash
set -euo pipefail

[[ "${GITHUB_ACTIONS:-}" == true ]] || {
  echo "This disposable database install test may run only on an isolated GitHub Actions runner." >&2
  exit 2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LAUNCHER="$REPO_ROOT/deployment/scripts/odoo-demo.sh"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/demo/compose.yml"
PROJECT="pmqms-demo2"
POSTGRES_VOLUME="pmqms_demo2_postgres"
ODOO_VOLUME="pmqms_demo2_odoo_data"
NETWORK="pmqms_demo2_network"
WORK="$(mktemp -d)"
BACKUP_WORK="$(mktemp -d /dev/shm/pmqms-demo2-backups.XXXXXX)"
CREATED=0

compose_test() {
  COMPOSE_PROJECT_NAME="$PROJECT" \
  ODOO_DEMO_CONFIG_DIR="$WORK/secrets/config" \
  ODOO_DEMO_PG_PASSWORD_FILE="$WORK/secrets/odoo_pg_password" \
  PMQMS_DEMO_RUNTIME_LOCK_FILE="$WORK/secrets/runtime/runtime-lock.json" \
  PMQMS_DEMO_SECRETS_DIR="$WORK/secrets" \
  PMQMS_DEMO_BACKUP_DIR="$WORK/backups" \
    docker compose --project-name "$PROJECT" -f "$COMPOSE_FILE" "$@"
}

cleanup() {
  if [[ "$CREATED" == 1 ]]; then
    compose_test down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
  rm -rf -- "$WORK"
  rm -rf -- "$BACKUP_WORK"
}
trap cleanup EXIT

for name in "$POSTGRES_VOLUME" "$ODOO_VOLUME"; do
  if docker volume inspect "$name" >/dev/null 2>&1; then
    echo "Refusing disposable install test: pre-existing target volume $name." >&2
    exit 1
  fi
done
if docker ps -aq --filter "label=com.docker.compose.project=$PROJECT" | grep -q .; then
  echo "Refusing disposable install test: pre-existing $PROJECT containers." >&2
  exit 1
fi
if docker network inspect "$NETWORK" >/dev/null 2>&1; then
  echo "Refusing disposable install test: pre-existing target network $NETWORK." >&2
  exit 1
fi

mkdir -p "$WORK/secrets/runtime" "$WORK/secrets/config" "$WORK/backups"
cp "$REPO_ROOT/deployment/runtime/runtime-lock.json" "$WORK/secrets/runtime/runtime-lock.json"
printf 'demo2\n' > "$WORK/secrets/.pmqms-demo-instance-owner"
printf 'demo2\n' > "$WORK/backups/.pmqms-demo-instance-owner"
chmod 600 "$WORK/secrets/.pmqms-demo-instance-owner" "$WORK/backups/.pmqms-demo-instance-owner"

export PMQMS_DEMO_INSTANCE=demo2
export PMQMS_DEMO_BACKUP_DIAGNOSTICS=1
export PMQMS_DEMO_SECRETS_DIR="$WORK/secrets"
export PMQMS_DEMO_BACKUP_DIR="$BACKUP_WORK"
export PMQMS_DEMO_RUNTIME_LOCK_FILE="$WORK/secrets/runtime/runtime-lock.json"
export ODOO_DEMO_HTTP_BIND=127.0.0.1
export ODOO_DEMO_LONGPOLLING_BIND=127.0.0.1

for image in \
  "$(jq -er '.odoo.image' "$PMQMS_DEMO_RUNTIME_LOCK_FILE")" \
  "$(jq -er '.postgres.image' "$PMQMS_DEMO_RUNTIME_LOCK_FILE")" \
  "$(jq -er '.alpine.image' "$PMQMS_DEMO_RUNTIME_LOCK_FILE")"; do
  docker pull "$image"
done

CREATED=1
"$LAUNCHER" install-demo2-2026-only &> "$WORK/install.log" || {
  cat "$WORK/install.log" >&2
  exit 1
}
grep -Fq 'demo2_2026_only_install=PASS' "$WORK/install.log"
backup_line="$(grep -F 'demo2_initial_backup=' "$WORK/install.log")"
backup_path="$(printf '%s\n' "$backup_line" | awk '{print $1}' | cut -d= -f2-)"
backup_recorded_sha="$(printf '%s\n' "$backup_line" | awk '{for (i = 1; i <= NF; i++) if ($i ~ /^sha256=/) {sub(/^sha256=/, "", $i); print $i}}')"
[[ "$backup_path" == "$BACKUP_WORK/"* && -f "$backup_path" ]]
[[ "$(stat -c '%a' "$backup_path")" == 600 ]]
[[ "$(sha256sum "$backup_path" | awk '{print $1}')" == "$backup_recorded_sha" ]]

packs="$(compose_test exec -T postgres-demo psql -U odoo -d pmqms_demo2 -Atqc \
  "SELECT count(*) || '|' || string_agg(code || '|' || version || '|' || state, ',' ORDER BY code) FROM pm_qms_framework_pack")"
profiles="$(compose_test exec -T postgres-demo psql -U odoo -d pmqms_demo2 -Atqc \
  "SELECT count(*) || '|' || string_agg(code || '|' || edition || '|' || state, ',' ORDER BY code) FROM pm_qms_mapping_profile")"
scenarios="$(compose_test exec -T postgres-demo psql -U odoo -d pmqms_demo2 -Atqc \
  "SELECT count(*) FROM pm_qms_iso9001_transition_scenario")"
non_draft_mappings="$(compose_test exec -T postgres-demo psql -U odoo -d pmqms_demo2 -Atqc \
  "SELECT count(*) FROM pm_qms_external_mapping WHERE review_status <> 'draft'")"

[[ "$packs" == '1|PM-QMS-ISO9001-2026|1.0|draft' ]]
[[ "$profiles" == '1|PM-QMS-QUALITY-ISO9001-2026-IMPLEMENTATION|2026|draft' ]]
[[ "$scenarios" == 0 && "$non_draft_mappings" == 0 ]]
! compose_test exec -T postgres-demo psql -U odoo -d pmqms_demo2 -Atqc \
  "SELECT 1 FROM pm_qms_framework_pack WHERE code IN ('PM-QMS-QUALITY', 'PM-QMS-ISO9001-INITIAL') LIMIT 1" | grep -q 1
! compose_test exec -T postgres-demo psql -U odoo -d pmqms_demo2 -Atqc \
  "SELECT 1 FROM pm_qms_mapping_profile WHERE edition = '2015' LIMIT 1" | grep -q 1

echo 'Clean Demo2 2026-only Odoo installation and pack-selection integration: PASS'
