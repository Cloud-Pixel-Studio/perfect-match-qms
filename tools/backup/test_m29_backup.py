import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.backup import m29_backup


class M29BackupToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pmqms-m29-test-")
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        for name, content in {
            "db.dump": b"fictional database\n",
            "filestore.tar.gz": b"fictional filestore\n",
            "environment_id": b"fictional-environment-id\n",
            "runtime-lock.json": b'{"schema_version":1}\n',
            "deployment-manifest.json": b'{"instance_slug":"fictional-test"}\n',
        }.items():
            (self.source / name).write_bytes(content)
        self.recipient = self.root / "recipient.age"
        self.identity = self.root / "identity.age"
        self.recipient.write_text("fictional-recipient\n")
        self.identity.write_text("fictional-identity\n")
        self.age = self.root / "age-fake.py"
        self.age.write_text(
            """#!/usr/bin/env python3
import shutil, sys
from pathlib import Path
if sys.argv[1] == '--version':
    print('age 1.2.1')
elif sys.argv[1] == '-R':
    shutil.copyfile(sys.argv[-1], sys.argv[sys.argv.index('-o') + 1])
elif sys.argv[1] == '-d':
    identity = Path(sys.argv[sys.argv.index('-i') + 1]).read_text()
    if 'wrong' in identity:
        raise SystemExit(3)
    shutil.copyfile(sys.argv[-1], sys.argv[sys.argv.index('-o') + 1])
else:
    raise SystemExit(2)
"""
        )
        self.age.chmod(self.age.stat().st_mode | stat.S_IEXEC)
        self.env = {**os.environ, "PMQMS_AGE_BIN": sys.executable, "PMQMS_AGE_VERSION": "1.2.1"}
        # The fake is invoked through Python, so its version is supplied by a wrapper below.
        self.wrapper = self.root / "age-wrapper.py"
        self.wrapper.write_text(
            """#!/usr/bin/env python3
import runpy, sys
if sys.argv[1] == '--version': print('age 1.2.1')
else: runpy.run_path(sys.argv[0].replace('age-wrapper.py', 'age-fake.py'), run_name='__main__')
"""
        )
        self.wrapper.chmod(self.wrapper.stat().st_mode | stat.S_IEXEC)
        if os.name == "nt":
            self.wrapper = self.root / "age-wrapper.cmd"
            self.wrapper.write_text(
                '@py -3 "%~dp0age-fake.py" %*\n',
                encoding="utf-8",
            )
        self.env["PMQMS_AGE_BIN"] = str(self.wrapper)

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(m29_backup.__file__), *args], env=self.env, text=True, capture_output=True)

    def pack(self, stamp="2026-09-01T12:00:00Z", name="backup.tar.age", point_class="daily"):
        archive = self.root / name
        args = [
            "pack", "--output", str(archive), "--recipient-file", str(self.recipient),
            "--source-instance", "fictional-test", "--source-database", "pmqms_fictional",
            "--source-environment-id", "fictional-environment-id", "--product-version", "test",
            "--source-release-sha", "f" * 40, "--recovery-point-class", point_class,
            "--created-utc", stamp,
        ]
        component_names = ("db.dump", "filestore.tar.gz", "environment_id", "runtime-lock.json", "deployment-manifest.json")
        if (self.source / "product-manifest.json").exists():
            component_names += ("product-manifest.json",)
        for name in component_names:
            args += ["--component", f"{name}={self.source / name}"]
        result = self.run_tool(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return archive

    def test_pack_manifest_checksums_and_disposable_restore(self):
        archive = self.pack()
        manifest = json.loads(Path(f"{archive}.manifest.json").read_text())
        self.assertEqual(manifest["format"], "pmqms-recovery-point-v1")
        self.assertEqual({item["name"] for item in manifest["components"]}, {"db.dump", "filestore.tar.gz", "environment_id", "runtime-lock.json", "deployment-manifest.json"})
        output = self.root / "recovery"
        result = self.run_tool("unpack", "--archive", str(archive), "--identity-file", str(self.identity), "--output", str(output))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((output / "db.dump").read_bytes(), b"fictional database\n")
        self.assertFalse(any(path.name.startswith("recipient") for path in output.iterdir()))

    def test_product_manifest_is_allowed_for_new_backups(self):
        (self.source / "product-manifest.json").write_text(
            '{"product_version":"v1.0.0-rc1","source_sha":"' + "f" * 40 + '"}\n',
            encoding="utf-8",
        )
        archive = self.pack(name="with-product-manifest.tar.age")
        manifest = json.loads(Path(f"{archive}.manifest.json").read_text())
        self.assertIn("product-manifest.json", {item["name"] for item in manifest["components"]})

    def test_manifest_is_deterministic_for_same_recovery_point(self):
        first = self.pack("2026-09-01T12:00:00Z", "first.tar.age")
        second = self.pack("2026-09-01T12:00:00Z", "second.tar.age")
        first_manifest = json.loads(Path(f"{first}.manifest.json").read_text())
        second_manifest = json.loads(Path(f"{second}.manifest.json").read_text())
        self.assertEqual(first_manifest["components"], second_manifest["components"])
        self.assertEqual(first_manifest["source"], second_manifest["source"])
        self.assertEqual(first_manifest["backup_created_utc"], second_manifest["backup_created_utc"])

    def test_wrong_key_and_corruption_fail_closed(self):
        archive = self.pack()
        wrong = self.root / "wrong.age"
        wrong.write_text("wrong\n")
        result = self.run_tool("unpack", "--archive", str(archive), "--identity-file", str(wrong), "--output", str(self.root / "wrong-out"))
        self.assertEqual(result.returncode, 2)
        archive.write_bytes(archive.read_bytes() + b"corrupt")
        result = self.run_tool("verify", "--archive", str(archive))
        self.assertEqual(result.returncode, 2)

    def test_missing_key_and_missing_component_fail_closed(self):
        archive = self.pack()
        result = self.run_tool("unpack", "--archive", str(archive), "--identity-file", str(self.root / "missing.age"), "--output", str(self.root / "missing-out"))
        self.assertEqual(result.returncode, 2)

    def test_sensitive_component_rejected(self):
        result = self.run_tool(
            "pack", "--output", str(self.root / "sensitive.tar.age"), "--recipient-file", str(self.recipient),
            "--source-instance", "fictional-test", "--source-database", "pmqms_fictional",
            "--source-environment-id", "fictional-environment-id", "--product-version", "test",
            "--source-release-sha", "f" * 40,
            "--component", f"db.dump={self.source / 'db.dump'}",
            "--component", f"secret.txt={self.source / 'db.dump'}",
            "--component", f"filestore.tar.gz={self.source / 'filestore.tar.gz'}",
            "--component", f"environment_id={self.source / 'environment_id'}",
            "--component", f"runtime-lock.json={self.source / 'runtime-lock.json'}",
            "--component", f"deployment-manifest.json={self.source / 'deployment-manifest.json'}",
        )
        self.assertEqual(result.returncode, 2)
        (self.source / "filestore.tar.gz").unlink()
        result = self.run_tool(
            "pack", "--output", str(self.root / "missing.tar.age"), "--recipient-file", str(self.recipient),
            "--source-instance", "fictional-test", "--source-database", "pmqms_fictional",
            "--source-environment-id", "fictional-environment-id", "--product-version", "test",
            "--source-release-sha", "f" * 40, *sum((["--component", f"{name}={self.source / name}"] for name in ("db.dump", "filestore.tar.gz", "environment_id", "runtime-lock.json", "deployment-manifest.json")), []),
        )
        self.assertEqual(result.returncode, 2)

    def test_transfer_and_partial_transfer_detection(self):
        archive = self.pack()
        target = self.root / "off-host"
        result = self.run_tool("transfer", "--archive", str(archive), "--destination", str(target))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_tool("transfer", "--archive", str(archive), "--destination", str(target))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"idempotent": true', result.stdout)
        (target / archive.name).write_bytes(b"partial")
        result = self.run_tool("verify", "--archive", str(target / archive.name))
        self.assertEqual(result.returncode, 2)

    def test_version_pin_collision_and_consistency_fail_closed(self):
        component_args = sum(
            (["--component", f"{name}={self.source / name}"] for name in (
                "db.dump", "filestore.tar.gz", "environment_id", "runtime-lock.json", "deployment-manifest.json"
            )),
            [],
        )
        self.env["PMQMS_AGE_VERSION"] = "1.2.10"
        result = self.run_tool(
            "pack", "--output", str(self.root / "wrong-version.tar.age"), "--recipient-file", str(self.recipient),
            "--source-instance", "fictional-test", "--source-database", "pmqms_fictional",
            "--source-environment-id", "fictional-environment-id", "--product-version", "test",
            "--source-release-sha", "f" * 40, *component_args,
        )
        self.assertEqual(result.returncode, 2)
        self.env["PMQMS_AGE_VERSION"] = "1.2.1"
        archive = self.pack()
        result = self.run_tool(
            "pack", "--output", str(archive), "--recipient-file", str(self.recipient),
            "--source-instance", "fictional-test", "--source-database", "pmqms_fictional",
            "--source-environment-id", "fictional-environment-id", "--product-version", "test",
            "--source-release-sha", "f" * 40, *component_args,
        )
        self.assertEqual(result.returncode, 2)
        manifest = json.loads(Path(f"{archive}.manifest.json").read_text())
        manifest["consistency"]["database_snapshot_utc"] = "2026-09-01T11:00:00Z"
        Path(f"{archive}.manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = self.run_tool("verify", "--archive", str(archive))
        self.assertEqual(result.returncode, 2)

    def test_retention_calendar_and_failure_injection(self):
        self.assertEqual(
            m29_backup.add_months(m29_backup.parse_utc("2024-02-29T12:00:00Z"), 12).date().isoformat(),
            "2025-02-28",
        )
        retention_dir = self.root / "failure-retention"
        retention_dir.mkdir()
        (retention_dir / m29_backup.RECOVERY_MARKER).touch()
        old = self.pack("2026-08-01T12:00:00Z", "failure-old.tar.age", "intraday")
        for suffix in (".manifest.json", ".sha256"):
            Path(f"{old}{suffix}").replace(retention_dir / f"{old.name}{suffix}")
        old.replace(retention_dir / old.name)
        newest = self.pack("2026-09-01T12:00:00Z", "failure-new.tar.age", "daily")
        for suffix in (".manifest.json", ".sha256"):
            Path(f"{newest}{suffix}").replace(retention_dir / f"{newest.name}{suffix}")
        newest.replace(retention_dir / newest.name)
        env = {**self.env, "PMQMS_RETENTION_FAIL_AFTER": "0"}
        result = subprocess.run(
            [sys.executable, str(m29_backup.__file__), "retention", "--directory", str(retention_dir),
             "--now", "2026-09-02T12:00:00Z", "--apply"],
            env=env, text=True, capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertTrue((retention_dir / old.name).exists())

    def test_retention_dry_run_apply_and_newest_protection(self):
        retention_dir = self.root / "retention"
        retention_dir.mkdir()
        (retention_dir / m29_backup.RECOVERY_MARKER).touch()
        old = self.pack("2026-08-01T12:00:00Z", "old.tar.age", "intraday")
        new = self.pack("2026-09-01T12:00:00Z", "new.tar.age", "daily")
        for archive in (old, new):
            for suffix in (".manifest.json", ".sha256"):
                Path(f"{archive}{suffix}").replace(retention_dir / f"{archive.name}{suffix}")
            archive.replace(retention_dir / archive.name)
        result = self.run_tool("retention", "--directory", str(retention_dir), "--now", "2026-09-02T12:00:00Z")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"action": "delete"', result.stdout)
        self.assertTrue((retention_dir / "new.tar.age").exists())
        result = self.run_tool("retention", "--directory", str(retention_dir), "--now", "2026-09-02T12:00:00Z", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((retention_dir / "old.tar.age").exists())
        self.assertTrue((retention_dir / "new.tar.age").exists())


if __name__ == "__main__":
    unittest.main()
