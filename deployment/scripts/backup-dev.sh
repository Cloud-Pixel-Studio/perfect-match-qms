#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker/dev/compose.yml"
SECRETS_DIR="${PMQMS_ODOO_DEV_SECRETS_DIR:-/opt/perfect-match/secrets/odoo-dev}"
BACKUP_ROOT="${PMQMS_DEV_BACKUP_DIR:-/opt/perfect-match/backups/odoo-dev}"
DB_NAME="${PMQMS_DEV_DB:-pmqms_dev}"
ODOO_VOLUME="${PMQMS_DEV_ODOO_VOLUME:-pmqms_dev_odoo_data}"

export ODOO_DEV_CONFIG_DIR="$SECRETS_DIR/config"
export ODOO_DEV_PG_PASSWORD_FILE="$SECRETS_DIR/odoo_pg_password"

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

usage() {
  cat <<'EOF'
Usage:
  ./deployment/scripts/backup-dev.sh [backup]
  ./deployment/scripts/backup-dev.sh validate <backup.tar.gz>

Creates a DEV backup outside Git under /opt/perfect-match/backups/odoo-dev by default.
The archive contains the PostgreSQL dump, Odoo filestore, DEV config, and a manifest.
EOF
}

validate_archive() {
  local archive="$1"
  [[ -f "$archive" ]] || { echo "Backup archive not found: $archive" >&2; exit 2; }
  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN
  tar -xzf "$archive" -C "$tmp"
  [[ -f "$tmp/db.dump" ]] || { echo "Backup missing db.dump" >&2; exit 1; }
  [[ -f "$tmp/filestore.tar.gz" ]] || { echo "Backup missing filestore.tar.gz" >&2; exit 1; }
  compose up -d postgres-dev >/dev/null
  compose exec -T postgres-dev pg_restore --list < "$tmp/db.dump" >/dev/null
  tar -tzf "$tmp/filestore.tar.gz" >/dev/null
  echo "Backup archive validated: $archive"
}

create_backup() {
  mkdir -p "$BACKUP_ROOT"
  chmod 700 "$BACKUP_ROOT"
  local timestamp archive tmp
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  archive="$BACKUP_ROOT/pmqms-dev-$timestamp.tar.gz"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN

  compose up -d postgres-dev >/dev/null
  compose exec -T postgres-dev pg_dump -U odoo -d "$DB_NAME" -Fc > "$tmp/db.dump"

  docker run --rm \
    -v "$ODOO_VOLUME:/odoo-data:ro" \
    -v "$tmp:/backup" \
    alpine:3.20 \
    sh -c "cd /odoo-data && if [ -d filestore/$DB_NAME ]; then tar -czf /backup/filestore.tar.gz filestore/$DB_NAME; else tar -czf /backup/filestore.tar.gz --files-from /dev/null; fi"

  mkdir -p "$tmp/config"
  if [[ -d "$SECRETS_DIR" ]]; then
    docker run --rm \
      -v "$SECRETS_DIR:/secrets:ro" \
      -v "$tmp/config:/backup-config" \
      -e BACKUP_UID="$(id -u)" \
      -e BACKUP_GID="$(id -g)" \
      alpine:3.20 \
      sh -c "cp -a /secrets/config/. /backup-config/ 2>/dev/null || true; cp /secrets/odoo_pg_password /backup-config/odoo_pg_password 2>/dev/null || true; chown -R \"\$BACKUP_UID:\$BACKUP_GID\" /backup-config; chmod -R u+rwX,go-rwx /backup-config"
  fi

  {
    echo "backup_created_utc=$timestamp"
    echo "database=$DB_NAME"
    echo "odoo_volume=$ODOO_VOLUME"
    echo "repo_branch=$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    echo "repo_commit=$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "compose_file=deployment/docker/dev/compose.yml"
  } > "$tmp/manifest.txt"

  tar -C "$tmp" -czf "$archive" .
  sha256sum "$archive" > "$archive.sha256"
  validate_archive "$archive"
  echo "$archive"
}

case "${1:-backup}" in
  backup)
    create_backup
    ;;
  validate)
    validate_archive "${2:-}"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $1" >&2
    usage >&2
    exit 2
    ;;
esac
