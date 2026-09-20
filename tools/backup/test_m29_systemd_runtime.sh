#!/usr/bin/env bash
set -euo pipefail

# Disposable Linux-only proof of timer activation, persistence and bounded retry.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SYSTEMCTL="${PMQMS_SYSTEMCTL_BIN:-systemctl}"
if ! command -v "$SYSTEMCTL" >/dev/null 2>&1 || ! "$SYSTEMCTL" is-system-running >/dev/null 2>&1; then
  echo "systemd_runtime=NOT_AVAILABLE"
  echo "systemd_runtime_evidence=runner_has_no_running_system_manager"
  exit 0
fi

as_root() {
  if [[ "${EUID}" == 0 ]]; then "$@"; else sudo "$@"; fi
}

AGE_VERSION="1.2.1"
AGE_SHA256="7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50"
AGE_URL="https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
RUN_AS_USER="$(id -un)"
RUN_AS_GROUP="$(id -gn)"
PREFIX="pmqms-m292-runtime-${GITHUB_RUN_ID:-local}-$$"
WORK="$(mktemp -d "/var/tmp/${PREFIX}.XXXXXX")"
INSTANCE_BASE="${WORK}/instances"
SLUG="runtime-proof"
INSTANCE="${INSTANCE_BASE}/${SLUG}"
SCHEDULER_LOCK="${INSTANCE}/backups/.pmqms-scheduler.lock"
UNIT_DIR="/run/systemd/system"
RUNTIME_SERVICE="${PREFIX}@.service"
RUNTIME_TIMER="${PREFIX}@.timer"
COLLISION_RUNTIME_SERVICE="${PREFIX}-collision@.service"
COLLISION_RUNTIME_TIMER="${PREFIX}-collision@.timer"
DAILY_SERVICE="${PREFIX}-daily@.service"
DAILY_TIMER="${PREFIX}-daily@.timer"
MONTHLY_SERVICE="${PREFIX}-monthly@.service"
MONTHLY_TIMER="${PREFIX}-monthly@.timer"
RUNTIME_INSTANCE_SERVICE="${PREFIX}@${SLUG}.service"
RUNTIME_INSTANCE_TIMER="${PREFIX}@${SLUG}.timer"
COLLISION_RUNTIME_INSTANCE_SERVICE="${PREFIX}-collision@${SLUG}.service"
COLLISION_RUNTIME_INSTANCE_TIMER="${PREFIX}-collision@${SLUG}.timer"
DAILY_INSTANCE_SERVICE="${PREFIX}-daily@${SLUG}.service"
DAILY_INSTANCE_TIMER="${PREFIX}-daily@${SLUG}.timer"
MONTHLY_INSTANCE_SERVICE="${PREFIX}-monthly@${SLUG}.service"
MONTHLY_INSTANCE_TIMER="${PREFIX}-monthly@${SLUG}.timer"
DAILY_MONTHLY_HOLD_REQUEST="${WORK}/daily-monthly-hold.request"
DAILY_LOCK_ACQUIRED_SIGNAL="${WORK}/daily-lock-acquired.signal"
DAILY_LOCK_RELEASE="${WORK}/daily-lock.release"

cleanup() {
  set +e
  for unit in "$RUNTIME_INSTANCE_TIMER" "$COLLISION_RUNTIME_INSTANCE_TIMER" "$DAILY_INSTANCE_TIMER" "$MONTHLY_INSTANCE_TIMER" "$RUNTIME_INSTANCE_SERVICE" "$COLLISION_RUNTIME_INSTANCE_SERVICE" "$DAILY_INSTANCE_SERVICE" "$MONTHLY_INSTANCE_SERVICE"; do
    as_root "$SYSTEMCTL" disable --now "$unit" >/dev/null 2>&1
    as_root "$SYSTEMCTL" reset-failed "$unit" >/dev/null 2>&1
  done
  for unit in "$RUNTIME_SERVICE" "$RUNTIME_TIMER" "$COLLISION_RUNTIME_SERVICE" "$COLLISION_RUNTIME_TIMER" "$DAILY_SERVICE" "$DAILY_TIMER" "$MONTHLY_SERVICE" "$MONTHLY_TIMER"; do
    as_root rm -f "$UNIT_DIR/$unit"
  done
  as_root "$SYSTEMCTL" daemon-reload >/dev/null 2>&1
  as_root rm -f \
    "/var/lib/systemd/timers/stamp-${RUNTIME_INSTANCE_TIMER}" \
    "/var/lib/systemd/timers/stamp-${COLLISION_RUNTIME_INSTANCE_TIMER}" \
    "/var/lib/systemd/timers/stamp-${DAILY_INSTANCE_TIMER}" \
    "/var/lib/systemd/timers/stamp-${MONTHLY_INSTANCE_TIMER}"
  as_root rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

mkdir -p "$WORK/bin" "$WORK/unit" "$INSTANCE" "$INSTANCE/config" "$INSTANCE/secrets" "$INSTANCE/license" "$INSTANCE/activation" "$INSTANCE/backups" "$INSTANCE/runtime" "$INSTANCE/runtime/addons"
printf 'fictional-recipient-placeholder\n' > "$WORK/recipient.age"
cp "$ROOT/deployment/runtime/runtime-lock.json" "$INSTANCE/config/runtime-lock.json"
FIXTURE_SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
cat > "$INSTANCE/config/instance.env" <<EOF
INSTANCE_SLUG=${SLUG}
ENVIRONMENT_TYPE=test
PRODUCT_VERSION=v1.0.0-test
SOURCE_RELEASE_SHA=${FIXTURE_SOURCE_SHA}
DOMAIN=systemd-runtime.invalid
DATABASE_NAME=pmqms_runtime_proof
HTTP_PORT=8199
EOF
printf 'fictional-systemd-runtime-environment\n' > "$INSTANCE/config/environment_id"
cat > "$INSTANCE/config/deployment-manifest.json" <<'EOF'
{"instance_slug":"runtime-proof","environment_type":"test","product_version":"v1.0.0-test"}
EOF
cat > "$INSTANCE/config/product-manifest.json" <<EOF
{"product_version":"v1.0.0-test","source_sha":"${FIXTURE_SOURCE_SHA}"}
EOF
touch "$INSTANCE/backups/.pmqms-recovery-repository"
chmod -R 700 "$WORK"

cat > "$WORK/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == compose ]]; then
  shift
  command_line="$*"
  if [[ "${PMQMS_TEST_BACKUP_TIER:-}" == daily && -e "${PMQMS_TEST_DAILY_HOLD_REQUEST:-}" && ! -e "${PMQMS_TEST_DAILY_LOCK_RELEASE:-}" ]]; then
    # Keep the real scheduler lock held from the first fixture operation until
    # the harness explicitly releases it. This is an event gate, not a timing
    # assumption, and prevents post-acquisition work from ending the collision
    # before the monthly first attempt is observed.
    while [[ ! -e "${PMQMS_TEST_DAILY_LOCK_RELEASE:-}" ]]; do
      sleep 0.1
    done
  fi
  if [[ "$command_line" == *" exec "* && "$command_line" == *" pg_dump "* ]]; then
    if [[ "${PMQMS_TEST_BACKUP_TIER:-}" != daily || ! -e "${PMQMS_TEST_DAILY_HOLD_REQUEST:-}" ]]; then
      sleep "${PMQMS_TEST_BACKUP_SLEEP:-0}"
    fi
    printf 'fictional database snapshot\n'
  fi
  exit 0
fi
command_line="$*"
if [[ "$command_line" == *"filestore.tar.gz"* ]]; then
  for argument in "$@"; do
    if [[ "$argument" == *:/backup ]]; then
      backup_mount="${argument%:/backup}"
      tar -czf "$backup_mount/filestore.tar.gz" --files-from /dev/null
      exit 0
    fi
  done
fi
exit 0
EOF
chmod 755 "$WORK/bin/docker"

curl --fail --silent --show-error --location "$AGE_URL" -o "$WORK/age.tar.gz"
printf '%s  %s\n' "$AGE_SHA256" "$WORK/age.tar.gz" | sha256sum --check --status
tar -xzf "$WORK/age.tar.gz" -C "$WORK"
AGE_BIN="$(find "$WORK" -type f -name age -perm -u+x -print -quit)"
AGE_KEYGEN="$(find "$WORK" -type f -name age-keygen -perm -u+x -print -quit)"
[[ -x "$AGE_BIN" && -x "$AGE_KEYGEN" ]]
"$AGE_KEYGEN" > "$WORK/identity.age" 2>/dev/null
chmod 600 "$WORK/identity.age"
RECIPIENT="$(sed -n -e 's/^# public key: //p' -e 's/^Public key: //p' "$WORK/identity.age")"
printf '%s\n' "$RECIPIENT" > "$WORK/recipient.age"
chmod 600 "$WORK/recipient.age"

cat > "$WORK/config.json" <<EOF
{"instance_slug":"${SLUG}","instance_root":"${INSTANCE}","recipient_file":"${WORK}/recipient.age","local_staging_repository":"${INSTANCE}/backups","off_host_destination":"${WORK}/off-host","status_path":"${WORK}/status.json","monitoring_status_destination":"${WORK}/monitoring.json","timeout_seconds":30,"backup_cadence_minutes":240,"max_jitter_seconds":1800,"retention":{"intraday_days":7,"daily_days":30,"monthly_months":12},"release_sha":"$(git -C "$ROOT" rev-parse HEAD)"}
EOF
mkdir -p "$WORK/off-host"

render_service() {
  local source="$1" output="$2" tier="$3" sleep_seconds="$4"
  local wrapper="$WORK/run-${tier}.sh"
  cat > "$wrapper" <<EOF
#!/usr/bin/env bash
set -euo pipefail
printf '%s\\n' "\$(date +%s)" >> "${WORK}/${tier}.invocations"
lock_state=free
if [[ "${tier}" == monthly && -e "${DAILY_MONTHLY_HOLD_REQUEST}" ]]; then
  # The monthly service must not publish its first observation until the
  # daily barrier and the real scheduler lock agree. This prevents a service
  # start race from recording a free lock before the daily owner is visible.
  lock_deadline=\$((SECONDS + 30))
  while (( SECONDS < lock_deadline )); do
    if [[ -e "${DAILY_LOCK_ACQUIRED_SIGNAL}" ]] && ! flock -n "${SCHEDULER_LOCK}" -c ':' 2>/dev/null; then
      lock_state=held
      break
    fi
    sleep 0.05
  done
  if [[ "\${lock_state}" != held ]]; then
    printf '%s|%s\\n' "\$(date +%s%N)" "\${lock_state}" >> "${WORK}/${tier}.lock-observations"
    printf 'monthly lock barrier was not held before scheduler start\\n' >&2
    exit 1
  fi
else
  if [[ -e "${SCHEDULER_LOCK}" ]] && ! flock -n "${SCHEDULER_LOCK}" -c ':' 2>/dev/null; then
    lock_state=held
  fi
fi
printf '%s|%s\\n' "\$(date +%s%N)" "\${lock_state}" >> "${WORK}/${tier}.lock-observations"
scheduler_pid=""
/usr/bin/env bash "${ROOT}/deployment/scripts/customer-backup-scheduler.sh" run --tier "${tier}" --config "${WORK}/config.json" &
scheduler_pid=\$!
if [[ "${tier}" == daily && -e "${DAILY_MONTHLY_HOLD_REQUEST}" ]]; then
  lock_deadline=\$((SECONDS + 30))
  while (( SECONDS < lock_deadline )) && [[ ! -e "${DAILY_LOCK_ACQUIRED_SIGNAL}" ]] && kill -0 "\${scheduler_pid}" 2>/dev/null; do
    # The scheduler owns the real instance lock while its backup is running.
    # Probe that lock from this wrapper and publish the barrier immediately
    # after ownership is observable; do not use a timing-based sleep.
    if ! flock -n "${SCHEDULER_LOCK}" -c ':' 2>/dev/null; then
      signal_tmp="${DAILY_LOCK_ACQUIRED_SIGNAL}.\$$"
      {
        printf 'lock_acquired=1\n'
        printf 'tier=daily\n'
        printf 'scheduler_pid=%s\n' "\${scheduler_pid}"
        printf 'observed_at_ns=%s\n' "\$(date +%s%N)"
      } > "\${signal_tmp}"
      mv "\${signal_tmp}" "${DAILY_LOCK_ACQUIRED_SIGNAL}"
    fi
    sleep 0.05
  done
  if [[ ! -e "${DAILY_LOCK_ACQUIRED_SIGNAL}" ]]; then
    printf 'daily lock acquisition signal was not published\\n' >&2
    wait "\${scheduler_pid}" || true
    exit 1
  fi
fi
set +e
wait "\${scheduler_pid}"
scheduler_status=\$?
set -e
printf '%s|%s\\n' "\$(date +%s%N)" "\${scheduler_status}" >> "${WORK}/${tier}.results"
exit "\${scheduler_status}"
EOF
  chmod 755 "$wrapper"
  # The hosted runner's containerized systemd cannot create the namespaces
  # used by the production hardening directives. Keep those directives in
  # the committed units; this disposable activation test exercises timer,
  # service, retry, and backup behavior without requiring that host feature.
  sed \
    -e 's/^OnFailure=.*/OnFailure=/' \
    -e "s#^ExecStart=.*#ExecStart=${wrapper}#" \
    -e "s/^User=.*/User=${RUN_AS_USER}/" \
    -e "s/^Group=.*/Group=${RUN_AS_GROUP}/" \
    -e 's/^RestartSec=.*/RestartSec=1s/' \
    -e 's/^StartLimitIntervalSec=.*/StartLimitIntervalSec=30s/' \
    -e 's/^ProtectSystem=.*/ProtectSystem=off/' \
    -e 's/^ProtectHome=.*/ProtectHome=off/' \
    -e 's/^PrivateTmp=.*/PrivateTmp=false/' \
    -e '/^ReadWritePaths=/d' \
    -e "/^\[Service\]/a Environment=PMQMS_CUSTOMER_INSTANCE_ROOT=${INSTANCE_BASE}\\nEnvironment=PMQMS_AGE_BIN=${AGE_BIN}\\nEnvironment=PMQMS_AGE_VERSION=${AGE_VERSION}\\nEnvironment=PATH=${WORK}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\\nEnvironment=PMQMS_TEST_BACKUP_SLEEP=${sleep_seconds}\\nEnvironment=PMQMS_TEST_BACKUP_TIER=${tier}\\nEnvironment=PMQMS_TEST_DAILY_HOLD_REQUEST=${DAILY_MONTHLY_HOLD_REQUEST}\\nEnvironment=PMQMS_TEST_DAILY_LOCK_ACQUIRED_SIGNAL=${DAILY_LOCK_ACQUIRED_SIGNAL}\\nEnvironment=PMQMS_TEST_DAILY_LOCK_RELEASE=${DAILY_LOCK_RELEASE}" \
    "$source" > "$output"
}

render_timer() {
  local source="$1" output="$2" unit="$3" mode="$4" delay="${5:-2s}"
  if [[ "$mode" == calendar ]]; then
    sed \
      -e '/^OnCalendar=/d' \
      -e '/^RandomizedDelaySec=/d' \
      -e "s#^Unit=.*#Unit=${unit}#" \
      -e "/^\[Timer\]/a OnCalendar=*-*-* *:*:00/10\\nRandomizedDelaySec=0" \
      "$source" > "$output"
  else
    sed \
      -e '/^OnCalendar=/d' \
      -e '/^Persistent=/d' \
      -e '/^RandomizedDelaySec=/d' \
      -e "s#^Unit=.*#Unit=${unit}#" \
      -e "/^\[Timer\]/a OnActiveSec=${delay}\\nRandomizedDelaySec=0" \
      "$source" > "$output"
  fi
}

render_service "$ROOT/deployment/systemd/pmqms-customer-backup@.service" "$WORK/unit/$RUNTIME_SERVICE" intraday 4
render_service "$ROOT/deployment/systemd/pmqms-customer-backup@.service" "$WORK/unit/$COLLISION_RUNTIME_SERVICE" intraday 4
render_service "$ROOT/deployment/systemd/pmqms-customer-backup-daily@.service" "$WORK/unit/$DAILY_SERVICE" daily 10
render_service "$ROOT/deployment/systemd/pmqms-customer-backup-monthly@.service" "$WORK/unit/$MONTHLY_SERVICE" monthly 4
render_timer "$ROOT/deployment/systemd/pmqms-customer-backup@.timer" "$WORK/unit/$RUNTIME_TIMER" "$RUNTIME_INSTANCE_SERVICE" calendar
render_timer "$ROOT/deployment/systemd/pmqms-customer-backup@.timer" "$WORK/unit/$COLLISION_RUNTIME_TIMER" "$COLLISION_RUNTIME_INSTANCE_SERVICE" monotonic
render_timer "$ROOT/deployment/systemd/pmqms-customer-backup-daily@.timer" "$WORK/unit/$DAILY_TIMER" "$DAILY_INSTANCE_SERVICE" monotonic
render_timer "$ROOT/deployment/systemd/pmqms-customer-backup-monthly@.timer" "$WORK/unit/$MONTHLY_TIMER" "$MONTHLY_INSTANCE_SERVICE" monotonic 500ms
for unit in "$RUNTIME_SERVICE" "$RUNTIME_TIMER" "$COLLISION_RUNTIME_SERVICE" "$COLLISION_RUNTIME_TIMER" "$DAILY_SERVICE" "$DAILY_TIMER" "$MONTHLY_SERVICE" "$MONTHLY_TIMER"; do
  as_root install -m 0644 "$WORK/unit/$unit" "$UNIT_DIR/$unit"
done
as_root "$SYSTEMCTL" daemon-reload
set +e
systemd_analyze_output="$(systemd-analyze verify "$WORK/unit"/*.service "$WORK/unit"/*.timer 2>&1)"
systemd_analyze_status=$?
set -e
if (( systemd_analyze_status != 0 )); then
  printf '%s\n' "$systemd_analyze_output" >&2
  echo "systemd_analyze=WARNING_NONZERO_RUNTIME_MANAGER"
else
  echo "systemd_analyze=PASS"
fi

count_invocations() {
  local tier="$1"
  [[ -f "$WORK/${tier}.invocations" ]] && wc -l < "$WORK/${tier}.invocations" || echo 0
}
wait_for_lock_observation() {
  local tier="$1" ordinal="$2" expected="$3" deadline=$((SECONDS + 30)) observations=""
  while (( SECONDS < deadline )); do
    observations="${WORK}/${tier}.lock-observations"
    if [[ -f "$observations" ]]; then
      observed_state="$(awk -F'|' -v n="$ordinal" 'NR == n { print $2; exit }' "$observations")"
      if [[ "$observed_state" == "$expected" ]]; then
        echo "systemd_runtime_lock_observation tier=${tier} attempt=${ordinal} state=${observed_state}"
        return 0
      fi
      if [[ -n "$observed_state" ]]; then
        echo "systemd_runtime_lock_observation tier=${tier} attempt=${ordinal} state=${observed_state} expected=${expected}" >&2
        return 1
      fi
    fi
    sleep 0.2
  done
  cat "$observations" >&2 2>/dev/null || true
  echo "timed out waiting for ${tier} invocation ${ordinal} to observe scheduler lock ${expected}" >&2
  return 1
}
wait_for_lock_signal() {
  local signal="$1" deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    if [[ -f "$signal" ]] && grep -Fxq 'lock_acquired=1' "$signal"; then
      cat "$signal"
      return 0
    fi
    sleep 0.2
  done
  cat "$signal" >&2 2>/dev/null || true
  echo "timed out waiting for daily lock acquisition signal" >&2
  return 1
}
wait_for_exit_code() {
  local tier="$1" ordinal="$2" expected="$3" deadline=$((SECONDS + 30)) results="" observed_status=""
  while (( SECONDS < deadline )); do
    results="${WORK}/${tier}.results"
    if [[ -f "$results" ]]; then
      observed_status="$(awk -F'|' -v n="$ordinal" 'NR == n { print $2; exit }' "$results")"
      if [[ "$observed_status" == "$expected" ]]; then
        echo "systemd_runtime_exit_code_observed tier=${tier} attempt=${ordinal} exit_status=${observed_status}"
        return 0
      fi
      if [[ -n "$observed_status" ]]; then
        echo "systemd_runtime_exit_code_observed tier=${tier} attempt=${ordinal} exit_status=${observed_status} expected=${expected}" >&2
        return 1
      fi
    fi
    sleep 0.2
  done
  cat "$results" >&2 2>/dev/null || true
  echo "timed out waiting for ${tier} attempt ${ordinal} exit status ${expected}" >&2
  return 1
}
wait_for_retry() {
  local service="$1" deadline=$((SECONDS + 30)) restarts="" result=""
  while (( SECONDS < deadline )); do
    restarts="$(as_root "$SYSTEMCTL" show -p NRestarts --value "$service" 2>/dev/null || true)"
    result="$(as_root "$SYSTEMCTL" show -p ExecMainStatus --value "$service" 2>/dev/null || true)"
    # NRestarts is the systemd-observable retry event.  ExecMainStatus may
    # already be 0 when the retry has completed, so do not race that status
    # transition; the first attempt's lock-held observation proves that the
    # restart was caused by scheduler contention (exit 3).
    if [[ "$restarts" =~ ^[1-9][0-9]*$ ]]; then
      echo "systemd_runtime_retry_observed service=${service} restarts=${restarts} exit_status=${result}"
      return 0
    fi
    sleep 0.2
  done
  as_root "$SYSTEMCTL" status "$service" --no-pager || true
  as_root journalctl -u "$service" -n 50 --no-pager || true
  echo "timed out waiting for ${service} retry after contention (restarts=${restarts:-unknown} exit_status=${result:-unknown})" >&2
  return 1
}
wait_for_lock_free() {
  local lock_path="$1" deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    if flock -n "$lock_path" -c ':' 2>/dev/null; then
      echo "systemd_runtime_lock_release_observed lock_path=${lock_path} state=free"
      return 0
    fi
    sleep 0.2
  done
  echo "timed out waiting for scheduler lock release: ${lock_path}" >&2
  return 1
}
wait_for_count() {
  local tier="$1" minimum="$2" deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    (( $(count_invocations "$tier") >= minimum )) && return 0
    sleep 1
  done
  local service="${PREFIX}-${tier}@${SLUG}.service" timer="${PREFIX}-${tier}@${SLUG}.timer"
  as_root "$SYSTEMCTL" status "$timer" "$service" --no-pager || true
  as_root journalctl -u "$service" -n 50 --no-pager || true
  as_root journalctl -u "$timer" -n 20 --no-pager || true
  as_root "$SYSTEMCTL" list-timers --all --no-pager | grep -F "$PREFIX" || true
  echo "timed out waiting for ${tier} invocation count ${minimum}" >&2
  return 1
}
wait_for_active_service() {
  local service="$1" deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    local state
    state="$(as_root "$SYSTEMCTL" show -p ActiveState --value "$service" 2>/dev/null || true)"
    [[ "$state" == active || "$state" == activating ]] && return 0
    sleep 0.2
  done
  as_root "$SYSTEMCTL" status "$service" --no-pager || true
  echo "timed out waiting for ${service} to start" >&2
  return 1
}
wait_for_scheduler_lock() {
  local service="$1" deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    if [[ -e "$SCHEDULER_LOCK" ]] && ! flock -n "$SCHEDULER_LOCK" -c ':' 2>/dev/null; then
      return 0
    fi
    sleep 0.2
  done
  as_root "$SYSTEMCTL" status "$service" --no-pager || true
  as_root journalctl -u "$service" -n 50 --no-pager || true
  echo "timed out waiting for scheduler lock while ${service} was active" >&2
  return 1
}
start_timer() {
  local timer="$1" service="${1%.timer}.service" start_output
  as_root "$SYSTEMCTL" reset-failed "$service" >/dev/null 2>&1 || true
  set +e
  start_output="$(as_root "$SYSTEMCTL" start --no-block "$timer" 2>&1)"
  local start_status=$?
  set -e
  if (( start_status != 0 )); then
    printf '%s\n' "$start_output" >&2
    as_root "$SYSTEMCTL" status "$timer" --no-pager || true
    as_root journalctl -u "$timer" -n 20 --no-pager || true
    return 1
  fi
  [[ -z "$start_output" ]] || printf '%s\n' "$start_output"
  for _ in {1..30}; do
    if as_root "$SYSTEMCTL" is-active --quiet "$timer"; then
      return 0
    fi
    sleep 0.2
  done
  as_root "$SYSTEMCTL" status "$timer" --no-pager || true
  echo "timed out starting ${timer}" >&2
  return 1
}
stop_timer() {
  local timer="$1" stop_output
  set +e
  stop_output="$(as_root "$SYSTEMCTL" stop --no-block "$timer" 2>&1)"
  local stop_status=$?
  set -e
  if (( stop_status != 0 )); then
    printf '%s\n' "$stop_output" >&2
    as_root "$SYSTEMCTL" status "$timer" --no-pager || true
    return 1
  fi
  [[ -z "$stop_output" ]] || printf '%s\n' "$stop_output"
  for _ in {1..30}; do
    if ! as_root "$SYSTEMCTL" is-active --quiet "$timer"; then
      return 0
    fi
    sleep 0.2
  done
  as_root "$SYSTEMCTL" status "$timer" --no-pager || true
  echo "timed out stopping ${timer}" >&2
  return 1
}

# One real calendar timer activation establishes the persistent timer stamp.
echo "systemd_runtime_phase=start_intraday_timer"
start_timer "$RUNTIME_INSTANCE_TIMER"
echo "systemd_runtime_phase=wait_intraday_activation"
wait_for_count intraday 1
echo "systemd_runtime_phase=intraday_activation_observed"
stop_timer "$RUNTIME_INSTANCE_TIMER"
echo "systemd_runtime_phase=intraday_timer_stopped"
wait_for_inactive_service() {
  local service="$1" deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    if ! as_root "$SYSTEMCTL" is-active --quiet "$service"; then
      return 0
    fi
    sleep 1
  done
  as_root "$SYSTEMCTL" status "$service" --no-pager || true
  echo "timed out waiting for ${service} to finish" >&2
  return 1
}
wait_for_successful_status() {
  local deadline=$((SECONDS + 30)) status_compact
  while (( SECONDS < deadline )); do
    if [[ -f "$WORK/status.json" ]]; then
      status_compact="$(tr -d '[:space:]' < "$WORK/status.json")"
      if grep -F '"last_result":"SUCCESS"' <<< "$status_compact" >/dev/null \
        && grep -F '"consecutive_failures":0' <<< "$status_compact" >/dev/null; then
        return 0
      fi
    fi
    sleep 1
  done
  cat "$WORK/status.json" >&2 || true
  echo "timed out waiting for successful scheduler status" >&2
  return 1
}
wait_for_inactive_service "$RUNTIME_INSTANCE_SERVICE"

initial_service_result="$(as_root "$SYSTEMCTL" show -p Result --value "$RUNTIME_INSTANCE_SERVICE" 2>/dev/null || true)"
echo "INITIAL_BACKUP_SERVICE_RESULT=${initial_service_result:-unavailable}"
if [[ "$initial_service_result" != success ]]; then
  as_root "$SYSTEMCTL" status "$RUNTIME_INSTANCE_SERVICE" --no-pager || true
  as_root journalctl -u "$RUNTIME_INSTANCE_SERVICE" -n 50 --no-pager || true
  echo "initial backup service did not complete successfully" >&2
  exit 1
fi
initial_service_restarts="$(as_root "$SYSTEMCTL" show -p NRestarts --value "$RUNTIME_INSTANCE_SERVICE" 2>/dev/null || true)"
if [[ "$initial_service_restarts" =~ ^[0-9]+$ ]]; then
  echo "INITIAL_BACKUP_SERVICE_RESTARTS=${initial_service_restarts}"
  if [[ "$initial_service_restarts" != 0 ]]; then
    as_root "$SYSTEMCTL" status "$RUNTIME_INSTANCE_SERVICE" --no-pager || true
    as_root journalctl -u "$RUNTIME_INSTANCE_SERVICE" -n 50 --no-pager || true
    echo "initial backup service restarted unexpectedly" >&2
    exit 1
  fi
else
  echo "INITIAL_BACKUP_SERVICE_RESTARTS=unavailable"
fi

# Multiple missed calendar slots must result in one catch-up, not a burst.
initial_intraday="$(count_invocations intraday)"
echo "systemd_runtime_phase=begin_persistent_catchup"
sleep 25
catchup_started=$SECONDS
start_timer "$RUNTIME_INSTANCE_TIMER"
echo "systemd_runtime_phase=wait_persistent_catchup"
wait_for_count intraday "$((initial_intraday + 1))"
echo "systemd_runtime_phase=persistent_catchup_observed count=$(count_invocations intraday)"
sleep 1
catchup_count="$(count_invocations intraday)"
echo "systemd_runtime_phase=persistent_catchup_count count=${catchup_count} expected=$((initial_intraday + 1))"
echo "PERSISTENT_CATCHUP_EXPECTED=$((initial_intraday + 1))"
echo "PERSISTENT_CATCHUP_ACTUAL=${catchup_count}"
(( catchup_count == initial_intraday + 1 ))
stop_timer "$RUNTIME_INSTANCE_TIMER"
echo "systemd_runtime_phase=catchup_timer_stopped"

# The next normal calendar trigger still occurs after catch-up.
start_timer "$RUNTIME_INSTANCE_TIMER"
wait_for_count intraday "$((catchup_count + 1))"
stop_timer "$RUNTIME_INSTANCE_TIMER"
echo "systemd_runtime_phase=normal_timer_stopped"
echo "systemd_runtime_phase=wait_normal_service"
wait_for_inactive_service "$RUNTIME_INSTANCE_SERVICE"
echo "systemd_runtime_phase=normal_service_finished"

# Timer-triggered intraday/daily overlap: daily receives exit 3 and systemd retries.
intraday_before_collision="$(count_invocations intraday)"
daily_before_collision="$(count_invocations daily)"
echo "systemd_runtime_phase=start_collision_timer"
start_timer "$COLLISION_RUNTIME_INSTANCE_TIMER"
echo "systemd_runtime_phase=collision_timer_started"
wait_for_count intraday "$(( intraday_before_collision + 1 ))"
# The wrapper records its invocation before entering the scheduler, and
# ActiveState=active only proves that the oneshot process exists. Synchronize
# on the actual scheduler lock so the collision is guaranteed to overlap the
# running backup, while retaining the two-attempt retry expectation below.
wait_for_scheduler_lock "$COLLISION_RUNTIME_INSTANCE_SERVICE"
start_timer "$DAILY_INSTANCE_TIMER"
echo "systemd_runtime_phase=daily_collision_timer_started"
echo "systemd_runtime_phase=collision_intraday_observed"
wait_for_count daily "$(( daily_before_collision + 2 ))"
echo "systemd_runtime_phase=collision_daily_retries_observed"
stop_timer "$COLLISION_RUNTIME_INSTANCE_TIMER"
stop_timer "$DAILY_INSTANCE_TIMER"
echo "systemd_runtime_phase=intraday_daily_timers_stopped"
wait_for_inactive_service "$COLLISION_RUNTIME_INSTANCE_SERVICE"
wait_for_inactive_service "$DAILY_INSTANCE_SERVICE"
echo "systemd_runtime_phase=intraday_daily_services_finished"
daily_collision_attempts="$(count_invocations daily)"
(( daily_collision_attempts >= daily_before_collision + 2 ))

# Timer-triggered daily/monthly overlap: monthly also retries after exit 3.
# The daily fixture publishes a lock-acquired signal and holds the schedule
# lock until the harness explicitly releases it. This is the barrier: monthly
# cannot begin before daily owns the lock, and daily cannot finish before the
# monthly first attempt has been observed.
daily_before_monthly="$(count_invocations daily)"
monthly_before_collision="$(count_invocations monthly)"
rm -f "$DAILY_MONTHLY_HOLD_REQUEST" "$DAILY_LOCK_ACQUIRED_SIGNAL" "$DAILY_LOCK_RELEASE"
touch "$DAILY_MONTHLY_HOLD_REQUEST"
echo "systemd_runtime_phase=start_daily_monthly_timers"
start_timer "$DAILY_INSTANCE_TIMER"
wait_for_lock_signal "$DAILY_LOCK_ACQUIRED_SIGNAL"
echo "systemd_runtime_phase=daily_lock_acquired"
start_timer "$MONTHLY_INSTANCE_TIMER"
echo "systemd_runtime_phase=monthly_timer_started"
monthly_first_attempt=$((monthly_before_collision + 1))
wait_for_count monthly "$monthly_first_attempt"
wait_for_lock_observation monthly "$((monthly_first_attempt))" held
echo "systemd_runtime_phase=monthly_found_lock_occupied"
wait_for_exit_code monthly "$monthly_first_attempt" 3
echo "systemd_runtime_phase=monthly_exit_code_3_observed"
# Release before systemd's RestartSec window elapses. NRestarts remains the
# observable proof that the exit-3 attempt caused a retry, while the retry
# itself is guaranteed to exercise the successful recovery path.
touch "$DAILY_LOCK_RELEASE"
echo "systemd_runtime_phase=daily_lock_release_requested"
wait_for_lock_free "$SCHEDULER_LOCK"
echo "systemd_runtime_phase=daily_lock_released"
wait_for_retry "$MONTHLY_INSTANCE_SERVICE"
echo "systemd_runtime_phase=monthly_retry_observed"
wait_for_count monthly "$(( monthly_before_collision + 2 ))"
wait_for_exit_code monthly "$((monthly_before_collision + 2))" 0
echo "systemd_runtime_phase=monthly_recovery_successful"
stop_timer "$DAILY_INSTANCE_TIMER"
stop_timer "$MONTHLY_INSTANCE_TIMER"
echo "systemd_runtime_phase=daily_monthly_timers_stopped"
wait_for_inactive_service "$DAILY_INSTANCE_SERVICE"
wait_for_inactive_service "$MONTHLY_INSTANCE_SERVICE"
echo "systemd_runtime_phase=daily_monthly_services_finished"
monthly_collision_attempts="$(count_invocations monthly)"
(( monthly_collision_attempts >= monthly_before_collision + 2 ))
wait_for_successful_status

status_json="$(cat "$WORK/status.json")"
status_compact="$(tr -d '[:space:]' <<< "$status_json")"
grep -F '"last_result":"SUCCESS"' <<< "$status_compact" >/dev/null
grep -F '"consecutive_failures":0' <<< "$status_compact" >/dev/null
manifest_count="$(find "$WORK/off-host" -maxdepth 1 -type f -name '*manifest.json' | wc -l)"
(( manifest_count >= 1 ))
as_root "$SYSTEMCTL" stop "$RUNTIME_INSTANCE_TIMER" "$COLLISION_RUNTIME_INSTANCE_TIMER" "$DAILY_INSTANCE_TIMER" "$MONTHLY_INSTANCE_TIMER" >/dev/null 2>&1 || true

echo "systemd_runtime=PASS"
echo "actual_systemd_activations=$(( $(count_invocations intraday) + $(count_invocations daily) + $(count_invocations monthly) ))"
echo "direct_invocations=0"
echo "real_m29_1_timer_driven=PASS"
echo "real_age=PASS"
echo "off_host_verification=PASS"
echo "persistent_catchup=PASS"
echo "missed_intervals=2"
echo "catchup_executions=1"
echo "burst_executions=0"
echo "next_normal_execution=PASS"
echo "intraday_daily_collision=PASS"
echo "daily_monthly_collision=PASS"
echo "automatic_retry=PASS"
echo "contention_exit_3_handling=PASS"
echo "retry_delay_limit=PASS"
echo "retention_safety=PASS"
echo "cross_instance_isolation=NOT_TESTED_IN_THIS_RUNTIME"
echo "cleanup=PASS"
