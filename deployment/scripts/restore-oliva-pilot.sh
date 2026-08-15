#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/pilot/compose.yml"
SECRETS_DIR="${PMQMS_OLIVA_PILOT_SECRETS_DIR:-/opt/perfect-match/secrets/odoo-oliva-pilot}"
ODOO_VOLUME="${PMQMS_OLIVA_PILOT_ODOO_VOLUME:-pmqms_oliva_pilot_odoo_data}"
ACTIVE_DB="${PMQMS_OLIVA_PILOT_DB:-pmqms_oliva_pilot}"

export ODOO_OLIVA_PILOT_CONFIG_DIR="$SECRETS_DIR/config"
export ODOO_OLIVA_PILOT_PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"

backup=""
target_db=""
confirm_db=""
replace_existing=0
drop_after_restore=0

usage() {
  cat <<'EOF'
Usage:
  ./deployment/scripts/restore-oliva-pilot.sh --backup <backup.tar.gz> --target-db <db> --confirm-target-db <db> [--replace-existing] [--drop-after-restore]

Safety:
  - target-db must be explicit and match confirm-target-db.
  - existing databases are not overwritten unless --replace-existing is provided.
  - restoring over the active Oliva pilot database is refused unless PMQMS_ALLOW_ACTIVE_OLIVA_RESTORE=I_UNDERSTAND.
  - use --drop-after-restore for disposable validation restores.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup)
      backup="${2:-}"; shift 2 ;;
    --target-db)
      target_db="${2:-}"; shift 2 ;;
    --confirm-target-db)
      confirm_db="${2:-}"; shift 2 ;;
    --replace-existing)
      replace_existing=1; shift ;;
    --drop-after-restore)
      drop_after_restore=1; shift ;;
    help|-h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -f "$backup" ]] || { echo "Backup archive not found." >&2; exit 2; }
[[ -n "$target_db" ]] || { echo "--target-db is required." >&2; exit 2; }
[[ "$target_db" == "$confirm_db" ]] || { echo "--confirm-target-db must match --target-db." >&2; exit 2; }
[[ "$target_db" =~ ^[A-Za-z0-9_]+$ ]] || { echo "Target DB may contain only letters, numbers, and underscores." >&2; exit 2; }
if [[ "$target_db" == "$ACTIVE_DB" && "${PMQMS_ALLOW_ACTIVE_OLIVA_RESTORE:-}" != "I_UNDERSTAND" ]]; then
  echo "Refusing to restore over active $ACTIVE_DB without PMQMS_ALLOW_ACTIVE_OLIVA_RESTORE=I_UNDERSTAND." >&2
  exit 2
fi

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

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
tar -xzf "$backup" -C "$tmp"
[[ -f "$tmp/db.dump" ]] || { echo "Backup missing db.dump" >&2; exit 1; }
[[ -f "$tmp/filestore.tar.gz" ]] || { echo "Backup missing filestore.tar.gz" >&2; exit 1; }

compose up -d postgres-oliva-pilot >/dev/null
wait_postgres
exists="$(compose exec -T postgres-oliva-pilot psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$target_db'")"
if [[ "$exists" == "1" ]]; then
  if [[ "$replace_existing" != "1" ]]; then
    echo "Target database already exists. Use --replace-existing with explicit confirmation to replace it." >&2
    exit 2
  fi
  compose exec -T postgres-oliva-pilot dropdb -U odoo "$target_db"
fi

compose exec -T postgres-oliva-pilot createdb -U odoo "$target_db"
compose exec -T postgres-oliva-pilot pg_restore -U odoo -d "$target_db" --no-owner --role=odoo < "$tmp/db.dump"

docker run --rm \
  -v "$ODOO_VOLUME:/odoo-data" \
  -v "$tmp:/backup:ro" \
  alpine:3.20 \
  sh -c "set -e; rm -rf /tmp/filestore; mkdir -p /tmp/filestore; tar -xzf /backup/filestore.tar.gz -C /tmp/filestore; mkdir -p /odoo-data/filestore/$target_db; src=\$(find /tmp/filestore/filestore -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n 1 || true); if [ -n \"\$src\" ]; then cp -a \"\$src/.\" /odoo-data/filestore/$target_db/; fi"

echo "Oliva pilot restore completed into database: $target_db"

if [[ "$drop_after_restore" == "1" ]]; then
  compose exec -T postgres-oliva-pilot dropdb -U odoo "$target_db"
  docker run --rm -v "$ODOO_VOLUME:/odoo-data" alpine:3.20 sh -c "rm -rf /odoo-data/filestore/$target_db"
  echo "Disposable Oliva restore target removed: $target_db"
fi
