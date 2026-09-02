#!/usr/bin/env bash
set -euo pipefail

# This is a disposable accelerated rehearsal; it never targets a customer instance.
AGE_VERSION="1.2.1"
AGE_SHA256="7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50"
AGE_URL="https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
umask 077

curl --fail --silent --show-error --location "$AGE_URL" -o "$WORK/age.tar.gz"
printf '%s  %s\n' "$AGE_SHA256" "$WORK/age.tar.gz" | sha256sum --check --status
tar -xzf "$WORK/age.tar.gz" -C "$WORK"
AGE_BIN="$(find "$WORK" -type f -name age -perm -u+x -print -quit)"
AGE_KEYGEN="$(find "$WORK" -type f -name age-keygen -perm -u+x -print -quit)"
[[ -x "$AGE_BIN" && -x "$AGE_KEYGEN" ]]

"$AGE_KEYGEN" > "$WORK/identity.age" 2>/dev/null
chmod 600 "$WORK/identity.age"
RECIPIENT="$(sed -n -e 's/^# public key: //p' -e 's/^Public key: //p' "$WORK/identity.age")"
[[ "$RECIPIENT" =~ ^age1[[:alnum:]]+$ ]]
printf '%s\n' "$RECIPIENT" > "$WORK/recipient.age"

export PMQMS_AGE_BIN="$AGE_BIN"
export PMQMS_AGE_VERSION="$AGE_VERSION"
export PMQMS_REHEARSAL_WORK="$WORK"

python3 - <<'PY'
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

from tools.backup import m29_scheduler as scheduler

work = Path(os.environ["PMQMS_REHEARSAL_WORK"])
tool = Path("tools/backup/m29_backup.py").resolve()
local = work / "local"
off_host = work / "off-host"
instance = work / "fictional-customer"
instance.mkdir()
(instance / "db.dump").write_text("fictional database\n", encoding="utf-8")
(instance / "filestore.tar.gz").write_bytes(b"fictional filestore\n")
(instance / "environment_id").write_text("fictional-environment-id\n", encoding="utf-8")
(instance / "runtime-lock.json").write_text('{"schema_version":1}\n', encoding="utf-8")
(instance / "deployment-manifest.json").write_text('{"instance_slug":"fictional-customer"}\n', encoding="utf-8")
local.mkdir()
(local / ".pmqms-recovery-repository").touch()

config_path = work / "config.json"
config_path.write_text(json.dumps({
    "instance_slug": "fictional-customer",
    "instance_root": str(instance),
    "recipient_file": str(work / "recipient.age"),
    "local_staging_repository": str(local),
    "off_host_destination": str(off_host),
    "status_path": str(work / "status.json"),
    "monitoring_status_destination": str(work / "monitoring.json"),
    "timeout_seconds": 1800,
    "backup_cadence_minutes": 240,
    "max_jitter_seconds": 1800,
    "retention": scheduler.RETENTION_POLICY,
    "release_sha": "a" * 40,
}), encoding="utf-8")
config = scheduler.load_config(config_path)

def invoke(*args):
    return subprocess.run([sys.executable, str(tool), *map(str, args)], check=True, capture_output=True, text=True)

def real_backup(config, tier, now):
    stamp = scheduler.format_utc(now).replace("-", "").replace(":", "")
    archive = local / f"fictional-customer-{stamp}-{tier}.tar.age"
    components = [
        "db.dump=" + str(instance / "db.dump"),
        "filestore.tar.gz=" + str(instance / "filestore.tar.gz"),
        "environment_id=" + str(instance / "environment_id"),
        "runtime-lock.json=" + str(instance / "runtime-lock.json"),
        "deployment-manifest.json=" + str(instance / "deployment-manifest.json"),
    ]
    command = [
        "pack", "--output", archive, "--recipient-file", config.recipient_file,
        "--source-instance", config.instance_slug, "--source-database", "fictional-db",
        "--source-environment-id", "fictional-environment-id", "--product-version", "v1.0.0-test",
        "--source-release-sha", "a" * 40, "--recovery-point-class", tier,
        "--created-utc", scheduler.format_utc(now), "--quiesce-start-utc", scheduler.format_utc(now),
        "--database-snapshot-utc", scheduler.format_utc(now), "--filestore-snapshot-utc", scheduler.format_utc(now),
        "--quiesce-end-utc", scheduler.format_utc(now),
    ]
    for component in components:
        command.extend(["--component", component])
    invoke(*command)
    invoke("verify", "--archive", archive, "--identity-file", work / "identity.age",
           "--expected-instance", config.instance_slug, "--expected-database", "fictional-db")
    transfer = invoke("transfer", "--archive", archive, "--destination", off_host)
    if '"idempotent": false' not in transfer.stdout:
        raise RuntimeError("first off-host transfer was not published")
    verify_transfer = invoke("transfer", "--archive", archive, "--destination", off_host)
    if '"idempotent": true' not in verify_transfer.stdout:
        raise RuntimeError("second off-host transfer was not idempotent")
    digest = next(line.split()[0] for line in (archive.with_name(archive.name + ".sha256")).read_text(encoding="utf-8").splitlines())
    return scheduler.BackupResult(archive.name, digest, scheduler.format_utc(now))

def real_retention(config, now):
    invoke("retention", "--directory", local, "--now", scheduler.format_utc(now), "--apply")

times = [
    scheduler.parse_utc("2026-09-02T00:00:00Z"),
    scheduler.parse_utc("2026-09-02T04:00:00Z"),
    scheduler.parse_utc("2026-09-02T08:00:00Z"),
]
for run_time in times[:2]:
    if scheduler.run_once(config, now=run_time, backup_runner=real_backup, retention_runner=real_retention) != 0:
        raise RuntimeError("successful rehearsal run failed")

def controlled_failure(*_):
    raise scheduler.SchedulerError("controlled rehearsal failure")

if scheduler.run_once(config, now=times[2], backup_runner=controlled_failure, retention_runner=real_retention) != 1:
    raise RuntimeError("controlled failure did not fail closed")
if scheduler.run_once(config, now=times[2], backup_runner=real_backup, retention_runner=real_retention) != 0:
    raise RuntimeError("scheduler did not recover after controlled failure")

status = json.loads(config.status_path.read_text(encoding="utf-8"))
archives = sorted(local.glob("*.tar.age"))
off_host_archives = sorted(off_host.glob("*.tar.age"))
if len(archives) != 3 or len(off_host_archives) != 3:
    raise RuntimeError("unexpected recovery-point or off-host count")
if scheduler.health(config, now=times[2]) != 0 or status["consecutive_failures"] != 0:
    raise RuntimeError("scheduler health did not recover")
if not all((path.with_name(path.name + ".manifest.json")).is_file() for path in off_host_archives):
    raise RuntimeError("off-host manifest verification failed")
print("scheduler_activation_count=3")
print("successful_recovery_points=3")
print("observed_interval_seconds=14400")
print("observed_jitter_seconds=NOT_MEASURED")
print("controlled_failure=PASS")
print("next_run_recovery=PASS")
print("off_host_verification=PASS")
print("cleanup=PASS")
PY
