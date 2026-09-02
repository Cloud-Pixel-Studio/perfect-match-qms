#!/usr/bin/env python3
"""Build and validate encrypted, manifest-driven QMS recovery points.

The archive contains only the database dump, filestore archive, identity,
non-secret runtime metadata, and signed license reference. Encryption is
delegated to a pinned age binary supplied by the operator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

FORMAT = "pmqms-recovery-point-v1"
DEFAULT_AGE_VERSION = "1.2.1"
RETENTION_DAYS = {"intraday": 7, "daily": 30, "monthly": 366}
ALLOWED_CLASSES = set(RETENTION_DAYS)
REJECTED_COMPONENT_NAMES = {
    "password",
    "credentials",
    "secret",
    "token",
    "private-key",
    "private_key",
    "identity",
    "recipient",
}


class BackupError(RuntimeError):
    """A safe, operator-actionable backup error."""


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
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
    return os.environ.get("PMQMS_AGE_VERSION", DEFAULT_AGE_VERSION)


def check_age() -> None:
    try:
        result = subprocess.run(
            [age_binary(), "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupError("pinned age tool is unavailable or failed version check") from exc
    version = (result.stdout or result.stderr).strip()
    if expected_age_version() not in version:
        raise BackupError("age tool version does not match the pinned M29.1 version")


def require_file(path: Path, label: str) -> Path:
    if not path.is_file() or not os.access(path, os.R_OK):
        raise BackupError(f"required {label} is missing or unreadable")
    return path


def canonical_manifest(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def component_spec(raw: str) -> tuple[str, Path]:
    name, separator, value = raw.partition("=")
    if not separator or not name or not value or Path(name).name != name:
        raise BackupError("components must use NAME=PATH with a plain component name")
    normalized = name.lower().replace("_", "-")
    if any(term in normalized for term in REJECTED_COMPONENT_NAMES):
        raise BackupError(f"sensitive component is not allowed in recovery payload: {name}")
    return name, require_file(Path(value), f"component {name}")


def build_manifest(args: argparse.Namespace, components: list[tuple[str, Path]]) -> dict:
    if args.recovery_point_class not in ALLOWED_CLASSES:
        raise BackupError("recovery point class must be intraday, daily, or monthly")
    component_data = []
    for name, path in sorted(components):
        digest, size = sha256_file(path)
        component_data.append({"name": name, "sha256": digest, "size": size})
    return {
        "schema_version": 1,
        "format": FORMAT,
        "backup_created_utc": args.created_utc or utc_now(),
        "recovery_point_class": args.recovery_point_class,
        "source": {
            "instance_slug": args.source_instance,
            "database_name": args.source_database,
            "environment_id": args.source_environment_id,
            "product_version": args.product_version,
            "release_sha": args.source_release_sha,
        },
        "components": component_data,
    }


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_manifest(data))


def pack(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    manifest_path = Path(args.manifest_output or f"{output}.manifest.json").resolve()
    checksum_path = Path(args.checksum_output or f"{output}.sha256").resolve()
    recipient = require_file(Path(args.recipient_file), "age recipient file")
    if output == recipient or manifest_path == recipient or checksum_path == recipient:
        raise BackupError("encryption recipient must remain outside backup outputs")
    components = [component_spec(raw) for raw in args.component]
    names = {name for name, _ in components}
    required = {"db.dump", "filestore.tar.gz", "environment_id", "runtime-lock.json", "deployment-manifest.json"}
    missing = required - names
    if missing:
        raise BackupError(f"required recovery components missing: {', '.join(sorted(missing))}")
    manifest = build_manifest(args, components)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pmqms-recovery-") as work:
        work_path = Path(work)
        inner_manifest = work_path / "manifest.json"
        write_json(inner_manifest, manifest)
        with tarfile.open(work_path / "payload.tar", "w") as archive:
            for name, source in [("manifest.json", inner_manifest), *components]:
                info = tarfile.TarInfo(name)
                info.size = source.stat().st_size
                info.mtime = 0
                info.uid = 0
                info.gid = 0
                info.uname = ""
                info.gname = ""
                with source.open("rb") as handle:
                    archive.addfile(info, handle)
        check_age()
        try:
            subprocess.run(
                [age_binary(), "-R", str(recipient), "-o", str(output), str(work_path / "payload.tar")],
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise BackupError("authenticated backup encryption failed") from exc
    if not output.is_file():
        raise BackupError("age did not produce the encrypted backup")
    digest, size = sha256_file(output)
    checksum_path.write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    outer = dict(manifest)
    outer["encrypted_archive"] = {"name": output.name, "sha256": digest, "size": size}
    write_json(manifest_path, outer)
    print(json.dumps({"backup": str(output), "manifest": str(manifest_path), "sha256": digest}, sort_keys=True))
    return 0


def read_manifest(path: Path) -> dict:
    try:
        data = json.loads(require_file(path, "backup manifest").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackupError("backup manifest is not valid JSON") from exc
    if data.get("schema_version") != 1 or data.get("format") != FORMAT:
        raise BackupError("unsupported backup manifest")
    if data.get("recovery_point_class") not in ALLOWED_CLASSES:
        raise BackupError("invalid recovery point class")
    parse_utc(data.get("backup_created_utc", ""))
    if not isinstance(data.get("components"), list):
        raise BackupError("backup manifest has no component list")
    return data


def verify_outer(archive: Path, manifest_path: Path, checksum_path: Path) -> dict:
    manifest = read_manifest(manifest_path)
    require_file(archive, "encrypted backup")
    require_file(checksum_path, "backup checksum")
    expected = checksum_path.read_text(encoding="utf-8").split()[0]
    actual, size = sha256_file(archive)
    if expected != actual:
        raise BackupError("encrypted backup checksum failed")
    recorded = manifest.get("encrypted_archive", {})
    if recorded.get("sha256") != actual or recorded.get("size") != size:
        raise BackupError("backup manifest does not match encrypted archive")
    return manifest


def decrypt_to(archive: Path, identity: Path, destination: Path) -> None:
    require_file(identity, "age identity file")
    check_age()
    try:
        subprocess.run(
            [age_binary(), "-d", "-i", str(identity), "-o", str(destination), str(archive)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BackupError("authenticated backup decryption failed") from exc


def unpack(args: argparse.Namespace) -> int:
    archive = Path(args.archive).resolve()
    manifest_path = Path(args.manifest or f"{archive}.manifest.json").resolve()
    checksum_path = Path(args.checksum or f"{archive}.sha256").resolve()
    manifest = verify_outer(archive, manifest_path, checksum_path)
    destination = Path(args.output).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise BackupError("restore output must be a new or empty directory")
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pmqms-decrypt-") as work:
        plaintext = Path(work) / "payload.tar"
        decrypt_to(archive, Path(args.identity_file), plaintext)
        try:
            with tarfile.open(plaintext, "r") as payload:
                members = payload.getmembers()
                if any(member.name.startswith("/") or ".." in Path(member.name).parts for member in members):
                    raise BackupError("backup contains an unsafe path")
                payload.extractall(destination, filter="data")
        except (OSError, tarfile.TarError) as exc:
            raise BackupError("decrypted backup payload is invalid") from exc
    inner = read_manifest(destination / "manifest.json")
    if inner != {key: manifest[key] for key in manifest if key != "encrypted_archive"}:
        raise BackupError("inner and outer backup manifests differ")
    files = {path.name: path for path in destination.iterdir() if path.is_file() and path.name != "manifest.json"}
    for component in manifest["components"]:
        path = files.get(component["name"])
        if not path:
            raise BackupError(f"decrypted component missing: {component['name']}")
        digest, size = sha256_file(path)
        if digest != component["sha256"] or size != component["size"]:
            raise BackupError(f"component checksum failed: {component['name']}")
    print(json.dumps({"restore_payload": str(destination), "source": manifest["source"]}, sort_keys=True))
    return 0


def transfer(args: argparse.Namespace) -> int:
    source_archive = Path(args.archive).resolve()
    source_manifest = Path(args.manifest or f"{source_archive}.manifest.json").resolve()
    source_checksum = Path(args.checksum or f"{source_archive}.sha256").resolve()
    verify_outer(source_archive, source_manifest, source_checksum)
    destination = Path(args.destination).resolve()
    if destination == source_archive.parent:
        raise BackupError("off-host destination must differ from backup source directory")
    destination.mkdir(parents=True, exist_ok=True)
    copies = [source_archive, source_manifest, source_checksum]
    for source in copies:
        target = destination / source.name
        shutil.copy2(source, target)
        if sha256_file(source)[0] != sha256_file(target)[0]:
            raise BackupError(f"off-host transfer checksum failed: {source.name}")
    print(json.dumps({"destination": str(destination), "files": sorted(path.name for path in copies)}, sort_keys=True))
    return 0


def retention(args: argparse.Namespace) -> int:
    directory = Path(args.directory).resolve()
    if not directory.is_dir() or directory == Path(directory.anchor):
        raise BackupError("retention target must be an existing non-root directory")
    now = parse_utc(args.now or utc_now())
    records = []
    decisions = []
    for manifest_path in sorted(directory.glob("*.manifest.json")):
        try:
            manifest = read_manifest(manifest_path)
            archive = directory / manifest["encrypted_archive"]["name"]
            checksum = Path(f"{archive}.sha256")
            verify_outer(archive, manifest_path, checksum)
            records.append((manifest_path, archive, checksum, manifest))
        except BackupError as exc:
            decisions.append({"manifest": manifest_path.name, "action": "skip", "reason": str(exc)})
    records.sort(key=lambda record: parse_utc(record[3]["backup_created_utc"]))
    newest = records[-1][0] if records else None
    for manifest_path, archive, checksum, manifest in records:
        created = parse_utc(manifest["backup_created_utc"])
        age_days = (now - created).total_seconds() / 86400
        keep = manifest_path == newest or age_days <= RETENTION_DAYS[manifest["recovery_point_class"]]
        action = "keep" if keep else "delete"
        if action == "delete" and args.apply:
            for path in (manifest_path, archive, checksum):
                path.unlink()
        decisions.append({"manifest": manifest_path.name, "class": manifest["recovery_point_class"], "age_days": round(age_days, 3), "action": action})
    print(json.dumps({"directory": str(directory), "dry_run": not args.apply, "decisions": decisions}, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--archive")
    common.add_argument("--manifest")
    common.add_argument("--checksum")
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
    pack_parser.add_argument("--component", action="append", default=[])
    for command in ("verify",):
        verify_parser = sub.add_parser(command, parents=[common])
        verify_parser.add_argument("--identity-file")
    unpack_parser = sub.add_parser("unpack", parents=[common])
    unpack_parser.add_argument("--identity-file", required=True)
    unpack_parser.add_argument("--output", required=True)
    transfer_parser = sub.add_parser("transfer", parents=[common])
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
        if args.command == "transfer":
            return transfer(args)
        if args.command == "retention":
            return retention(args)
        verify_outer(Path(args.archive).resolve(), Path(args.manifest or f"{args.archive}.manifest.json").resolve(), Path(args.checksum or f"{args.archive}.sha256").resolve())
        if args.identity_file:
            with tempfile.TemporaryDirectory(prefix="pmqms-verify-") as work:
                decrypt_to(Path(args.archive).resolve(), Path(args.identity_file), Path(work) / "payload.tar")
        print("backup_verification=pass")
        return 0
    except BackupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
