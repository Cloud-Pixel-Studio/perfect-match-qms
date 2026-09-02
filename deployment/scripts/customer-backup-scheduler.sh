#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCHEDULER="$SCRIPT_DIR/../../tools/backup/m29_scheduler.py"
PYTHON="${PMQMS_PYTHON:-python3}"
UNIT_DIR="${PMQMS_SYSTEMD_UNIT_DIR:-/etc/systemd/system}"
SYSTEMCTL="${PMQMS_SYSTEMCTL_BIN:-systemctl}"

die() { echo "ERROR: $*" >&2; exit 2; }
slug_ok() { [[ "${1:-}" =~ ^[a-z0-9]+([a-z0-9-]*[a-z0-9])?$ ]]; }

usage() {
  cat <<'EOF'
Usage: customer-backup-scheduler.sh <run|health|status|validate-config> --config file [--tier tier]
       customer-backup-scheduler.sh install <slug> --config file
       customer-backup-scheduler.sh remove <slug>

Install/remove manage the shared systemd templates and per-instance timer
enablement. Configuration and recovery data remain outside Git.
EOF
}

install_units() {
  local slug="${1:-}" config="" arg
  slug_ok "$slug" || die "invalid instance slug"
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --config) config="${2:-}"; shift 2;;
      *) die "unknown install option: $1";;
    esac
  done
  [[ -n "$config" && -f "$config" ]] || die "scheduler config is required"
  "$PYTHON" "$SCHEDULER" validate-config --config "$config" >/dev/null
  install -d -m 0755 "$UNIT_DIR"
  for arg in \
    pmqms-customer-backup@.service \
    pmqms-customer-backup@.timer \
    pmqms-customer-backup-daily@.service \
    pmqms-customer-backup-daily@.timer \
    pmqms-customer-backup-monthly@.service \
    pmqms-customer-backup-monthly@.timer \
    pmqms-customer-backup-failure@.service; do
    install -m 0644 "$SCRIPT_DIR/../systemd/$arg" "$UNIT_DIR/$arg"
  done
  "$SYSTEMCTL" daemon-reload
  "$SYSTEMCTL" enable "pmqms-customer-backup@$slug.timer"
  "$SYSTEMCTL" enable "pmqms-customer-backup-daily@$slug.timer"
  "$SYSTEMCTL" enable "pmqms-customer-backup-monthly@$slug.timer"
  echo "scheduler_units=installed"
}

remove_units() {
  local slug="${1:-}"
  slug_ok "$slug" || die "invalid instance slug"
  "$SYSTEMCTL" disable --now "pmqms-customer-backup@$slug.timer" "pmqms-customer-backup-daily@$slug.timer" "pmqms-customer-backup-monthly@$slug.timer" >/dev/null 2>&1 || true
  "$SYSTEMCTL" daemon-reload
  echo "scheduler_units=removed"
}

command="${1:-}"
shift || true
case "$command" in
  run|health|status|validate-config)
    exec "$PYTHON" "$SCHEDULER" "$command" "$@";;
  install) install_units "$@";;
  remove) remove_units "$@";;
  help|-h|--help) usage;;
  *) usage; exit 2;;
esac
