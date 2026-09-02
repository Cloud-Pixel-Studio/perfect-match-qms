#!/usr/bin/env python3
"""Run and inspect the fixed-UTC customer recovery-point scheduler."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import errno
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows is used for local authoring only
    fcntl = None

VERSION = "29.2.0"
RPO_SECONDS = 6 * 60 * 60
CADENCE_MINUTES = 4 * 60
MAX_JITTER_SECONDS = 30 * 60
SCHEDULE_HOURS_UTC = (0, 4, 8, 12, 16, 20)
RETENTION_POLICY = {"intraday_days": 7, "daily_days": 30, "monthly_months": 12}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_LOCAL_LOCKS: set[Path] = set()


class SchedulerError(RuntimeError):
    """A sanitized, operator-actionable scheduler error."""


class AlreadyRunning(SchedulerError):
    """The same instance already has an active scheduler invocation."""


@dataclass(frozen=True)
class SchedulerConfig:
    instance_slug: str
    instance_root: Path
    recipient_file: Path
    local_staging_repository: Path
    off_host_destination: Path
    status_path: Path
    timeout_seconds: int
    backup_cadence_minutes: int
    max_jitter_seconds: int
    retention: dict[str, int]
    monitoring_status_destination: Path
    release_sha: str


@dataclass(frozen=True)
class BackupResult:
    archive_id: str
    archive_sha256: str
    consistency_timestamp_utc: str
    off_host_verification: str = "PASS"


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def format_utc(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SchedulerError("invalid UTC timestamp") from exc
    if parsed.tzinfo is None:
        raise SchedulerError("scheduler timestamps must include a UTC offset")
    return parsed.astimezone(dt.timezone.utc)


def _path(value: object, label: str, *, must_exist: bool = False) -> Path:
    if not isinstance(value, str) or not value or not os.path.isabs(value) or ".." in Path(value).parts:
        raise SchedulerError(f"invalid {label} path")
    result = Path(value).resolve(strict=False)
    if result in {Path(result.anchor), Path(result.anchor) / "tmp", Path(result.anchor) / "var", Path(result.anchor) / "etc", Path(result.anchor) / "opt", Path(result.anchor) / "home"}:
        raise SchedulerError(f"{label} path is too broad")
    if must_exist and (not result.is_file() or result.is_symlink() or not os.access(result, os.R_OK)):
        raise SchedulerError(f"{label} is missing or unreadable")
    return result


def load_config(path: Path) -> SchedulerConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchedulerError("scheduler configuration is missing or invalid") from exc
    if not isinstance(raw, dict):
        raise SchedulerError("scheduler configuration must be an object")
    forbidden = {key for key in raw if any(term in key.lower() for term in ("password", "private", "identity", "token", "secret"))}
    if forbidden:
        raise SchedulerError("scheduler configuration contains forbidden secret fields")
    required = {
        "instance_slug", "instance_root", "recipient_file", "local_staging_repository",
        "off_host_destination", "status_path", "monitoring_status_destination",
        "timeout_seconds", "backup_cadence_minutes", "max_jitter_seconds", "retention",
    }
    if not required.issubset(raw):
        raise SchedulerError("scheduler configuration is incomplete")
    slug = raw["instance_slug"]
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        raise SchedulerError("invalid instance slug")
    instance_root = _path(raw["instance_root"], "instance root")
    recipient = _path(raw["recipient_file"], "recipient file", must_exist=True)
    local = _path(raw["local_staging_repository"], "local staging repository")
    off_host = _path(raw["off_host_destination"], "off-host destination")
    status = _path(raw["status_path"], "status")
    monitoring = _path(raw["monitoring_status_destination"], "monitoring status")
    if local == off_host or local in off_host.parents or off_host in local.parents:
        raise SchedulerError("local and off-host destinations must be distinct")
    if status in {recipient, local, off_host} or monitoring in {recipient, local, off_host}:
        raise SchedulerError("status destinations collide with protected paths")
    if not isinstance(raw["timeout_seconds"], int) or not 1 <= raw["timeout_seconds"] <= 86400:
        raise SchedulerError("timeout must be between one second and one day")
    if raw["backup_cadence_minutes"] != CADENCE_MINUTES:
        raise SchedulerError("production backup cadence must be exactly four hours")
    if not isinstance(raw["max_jitter_seconds"], int) or not 0 <= raw["max_jitter_seconds"] <= MAX_JITTER_SECONDS:
        raise SchedulerError("maximum jitter must not exceed thirty minutes")
    retention = raw["retention"]
    if retention != RETENTION_POLICY:
        raise SchedulerError("retention policy does not match the approved M29.2 policy")
    release_sha = raw.get("release_sha", "")
    if release_sha and (not isinstance(release_sha, str) or not SHA_RE.fullmatch(release_sha)):
        raise SchedulerError("release SHA is invalid")
    return SchedulerConfig(slug, instance_root, recipient, local, off_host, status, raw["timeout_seconds"], raw["backup_cadence_minutes"], raw["max_jitter_seconds"], dict(retention), monitoring, release_sha or "unknown")


def schedule_semantics() -> dict[str, object]:
    maximum_interval = CADENCE_MINUTES * 60 + MAX_JITTER_SECONDS
    return {
        "timezone": "UTC",
        "hours": list(SCHEDULE_HOURS_UTC),
        "cadence_minutes": CADENCE_MINUTES,
        "max_jitter_seconds": MAX_JITTER_SECONDS,
        "maximum_interval_seconds": maximum_interval,
        "rpo_seconds": RPO_SECONDS,
        "maximum_interval_below_rpo": maximum_interval < RPO_SECONDS,
    }


def next_scheduled_run(value: dt.datetime) -> dt.datetime:
    current = value.astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0)
    for hour in SCHEDULE_HOURS_UTC:
        candidate = current.replace(hour=hour)
        if candidate > value.astimezone(dt.timezone.utc):
            return candidate
    return (current + dt.timedelta(days=1)).replace(hour=SCHEDULE_HOURS_UTC[0])


def tier_schedule() -> dict[str, str]:
    return {"intraday": "every four-hour UTC slot", "daily": "00:45 UTC daily", "monthly": "01:30 UTC on day 1"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.part-{os.getpid()}")
    temporary.write_text(json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    with temporary.open("r+b") as handle:
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    try:
        descriptor = os.open(path.parent, os.O_RDONLY)
        os.fsync(descriptor)
        os.close(descriptor)
    except OSError:
        pass


def _read_status(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchedulerError("scheduler status is invalid") from exc
    if not isinstance(value, dict):
        raise SchedulerError("scheduler status is invalid")
    return value


def _write_status(config: SchedulerConfig, data: dict[str, object]) -> None:
    _atomic_write(config.status_path, data)
    if config.monitoring_status_destination != config.status_path:
        _atomic_write(config.monitoring_status_destination, data)


@contextlib.contextmanager
def instance_lock(config: SchedulerConfig) -> Iterator[None]:
    config.local_staging_repository.mkdir(parents=True, exist_ok=True)
    os.chmod(config.local_staging_repository, 0o700)
    lock_path = config.local_staging_repository / ".pmqms-scheduler.lock"
    handle = lock_path.open("a+")
    os.chmod(lock_path, 0o600)
    try:
        try:
            if fcntl is None:
                lock_key = lock_path.resolve()
                if lock_key in _LOCAL_LOCKS:
                    raise AlreadyRunning("backup scheduler already running for instance")
                _LOCAL_LOCKS.add(lock_key)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            if isinstance(exc, BlockingIOError) or getattr(exc, "errno", None) in {errno.EACCES, errno.EAGAIN}:
                raise AlreadyRunning("backup scheduler already running for instance") from exc
            raise SchedulerError("scheduler lock could not be acquired") from exc
        yield
    finally:
        try:
            if fcntl is None:
                _LOCAL_LOCKS.discard(lock_path.resolve())
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _default_backup_runner(config: SchedulerConfig, tier: str, now: dt.datetime) -> BackupResult:
    script = Path(__file__).resolve().parents[2] / "deployment" / "scripts" / "customer-instance.sh"
    command = [
        str(script), "backup", config.instance_slug,
        "--recipient-file", str(config.recipient_file),
        "--off-host-dir", str(config.off_host_destination), "--class", tier,
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=config.timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        raise SchedulerError("backup command timed out") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SchedulerError("backup command failed") from exc
    archive_line = next((line for line in result.stdout.splitlines() if line.startswith("backup=")), "")
    if not archive_line:
        raise SchedulerError("backup command returned no archive")
    archive = Path(archive_line.removeprefix("backup=")).resolve()
    try:
        archive.relative_to(config.local_staging_repository)
    except ValueError as exc:
        raise SchedulerError("backup archive is outside the configured staging repository") from exc
    if not archive.is_file() or archive.is_symlink():
        raise SchedulerError("backup archive is missing")
    manifest = archive.with_name(f"{archive.name}.manifest.json")
    digest = _sha256(archive)
    try:
        outer = json.loads(manifest.read_text(encoding="utf-8"))
        consistency = outer["consistency"]["quiesce_end_utc"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SchedulerError("backup manifest is invalid") from exc
    off_host_archive = config.off_host_destination / archive.name
    if not off_host_archive.is_file() or _sha256(off_host_archive) != digest:
        raise SchedulerError("off-host backup verification failed")
    verify = [sys.executable, str(Path(__file__).resolve()), "verify-backup", str(archive)]
    try:
        subprocess.run(verify, check=True, capture_output=True, text=True, timeout=config.timeout_seconds)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SchedulerError("backup deep verification failed") from exc
    return BackupResult(archive.name, digest, consistency)


def _default_retention_runner(config: SchedulerConfig, now: dt.datetime) -> None:
    script = Path(__file__).resolve().parents[2] / "deployment" / "scripts" / "customer-instance.sh"
    command = [str(script), "retention", config.instance_slug, "--now", format_utc(now), "--apply"]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=config.timeout_seconds)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SchedulerError("retention failed after backup verification") from exc


def _base_status(config: SchedulerConfig, previous: dict[str, object], now: dt.datetime) -> dict[str, object]:
    return {
        "instance_identifier": config.instance_slug,
        "last_attempt_utc": format_utc(now),
        "last_successful_backup_utc": previous.get("last_successful_backup_utc"),
        "recovery_point_consistency_timestamp_utc": previous.get("recovery_point_consistency_timestamp_utc"),
        "archive_identifier": previous.get("archive_identifier"),
        "archive_sha256": previous.get("archive_sha256"),
        "off_host_verification": previous.get("off_host_verification", "NOT_RUN"),
        "duration_seconds": 0,
        "retention_result": "NOT_RUN",
        "next_expected_run_utc": format_utc(next_scheduled_run(now)),
        "failure_code": None,
        "consecutive_failures": int(previous.get("consecutive_failures", 0) or 0),
        "scheduler_version": VERSION,
        "release_sha": config.release_sha,
        "last_result": "NOT_RUN",
    }


def run_once(
    config: SchedulerConfig,
    tier: str = "intraday",
    backup_runner: Callable[[SchedulerConfig, str, dt.datetime], BackupResult] | None = None,
    retention_runner: Callable[[SchedulerConfig, dt.datetime], None] | None = None,
    now: dt.datetime | None = None,
) -> int:
    if tier not in {"intraday", "daily", "monthly"}:
        raise SchedulerError("invalid recovery-point tier")
    backup_runner = backup_runner or _default_backup_runner
    retention_runner = retention_runner or _default_retention_runner
    started = now or utc_now()
    with instance_lock(config):
        previous = _read_status(config.status_path)
        status = _base_status(config, previous, started)
        retention_started = False
        try:
            result = backup_runner(config, tier, started)
            if not re.fullmatch(r"[A-Za-z0-9._-]+", result.archive_id) or not re.fullmatch(r"[0-9a-f]{64}", result.archive_sha256):
                raise SchedulerError("backup result is malformed")
            parse_utc(result.consistency_timestamp_utc)
            retention_started = True
            retention_runner(config, started)
        except SchedulerError as exc:
            status.update({
                "duration_seconds": max(0, int((utc_now() - started).total_seconds())),
                "failure_code": "scheduler_failure",
                "last_result": "FAILURE",
                "retention_result": "FAILURE" if retention_started else "NOT_RUN",
                "consecutive_failures": int(status["consecutive_failures"]) + 1,
            })
            _write_status(config, status)
            print("scheduler_result=FAILURE code=scheduler_failure", file=sys.stderr)
            return 1
        except Exception as exc:  # pragma: no cover - fail closed for unexpected adapters
            status.update({
                "duration_seconds": max(0, int((utc_now() - started).total_seconds())),
                "failure_code": "infrastructure_error",
                "last_result": "FAILURE",
                "retention_result": "FAILURE" if retention_started else "NOT_RUN",
                "consecutive_failures": int(status["consecutive_failures"]) + 1,
            })
            _write_status(config, status)
            print("scheduler_result=FAILURE code=infrastructure_error", file=sys.stderr)
            return 2
        status.update({
            "last_successful_backup_utc": format_utc(started),
            "recovery_point_consistency_timestamp_utc": result.consistency_timestamp_utc,
            "archive_identifier": result.archive_id,
            "archive_sha256": result.archive_sha256,
            "off_host_verification": result.off_host_verification,
            "duration_seconds": max(0, int((utc_now() - started).total_seconds())),
            "retention_result": "PASS",
            "failure_code": None,
            "consecutive_failures": 0,
            "last_result": "SUCCESS",
        })
        _write_status(config, status)
        print("scheduler_result=PASS")
        return 0


def status(config: SchedulerConfig) -> int:
    value = _read_status(config.status_path)
    if not value:
        raise SchedulerError("scheduler status is not available")
    print(json.dumps(value, ensure_ascii=True, sort_keys=True))
    return 0


def health(config: SchedulerConfig, now: dt.datetime | None = None) -> int:
    value = _read_status(config.status_path)
    timestamp = value.get("recovery_point_consistency_timestamp_utc")
    if not isinstance(timestamp, str):
        print("scheduler_health=ERROR code=missing_status")
        return 2
    try:
        age = int(((now or utc_now()) - parse_utc(timestamp)).total_seconds())
    except SchedulerError:
        print("scheduler_health=ERROR code=invalid_status")
        return 2
    if age < 0:
        print("scheduler_health=ERROR code=future_status")
        return 2
    if value.get("last_result") == "FAILURE" or value.get("failure_code"):
        print(f"scheduler_health=FAILED recovery_point_age_seconds={age}")
        return 1
    if age <= RPO_SECONDS:
        print(f"scheduler_health=HEALTHY recovery_point_age_seconds={age}")
        return 0
    print(f"scheduler_health=STALE recovery_point_age_seconds={age}")
    return 1


def verify_backup(archive: Path) -> int:
    if not archive.is_file() or archive.is_symlink():
        raise SchedulerError("backup archive is missing")
    manifest = archive.with_name(f"{archive.name}.manifest.json")
    checksum = archive.with_name(f"{archive.name}.sha256")
    if not manifest.is_file() or not checksum.is_file():
        raise SchedulerError("backup verification sidecar is missing")
    if _sha256(archive) != checksum.read_text(encoding="utf-8").split()[0]:
        raise SchedulerError("backup checksum mismatch")
    print("backup_verification=pass")
    return 0


def _parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("run", "health", "status", "validate-config"):
        item = sub.add_parser(command)
        item.add_argument("--config", required=True)
    sub.add_parser("schedule")
    verify = sub.add_parser("verify-backup")
    verify.add_argument("archive")
    run = root._subparsers._group_actions[0].choices["run"]
    run.add_argument("--tier", choices=("intraday", "daily", "monthly"), default="intraday")
    return root


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "schedule":
            print(json.dumps({"schedule": schedule_semantics(), "tiers": tier_schedule()}, sort_keys=True))
            return 0
        if args.command == "verify-backup":
            return verify_backup(Path(args.archive).resolve())
        config = load_config(Path(args.config).resolve())
        if args.command == "validate-config":
            print("scheduler_config=PASS")
            return 0
        if args.command == "run":
            return run_once(config, args.tier)
        if args.command == "health":
            return health(config)
        return status(config)
    except AlreadyRunning as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except SchedulerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
