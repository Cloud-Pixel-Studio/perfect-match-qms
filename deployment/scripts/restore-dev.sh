#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/dev/compose.yml"
SECRETS_DIR="${PMQMS_ODOO_DEV_SECRETS_DIR:-/opt/perfect-match/secrets/odoo-dev}"
ODOO_VOLUME="${PMQMS_DEV_ODOO_VOLUME:-pmqms_dev_odoo_data}"

export ODOO_DEV_CONFIG_DIR="$SECRETS_DIR/config"
export ODOO_DEV_PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"

backup=""
target_db=""
confirm_db=""
replace_existing=0
drop_after_restore=0

usage() {
  cat <<'EOF'
Usage:
  ./deployment/scripts/restore-dev.sh --backup <backup.tar.gz> --target-db <db> --confirm-target-db <db> [--replace-existing] [--drop-after-restore]

Safety:
  - target-db must be explicit and match confirm-target-db.
  - existing databases are not overwritten unless --replace-existing is provided.
  - restoring over pmqms_dev is refused unless PMQMS_ALLOW_ACTIVE_DEV_RESTORE=I_UNDERSTAND.
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
if [[ "$target_db" == "pmqms_dev" && "${PMQMS_ALLOW_ACTIVE_DEV_RESTORE:-}" != "I_UNDERSTAND" ]]; then
  echo "Refusing to restore over active pmqms_dev without PMQMS_ALLOW_ACTIVE_DEV_RESTORE=I_UNDERSTAND." >&2
  exit 2
fi

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
tar -xzf "$backup" -C "$tmp"
[[ -f "$tmp/db.dump" ]] || { echo "Backup missing db.dump" >&2; exit 1; }
[[ -f "$tmp/filestore.tar.gz" ]] || { echo "Backup missing filestore.tar.gz" >&2; exit 1; }

compose up -d postgres-dev >/dev/null
exists="$(compose exec -T postgres-dev psql -U odoo -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$target_db'")"
if [[ "$exists" == "1" ]]; then
  if [[ "$replace_existing" != "1" ]]; then
    echo "Target database already exists. Use --replace-existing with explicit confirmation to replace it." >&2
    exit 2
  fi
  compose exec -T postgres-dev dropdb -U odoo "$target_db"
fi

compose exec -T postgres-dev createdb -U odoo "$target_db"
compose exec -T postgres-dev pg_restore -U odoo -d "$target_db" --no-owner --role=odoo < "$tmp/db.dump"

docker run --rm \
  -v "$ODOO_VOLUME:/odoo-data" \
  -v "$tmp:/backup:ro" \
  alpine:3.20 \
  sh -c "set -e; rm -rf /tmp/filestore; mkdir -p /tmp/filestore; tar -xzf /backup/filestore.tar.gz -C /tmp/filestore; mkdir -p /odoo-data/filestore/$target_db; src=\$(find /tmp/filestore/filestore -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n 1 || true); if [ -n \"\$src\" ]; then cp -a \"\$src/.\" /odoo-data/filestore/$target_db/; fi"

echo "Restore completed into database: $target_db"

if [[ "$drop_after_restore" == "1" ]]; then
  compose exec -T postgres-dev dropdb -U odoo "$target_db"
  docker run --rm -v "$ODOO_VOLUME:/odoo-data" alpine:3.20 sh -c "rm -rf /odoo-data/filestore/$target_db"
  echo "Disposable restore target removed: $target_db"
fi
