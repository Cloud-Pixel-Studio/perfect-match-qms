#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
UNIT_DIR="$WORK/systemd"
SYSTEMCTL_LOG="$WORK/systemctl.log"
mkdir -p "$UNIT_DIR"
cat > "$WORK/systemctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$SYSTEMCTL_LOG"
EOF
chmod 700 "$WORK/systemctl"
export SYSTEMCTL_LOG
export PMQMS_SYSTEMD_UNIT_DIR="$UNIT_DIR"
export PMQMS_SYSTEMCTL_BIN="$WORK/systemctl"
printf 'age1fictionalrecipient\n' > "$WORK/recipient.age"
cat > "$WORK/config.json" <<EOF
{"instance_slug":"fictional-customer","instance_root":"$WORK/instance","recipient_file":"$WORK/recipient.age","local_staging_repository":"$WORK/local","off_host_destination":"$WORK/off-host","status_path":"$WORK/status.json","monitoring_status_destination":"$WORK/monitoring.json","timeout_seconds":1800,"backup_cadence_minutes":240,"max_jitter_seconds":1800,"retention":{"intraday_days":7,"daily_days":30,"monthly_months":12}}
EOF
bash "$ROOT/customer-backup-scheduler.sh" install fictional-customer --config "$WORK/config.json" >/dev/null
bash "$ROOT/customer-backup-scheduler.sh" install fictional-customer --config "$WORK/config.json" >/dev/null
test "$(find "$UNIT_DIR" -type f | wc -l)" -eq 7
grep -F 'enable pmqms-customer-backup@fictional-customer.timer' "$SYSTEMCTL_LOG" >/dev/null
if command -v systemd-analyze >/dev/null 2>&1; then
  systemd-analyze verify "$ROOT/../systemd"/*.service "$ROOT/../systemd"/*.timer
fi
for unit in \
  pmqms-customer-backup@.service \
  pmqms-customer-backup-daily@.service \
  pmqms-customer-backup-monthly@.service; do
  grep -F 'Restart=on-failure' "$ROOT/../systemd/$unit" >/dev/null
  grep -F 'RestartSec=30s' "$ROOT/../systemd/$unit" >/dev/null
  grep -F 'StartLimitBurst=3' "$ROOT/../systemd/$unit" >/dev/null
done
bash "$ROOT/customer-backup-scheduler.sh" remove fictional-customer >/dev/null
bash "$ROOT/customer-backup-scheduler.sh" remove fictional-customer >/dev/null
grep -F 'disable --now pmqms-customer-backup@fictional-customer.timer pmqms-customer-backup-daily@fictional-customer.timer pmqms-customer-backup-monthly@fictional-customer.timer' "$SYSTEMCTL_LOG" >/dev/null
echo 'customer-backup-scheduler units: PASS'
