#!/usr/bin/env python3
"""Create and verify encrypted, manifest-driven QMS recovery points."""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

FORMAT = "pmqms-recovery-point-v1"
SCHEMA_VERSION = 1
DEFAULT_AGE_VERSION = "1.2.1"
AGE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RELEASE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RECOVERY_MARKER = ".pmqms-recovery-repository"
REQUIRED_COMPONENTS = {
    "db.dump",
    "filestore.tar.gz",
    "environment_id",
    "runtime-lock.json",
    "deployment-manifest.json",
}
OPTIONAL_COMPONENTS = {"active.pmql"}
ALLOWED_COMPONENTS = REQUIRED_COMPONENTS | OPTIONAL_COMPONENTS
REJECTED_COMPONENT_TERMS = (
    "password",
    "credential",
    "secret",
    "token",
    "private-key",
    "identity",
    "recipient",
)
CONSISTENCY_METHOD = "maintenance-write-stop"


class BackupError(RuntimeError):
    """An operator-actionable, fail-closed backup error."""


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def fsync_file(path: Path) -> None:
    with path.open("r+b") as handle:
        os.fsync(handle.fileno())


def fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise BackupError("UTC timestamp is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BackupError(f"invalid UTC timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise BackupError("backup timestamp must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def age_binary() -> str:
    return os.environ.get("PMQMS_AGE_BIN", "age")


def expected_age_version() -> str:
    value = os.environ.get("PMQMS_AGE_VERSION", DEFAULT_AGE_VERSION)
    if not AGE_VERSION_RE.fullmatch(value):
        raise BackupError("configured age version is not a semantic version")
    return value


def actual_age_version(output: str) -> str:
    match = re.search(r"\bage\s+(\d+\.\d+\.\d+)\b", output)
    if not match:
        raise BackupError("age version output is not recognized")
    return match.group(1)


def check_age() -> str:
    expected = expected_age_version()
    try:
        result = subprocess.run([age_binary(), "--version"], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupError("pinned age tool is unavailable or failed version check") from exc
    actual = actual_age_version((result.stdout or "") + "\n" + (result.stderr or ""))
    if actual != expected:
        raise BackupError(f"age tool version mismatch: expected {expected}, got {actual}")
    return actual


def require_file(path: Path, label: str) -> Path:
    if not path.is_file() or path.is_symlink() or not os.access(path, os.R_OK):
        raise BackupError(f"required {label} is missing or unreadable")
    return path


def canonical_json(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(data))
    fsync_file(path)


def safe_name(name: object) -> bool:
    return isinstance(name, str) and bool(name) and Path(name).name == name and name not in {".", ".."}


def component_spec(raw: str) -> tuple[str, Path]:
    name, separator, value = raw.partition("=")
    if not separator or not safe_name(name) or not value:
        raise BackupError("components must use NAME=PATH with a plain component name")
    normalized = name.lower().replace("_", "-")
    if any(term in normalized for term in REJECTED_COMPONENT_TERMS):
        raise BackupError(f"sensitive component is not allowed in recovery payload: {name}")
    path = require_file(Path(value).resolve(), f"component {name}")
    if not path.is_file() or path.is_symlink():
        raise BackupError(f"component is not a regular file: {name}")
    sensitive_parts = {part.lower() for part in path.parts}
    if sensitive_parts & {"secrets", ".ssh"} or path.name.lower() in {"identity", "identity.age", "private.key"}:
        raise BackupError(f"sensitive component source is not allowed: {name}")
    return name, path


def source_identity(args: argparse.Namespace) -> dict:
    values = {
        "instance_slug": args.source_instance,
        "database_name": args.source_database,
        "environment_id": args.source_environment_id,
        "product_version": args.product_version,
        "release_sha": args.source_release_sha,
    }
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise BackupError("source identity fields must be nonempty")
    if not RELEASE_SHA_RE.fullmatch(values["release_sha"]):
        raise BackupError("source release SHA must be a 40-character hexadecimal Git SHA")
    return values


def consistency_metadata(args: argparse.Namespace, created: str) -> dict:
    fields = {
        "method": args.consistency_method,
        "quiesce_start_utc": args.quiesce_start_utc or created,
        "database_snapshot_utc": args.database_snapshot_utc or created,
        "filestore_snapshot_utc": args.filestore_snapshot_utc or created,
        "quiesce_end_utc": args.quiesce_end_utc or created,
    }
    if fields["method"] != CONSISTENCY_METHOD:
        raise BackupError("unsupported consistency method")
    stamps = [parse_utc(fields[key]) for key in (
        "quiesce_start_utc",
        "database_snapshot_utc",
        "filestore_snapshot_utc",
        "quiesce_end_utc",
    )]
    if stamps != sorted(stamps):
        raise BackupError("consistency timestamps are out of order")
    return fields


def build_manifest(args: argparse.Namespace, components: list[tuple[str, Path]]) -> dict:
    if args.recovery_point_class not in {"intraday", "daily", "monthly"}:
        raise BackupError("recovery point class must be intraday, daily, or monthly")
    created = args.created_utc or utc_now()
    parse_utc(created)
    age_version = check_age()
    component_data = []
    for name, path in sorted(components):
        digest, size = sha256_file(path)
        component_data.append({"name": name, "sha256": digest, "size": size})
    return {
        "schema_version": SCHEMA_VERSION,
        "format": FORMAT,
        "backup_created_utc": created,
        "recovery_point_class": args.recovery_point_class,
        "source": source_identity(args),
        "encryption": {"tool": "age", "version": age_version, "mode": "recipient-file"},
        "consistency": consistency_metadata(args, created),
        "components": component_data,
    }


def validate_manifest(data: object, outer: bool) -> dict:
    if not isinstance(data, dict):
        raise BackupError("backup manifest must be an object")
    common = {"schema_version", "format", "backup_created_utc", "recovery_point_class", "source", "encryption", "consistency", "components"}
    expected_keys = common | ({"encrypted_archive"} if outer else set())
    if set(data) != expected_keys:
        raise BackupError("backup manifest schema is incomplete or contains unknown fields")
    if data["schema_version"] != SCHEMA_VERSION or data["format"] != FORMAT:
        raise BackupError("unsupported backup manifest version")
    if data["recovery_point_class"] not in {"intraday", "daily", "monthly"}:
        raise BackupError("invalid recovery point class")
    created = parse_utc(data["backup_created_utc"])
    source = data["source"]
    if not isinstance(source, dict) or set(source) != {"instance_slug", "database_name", "environment_id", "product_version", "release_sha"}:
        raise BackupError("backup source identity is incomplete")
    if any(not isinstance(value, str) or not value.strip() for value in source.values()):
        raise BackupError("backup source identity contains an empty value")
    if not RELEASE_SHA_RE.fullmatch(source["release_sha"]):
        raise BackupError("backup source release SHA is invalid")
    encryption = data["encryption"]
    if not isinstance(encryption, dict) or set(encryption) != {"tool", "version", "mode"}:
        raise BackupError("backup encryption metadata is incomplete")
    if encryption["tool"] != "age" or encryption["mode"] != "recipient-file" or not AGE_VERSION_RE.fullmatch(str(encryption["version"])):
        raise BackupError("backup encryption metadata is invalid")
    consistency = data["consistency"]
    consistency_keys = {"method", "quiesce_start_utc", "database_snapshot_utc", "filestore_snapshot_utc", "quiesce_end_utc"}
    if not isinstance(consistency, dict) or set(consistency) != consistency_keys or consistency["method"] != CONSISTENCY_METHOD:
        raise BackupError("backup consistency metadata is incomplete")
    stamps = [parse_utc(consistency[key]) for key in (
        "quiesce_start_utc",
        "database_snapshot_utc",
        "filestore_snapshot_utc",
        "quiesce_end_utc",
    )]
    if stamps != sorted(stamps) or created < stamps[-1]:
        raise BackupError("backup consistency timestamps are invalid")
    components = data["components"]
    if not isinstance(components, list) or not components:
        raise BackupError("backup manifest has no components")
    names = []
    for component in components:
        if not isinstance(component, dict) or set(component) != {"name", "sha256", "size"}:
            raise BackupError("backup component manifest entry is invalid")
        name = component["name"]
        if not safe_name(name) or name not in ALLOWED_COMPONENTS:
            raise BackupError(f"unknown backup component: {name}")
        if name in names or not SHA256_RE.fullmatch(str(component["sha256"])):
            raise BackupError("backup component names or checksums are invalid")
        if not isinstance(component["size"], int) or isinstance(component["size"], bool) or component["size"] < 0:
            raise BackupError("backup component size is invalid")
        names.append(name)
    if not REQUIRED_COMPONENTS.issubset(names):
        raise BackupError("required backup components are missing")
    if outer:
        archive = data["encrypted_archive"]
        if not isinstance(archive, dict) or set(archive) != {"name", "sha256", "size"} or not safe_name(archive["name"]):
            raise BackupError("encrypted archive metadata is invalid")
        if not archive["name"].endswith(".tar.age") or not SHA256_RE.fullmatch(str(archive["sha256"])):
            raise BackupError("encrypted archive metadata is invalid")
        if not isinstance(archive["size"], int) or archive["size"] < 1:
            raise BackupError("encrypted archive size is invalid")
    return data


def read_manifest(path: Path, outer: bool = True) -> dict:
    try:
        data = json.loads(require_file(path, "backup manifest").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackupError("backup manifest is not valid JSON") from exc
    return validate_manifest(data, outer=outer)


def atomic_publish(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        raise BackupError(f"refusing to overwrite existing recovery artifact: {target.name}")
    try:
        os.link(source, target)
        source.unlink()
    except OSError as exc:
        raise BackupError(f"atomic recovery artifact publication failed: {target.name}") from exc
    fsync_directory(target.parent)


def pack(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    manifest_path = Path(args.manifest_output or f"{output}.manifest.json").resolve()
    checksum_path = Path(args.checksum_output or f"{output}.sha256").resolve()
    if manifest_path != Path(f"{output}.manifest.json") or checksum_path != Path(f"{output}.sha256"):
        raise BackupError("custom manifest/checksum paths are unsupported; use the archive sidecar contract")
    recipient = require_file(Path(args.recipient_file).resolve(), "age recipient file")
    final_paths = {output, manifest_path, checksum_path, recipient}
    if len(final_paths) != 4:
        raise BackupError("recovery output paths must not alias recipient or sidecars")
    components = [component_spec(raw) for raw in args.component]
    names = [name for name, _ in components]
    if len(names) != len(set(names)):
        raise BackupError("duplicate recovery component name")
    if not REQUIRED_COMPONENTS.issubset(names) or not set(names).issubset(ALLOWED_COMPONENTS):
        raise BackupError("recovery components do not match the exact allowlist")
    if any(path in final_paths for _, path in components):
        raise BackupError("recovery output paths must not alias input components")
    output.parent.mkdir(parents=True, exist_ok=True)
    if any(path.exists() or path.is_symlink() for path in (output, manifest_path, checksum_path)):
        raise BackupError("recovery point already exists; refusing overwrite")
    stage = Path(tempfile.mkdtemp(prefix=".pmqms-recovery-stage-", dir=output.parent))
    published: list[Path] = []
    try:
        manifest = build_manifest(args, components)
        inner_manifest = stage / "manifest.json"
        write_json(inner_manifest, manifest)
        payload = stage / "payload.tar"
        with tarfile.open(payload, "w") as archive:
            for name, source in [("manifest.json", inner_manifest), *sorted(components)]:
                info = tarfile.TarInfo(name)
                info.size = source.stat().st_size
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                with source.open("rb") as handle:
                    archive.addfile(info, handle)
        fsync_file(payload)
        encrypted = stage / output.name
        try:
            subprocess.run([age_binary(), "-R", str(recipient), "-o", str(encrypted), str(payload)], check=True, capture_output=True, text=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise BackupError("authenticated backup encryption failed") from exc
        require_file(encrypted, "encrypted backup")
        digest, size = sha256_file(encrypted)
        outer = dict(manifest)
        outer["encrypted_archive"] = {"name": output.name, "sha256": digest, "size": size}
        staged_manifest = stage / manifest_path.name
        staged_checksum = stage / checksum_path.name
        write_json(staged_manifest, outer)
        staged_checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
        fsync_file(staged_checksum)
        atomic_publish(encrypted, output); published.append(output)
        atomic_publish(staged_manifest, manifest_path); published.append(manifest_path)
        atomic_publish(staged_checksum, checksum_path); published.append(checksum_path)
        print(json.dumps({"backup": str(output), "manifest": str(manifest_path), "sha256": digest}, sort_keys=True))
        return 0
    except BackupError:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def verify_outer(archive: Path, manifest_path: Path, checksum_path: Path) -> dict:
    manifest = read_manifest(manifest_path, outer=True)
    require_file(archive, "encrypted backup")
    require_file(checksum_path, "backup checksum")
    if manifest["encrypted_archive"]["name"] != archive.name:
        raise BackupError("manifest archive name does not match the selected archive")
    if manifest_path.name != f"{archive.name}.manifest.json" or checksum_path.name != f"{archive.name}.sha256":
        raise BackupError("backup sidecars do not match the archive naming contract")
    checksum_parts = checksum_path.read_text(encoding="utf-8").split()
    if len(checksum_parts) != 2 or checksum_parts[1] != archive.name or not SHA256_RE.fullmatch(checksum_parts[0]):
        raise BackupError("backup checksum sidecar is malformed")
    actual, size = sha256_file(archive)
    if checksum_parts[0] != actual or manifest["encrypted_archive"]["sha256"] != actual or manifest["encrypted_archive"]["size"] != size:
        raise BackupError("encrypted backup checksum failed")
    return manifest


def decrypt_to(archive: Path, identity: Path, destination: Path) -> None:
    require_file(identity.resolve(), "age identity file")
    check_age()
    try:
        subprocess.run([age_binary(), "-d", "-i", str(identity.resolve()), "-o", str(destination), str(archive)], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupError("authenticated backup decryption failed") from exc


def validate_payload(plaintext: Path, outer_manifest: dict, destination: Path) -> None:
    with tarfile.open(plaintext, "r:") as payload:
        members = payload.getmembers()
        names = [member.name for member in members]
        if len(names) != len(set(names)):
            raise BackupError("backup payload contains duplicate member names")
        if not all(safe_name(name) for name in names):
            raise BackupError("backup payload contains an unsafe member name")
        member_by_name = {member.name: member for member in members}
        if "manifest.json" not in member_by_name or any(name not in {"manifest.json"} | ALLOWED_COMPONENTS for name in names):
            raise BackupError("backup payload contains an unexpected member")
        if any(not member.isreg() or member.size < 0 for member in members):
            raise BackupError("backup payload contains a non-regular member")
        manifest_member = member_by_name["manifest.json"]
        handle = payload.extractfile(manifest_member)
        if handle is None:
            raise BackupError("backup payload manifest cannot be read")
        inner_bytes = handle.read()
        try:
            inner = json.loads(inner_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BackupError("inner backup manifest is invalid") from exc
        validate_manifest(inner, outer=False)
        expected_inner = {key: value for key, value in outer_manifest.items() if key != "encrypted_archive"}
        if inner != expected_inner:
            raise BackupError("inner and outer backup manifests differ")
        expected_names = {"manifest.json"} | {item["name"] for item in outer_manifest["components"]}
        if set(names) != expected_names or len(names) != len(expected_names):
            raise BackupError("backup payload members do not match the manifest exactly")
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "manifest.json").write_bytes(inner_bytes)
        fsync_file(destination / "manifest.json")
        for component in outer_manifest["components"]:
            name = component["name"]
            member = member_by_name[name]
            source = payload.extractfile(member)
            if source is None:
                raise BackupError(f"backup component cannot be read: {name}")
            temporary = destination / f".{name}.part"
            digest = hashlib.sha256()
            size = 0
            try:
                with temporary.open("wb") as target:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(block)
                        size += len(block)
                        target.write(block)
                    target.flush()
                    os.fsync(target.fileno())
                if size != member.size or size != component["size"] or digest.hexdigest() != component["sha256"]:
                    raise BackupError(f"backup component checksum or size failed: {name}")
                os.replace(temporary, destination / name)
            finally:
                temporary.unlink(missing_ok=True)


def check_expected_source(manifest: dict, args: argparse.Namespace) -> None:
    expected = {
        "instance_slug": args.expected_instance,
        "database_name": args.expected_database,
        "environment_id": args.expected_environment_id,
    }
    for key, value in expected.items():
        if value is not None and manifest["source"][key] != value:
            raise BackupError(f"recovery source identity mismatch: {key}")


def unpack(args: argparse.Namespace) -> int:
    archive = Path(args.archive).resolve()
    manifest_path = Path(args.manifest or f"{archive}.manifest.json").resolve()
    checksum_path = Path(args.checksum or f"{archive}.sha256").resolve()
    manifest = verify_outer(archive, manifest_path, checksum_path)
    check_expected_source(manifest, args)
    destination = Path(args.output).resolve()
    if destination.is_symlink() or (destination.exists() and any(destination.iterdir())):
        raise BackupError("restore output must be a new or empty directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".pmqms-restore-stage-", dir=destination.parent))
    try:
        with tempfile.TemporaryDirectory(prefix="pmqms-decrypt-") as work:
            plaintext = Path(work) / "payload.tar"
            decrypt_to(archive, Path(args.identity_file), plaintext)
            validate_payload(plaintext, manifest, stage)
        destination.mkdir(parents=True, exist_ok=True)
        for path in stage.iterdir():
            os.replace(path, destination / path.name)
        print(json.dumps({"restore_payload": str(destination), "source": manifest["source"]}, sort_keys=True))
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def deep_verify(args: argparse.Namespace, manifest: dict) -> None:
    with tempfile.TemporaryDirectory(prefix="pmqms-deep-verify-") as root:
        root_path = Path(root)
        plaintext = root_path / "payload.tar"
        destination = root_path / "payload"
        decrypt_to(Path(args.archive).resolve(), Path(args.identity_file), plaintext)
        validate_payload(plaintext, manifest, destination)
        check_expected_source(manifest, args)


def verify(args: argparse.Namespace) -> int:
    archive = Path(args.archive).resolve()
    manifest = verify_outer(archive, Path(args.manifest or f"{archive}.manifest.json").resolve(), Path(args.checksum or f"{archive}.sha256").resolve())
    if args.identity_file:
        deep_verify(args, manifest)
        print("backup_verification=deep-pass")
    else:
        print("backup_verification=shallow-pass")
    return 0


def transfer(args: argparse.Namespace) -> int:
    source_archive = Path(args.archive).resolve()
    source_manifest = Path(args.manifest or f"{source_archive}.manifest.json").resolve()
    source_checksum = Path(args.checksum or f"{source_archive}.sha256").resolve()
    verify_outer(source_archive, source_manifest, source_checksum)
    destination = Path(args.destination).resolve()
    if destination == source_archive.parent:
        raise BackupError("off-host destination must be distinct from the backup source directory")
    destination.mkdir(parents=True, exist_ok=True)
    copies = [source_archive, source_manifest, source_checksum]
    targets = [destination / path.name for path in copies]
    existing = [target for target in targets if target.exists() or target.is_symlink()]
    for source, target in zip(copies, targets):
        if target.is_symlink() or (target.exists() and sha256_file(source)[0] != sha256_file(target)[0]):
            raise BackupError(f"off-host destination contains a different artifact: {target.name}")
    if len(existing) == len(targets):
        print(json.dumps({"destination": str(destination), "idempotent": True, "files": sorted(path.name for path in copies)}, sort_keys=True))
        return 0
    stage = Path(tempfile.mkdtemp(prefix=".pmqms-transfer-stage-", dir=destination))
    published: list[Path] = []
    try:
        for source in copies:
            target = stage / source.name
            shutil.copy2(source, target)
            if sha256_file(source)[0] != sha256_file(target)[0]:
                raise BackupError(f"off-host transfer checksum failed: {source.name}")
            fsync_file(target)
        for source in copies:
            target = destination / source.name
            if target.exists() or target.is_symlink():
                continue
            atomic_publish(stage / source.name, target)
            published.append(target)
        print(json.dumps({"destination": str(destination), "idempotent": False, "files": sorted(path.name for path in copies)}, sort_keys=True))
        return 0
    except BackupError:
        for path in reversed(published):
            path.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def retention_deadline(created: datetime, point_class: str) -> datetime:
    if point_class == "intraday":
        return created + timedelta(days=7)
    if point_class == "daily":
        return created + timedelta(days=30)
    return add_months(created, 12)


def retention(args: argparse.Namespace) -> int:
    directory = Path(args.directory).resolve()
    if not directory.is_dir() or directory == Path(directory.anchor) or not (directory / RECOVERY_MARKER).is_file():
        raise BackupError("retention target must be an explicit recovery repository")
    now = parse_utc(args.now or utc_now())
    records = []
    decisions = []
    for manifest_path in sorted(directory.glob("*.manifest.json")):
        try:
            manifest = read_manifest(manifest_path, outer=True)
            archive_name = manifest["encrypted_archive"]["name"]
            archive = directory / archive_name
            checksum = directory / f"{archive_name}.sha256"
            if manifest_path.name != f"{archive_name}.manifest.json" or archive.parent != directory or checksum.parent != directory:
                raise BackupError("retention artifact naming contract failed")
            verify_outer(archive, manifest_path, checksum)
            created = parse_utc(manifest["backup_created_utc"])
            if created > now:
                raise BackupError("future-dated recovery point")
            source = tuple(manifest["source"][key] for key in ("instance_slug", "database_name", "environment_id"))
            records.append((manifest_path, archive, checksum, manifest, source, created))
        except BackupError as exc:
            decisions.append({"manifest": manifest_path.name, "action": "skip", "reason": str(exc)})
    newest_by_source = {}
    for record in records:
        current = newest_by_source.get(record[4])
        if current is None or (record[5], record[0].name) > (current[5], current[0].name):
            newest_by_source[record[4]] = record
    delete_count = 0
    for manifest_path, archive, checksum, manifest, source, created in records:
        keep = manifest_path == newest_by_source[source][0] or now <= retention_deadline(created, manifest["recovery_point_class"])
        action = "keep" if keep else "delete"
        if action == "delete" and args.apply:
            for path in (manifest_path, archive, checksum):
                if not path.is_file() or path.is_symlink() or path.parent != directory:
                    raise BackupError(f"retention artifact is not safe to delete: {path.name}")
                delete_count += 1
                failure_after = os.environ.get("PMQMS_RETENTION_FAIL_AFTER")
                if failure_after and delete_count > int(failure_after):
                    raise BackupError("simulated retention deletion failure")
                path.unlink()
        decisions.append({"manifest": manifest_path.name, "class": manifest["recovery_point_class"], "source": source[0], "age_seconds": int((now - created).total_seconds()), "action": action})
    print(json.dumps({"directory": str(directory), "dry_run": not args.apply, "decisions": decisions}, sort_keys=True))
    return 0


def common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--archive")
    parser.add_argument("--manifest")
    parser.add_argument("--checksum")
    parser.add_argument("--expected-instance")
    parser.add_argument("--expected-database")
    parser.add_argument("--expected-environment-id")
    return parser


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    pack_parser = sub.add_parser("pack")
    pack_parser.add_argument("--output", required=True)
    pack_parser.add_argument("--manifest-output")
    pack_parser.add_argument("--checksum-output")
    pack_parser.add_argument("--recipient-file", required=True)
    pack_parser.add_argument("--source-instance", required=True)
    pack_parser.add_argument("--source-database", required=True)
    pack_parser.add_argument("--source-environment-id", required=True)
    pack_parser.add_argument("--product-version", required=True)
    pack_parser.add_argument("--source-release-sha", required=True)
    pack_parser.add_argument("--recovery-point-class", default="daily")
    pack_parser.add_argument("--created-utc")
    pack_parser.add_argument("--consistency-method", default=CONSISTENCY_METHOD)
    pack_parser.add_argument("--quiesce-start-utc")
    pack_parser.add_argument("--database-snapshot-utc")
    pack_parser.add_argument("--filestore-snapshot-utc")
    pack_parser.add_argument("--quiesce-end-utc")
    pack_parser.add_argument("--component", action="append", default=[])
    verify_parser = sub.add_parser("verify", parents=[common_parser()])
    verify_parser.add_argument("--identity-file")
    unpack_parser = sub.add_parser("unpack", parents=[common_parser()])
    unpack_parser.add_argument("--identity-file", required=True)
    unpack_parser.add_argument("--output", required=True)
    transfer_parser = sub.add_parser("transfer", parents=[common_parser()])
    transfer_parser.add_argument("--destination", required=True)
    retention_parser = sub.add_parser("retention")
    retention_parser.add_argument("--directory", required=True)
    retention_parser.add_argument("--now")
    retention_parser.add_argument("--apply", action="store_true")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "pack":
            return pack(args)
        if args.command == "unpack":
            return unpack(args)
        if args.command == "verify":
            return verify(args)
        if args.command == "transfer":
            return transfer(args)
        if args.command == "retention":
            return retention(args)
        raise BackupError("unknown backup command")
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
