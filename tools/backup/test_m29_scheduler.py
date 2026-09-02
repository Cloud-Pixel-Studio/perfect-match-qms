#!/usr/bin/env python3
"""Focused M29.2 scheduler contract and failure-path tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from tools.backup import m29_scheduler as scheduler


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.recipient = root / "recipient.age"
        self.recipient.write_text("age1fictionalrecipient\n", encoding="utf-8")
        self.config_path = root / "config.json"
        self.raw_config = {
            "instance_slug": "fictional-customer",
            "instance_root": str(root / "instance"),
            "recipient_file": str(self.recipient),
            "local_staging_repository": str(root / "local"),
            "off_host_destination": str(root / "off-host"),
            "status_path": str(root / "status.json"),
            "monitoring_status_destination": str(root / "monitoring.json"),
            "timeout_seconds": 1800,
            "backup_cadence_minutes": 240,
            "max_jitter_seconds": 1800,
            "retention": dict(scheduler.RETENTION_POLICY),
            "release_sha": "a" * 40,
        }
        self.config_path.write_text(json.dumps(self.raw_config), encoding="utf-8")
        self.config = scheduler.load_config(self.config_path)

    def tearDown(self):
        self.temp.cleanup()

    def result(self, _config, tier, now):
        return scheduler.BackupResult(f"{tier}-20260902.tar.age", "a" * 64, scheduler.format_utc(now))

    def test_schedule_is_fixed_utc_and_below_rpo(self):
        semantics = scheduler.schedule_semantics()
        self.assertEqual(semantics["hours"], [0, 4, 8, 12, 16, 20])
        self.assertEqual(semantics["cadence_minutes"], 240)
        self.assertEqual(semantics["max_jitter_seconds"], 1800)
        self.assertEqual(semantics["maximum_interval_seconds"], 16200)
        self.assertTrue(semantics["maximum_interval_below_rpo"])
        self.assertEqual(scheduler.tier_schedule()["daily"], "00:45 UTC daily")
        self.assertEqual(scheduler.tier_schedule()["monthly"], "01:30 UTC on day 1")

    def test_utc_schedule_is_dst_independent(self):
        before = scheduler.next_scheduled_run(scheduler.parse_utc("2026-03-08T01:59:00Z"))
        after = scheduler.next_scheduled_run(scheduler.parse_utc("2026-11-01T01:59:00Z"))
        self.assertEqual(scheduler.format_utc(before), "2026-03-08T04:00:00Z")
        self.assertEqual(scheduler.format_utc(after), "2026-11-01T04:00:00Z")

    def test_success_writes_atomic_status_and_exact_boundary_is_healthy(self):
        now = scheduler.parse_utc("2026-09-02T00:00:00Z")
        self.assertEqual(scheduler.run_once(self.config, now=now, backup_runner=self.result, retention_runner=lambda *_: None), 0)
        status = json.loads(self.config.status_path.read_text(encoding="utf-8"))
        self.assertEqual(status["last_result"], "SUCCESS")
        self.assertEqual(status["consecutive_failures"], 0)
        self.assertEqual(status["off_host_verification"], "PASS")
        self.assertEqual(scheduler.health(self.config, now=now + timedelta(seconds=scheduler.RPO_SECONDS)), 0)
        self.assertEqual(scheduler.health(self.config, now=now + timedelta(seconds=scheduler.RPO_SECONDS + 1)), 1)
        self.assertFalse(list(self.config.status_path.parent.glob("*.part-*")))
        self.assertEqual(json.loads(self.config.monitoring_status_destination.read_text(encoding="utf-8")), status)

    def test_backup_failure_preserves_last_success_and_next_success_resets_counter(self):
        first = scheduler.parse_utc("2026-09-02T00:00:00Z")
        later = scheduler.parse_utc("2026-09-02T04:00:00Z")
        self.assertEqual(scheduler.run_once(self.config, now=first, backup_runner=self.result, retention_runner=lambda *_: None), 0)

        def failed(*_):
            raise scheduler.SchedulerError("simulated backup failure")

        self.assertEqual(scheduler.run_once(self.config, now=later, backup_runner=failed, retention_runner=lambda *_: self.fail("retention ran after failure")), 1)
        failed_status = json.loads(self.config.status_path.read_text(encoding="utf-8"))
        self.assertEqual(failed_status["last_successful_backup_utc"], scheduler.format_utc(first))
        self.assertEqual(failed_status["consecutive_failures"], 1)
        self.assertEqual(failed_status["retention_result"], "NOT_RUN")
        self.assertEqual(scheduler.health(self.config, now=later), 1)
        self.assertEqual(scheduler.run_once(self.config, now=later, backup_runner=self.result, retention_runner=lambda *_: None), 0)
        self.assertEqual(json.loads(self.config.status_path.read_text(encoding="utf-8"))["consecutive_failures"], 0)

    def test_retention_failure_is_nonzero_and_does_not_claim_success(self):
        def failed_retention(*_):
            raise scheduler.SchedulerError("simulated retention failure")

        now = scheduler.parse_utc("2026-09-02T00:00:00Z")
        self.assertEqual(scheduler.run_once(self.config, now=now, backup_runner=self.result, retention_runner=failed_retention), 1)
        status = json.loads(self.config.status_path.read_text(encoding="utf-8"))
        self.assertEqual(status["last_result"], "FAILURE")
        self.assertEqual(status["retention_result"], "FAILURE")
        self.assertIsNone(status["last_successful_backup_utc"])

    def test_malformed_result_is_rejected(self):
        now = scheduler.parse_utc("2026-09-02T00:00:00Z")
        malformed = lambda *_: scheduler.BackupResult("../../unsafe", "z" * 64, scheduler.format_utc(now))
        self.assertEqual(scheduler.run_once(self.config, now=now, backup_runner=malformed, retention_runner=lambda *_: self.fail()), 1)

    def test_locking_and_cross_instance_isolation(self):
        now = scheduler.parse_utc("2026-09-02T00:00:00Z")
        with scheduler.instance_lock(self.config):
            with self.assertRaises(scheduler.AlreadyRunning):
                scheduler.run_once(self.config, now=now, backup_runner=self.result, retention_runner=lambda *_: None)
        other_raw = dict(self.raw_config)
        other_raw.update({"instance_slug": "another-customer", "local_staging_repository": str(Path(self.temp.name) / "other-local"), "off_host_destination": str(Path(self.temp.name) / "other-off"), "status_path": str(Path(self.temp.name) / "other-status.json"), "monitoring_status_destination": str(Path(self.temp.name) / "other-monitoring.json")})
        other_path = Path(self.temp.name) / "other.json"
        other_path.write_text(json.dumps(other_raw), encoding="utf-8")
        other = scheduler.load_config(other_path)
        self.assertEqual(scheduler.run_once(self.config, now=now, backup_runner=self.result, retention_runner=lambda *_: None), 0)
        self.assertEqual(scheduler.run_once(other, now=now, backup_runner=self.result, retention_runner=lambda *_: None), 0)

    def test_config_fails_closed_for_missing_input_collision_and_secrets(self):
        missing = dict(self.raw_config)
        missing["recipient_file"] = str(Path(self.temp.name) / "missing.age")
        path = Path(self.temp.name) / "invalid.json"
        path.write_text(json.dumps(missing), encoding="utf-8")
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.load_config(path)
        collision = dict(self.raw_config)
        collision["off_host_destination"] = collision["local_staging_repository"]
        path.write_text(json.dumps(collision), encoding="utf-8")
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.load_config(path)
        secret = dict(self.raw_config)
        secret["private_identity"] = "/outside/identity.age"
        path.write_text(json.dumps(secret), encoding="utf-8")
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.load_config(path)

    def test_status_does_not_contain_secret_or_protected_path(self):
        now = scheduler.parse_utc("2026-09-02T00:00:00Z")
        self.assertEqual(scheduler.run_once(self.config, now=now, backup_runner=self.result, retention_runner=lambda *_: None), 0)
        status_text = self.config.status_path.read_text(encoding="utf-8")
        self.assertNotIn("identity", status_text.lower())
        self.assertNotIn("password", status_text.lower())
        self.assertNotIn(str(self.recipient), status_text)
        self.assertNotIn(str(self.config.instance_root), status_text)

    def test_status_collision_with_recipient_is_rejected(self):
        collision = dict(self.raw_config)
        collision["status_path"] = str(self.recipient)
        path = Path(self.temp.name) / "status-collision.json"
        path.write_text(json.dumps(collision), encoding="utf-8")
        with self.assertRaises(scheduler.SchedulerError):
            scheduler.load_config(path)

    def test_daily_and_monthly_runs_share_lock_and_write_tiered_points(self):
        now = scheduler.parse_utc("2026-09-02T00:45:00Z")
        self.assertEqual(scheduler.run_once(self.config, tier="daily", now=now, backup_runner=self.result, retention_runner=lambda *_: None), 0)
        monthly = now.replace(day=1, hour=1, minute=30)
        self.assertEqual(scheduler.run_once(self.config, tier="monthly", now=monthly, backup_runner=self.result, retention_runner=lambda *_: None), 0)
        self.assertEqual(json.loads(self.config.status_path.read_text(encoding="utf-8"))["last_result"], "SUCCESS")

    def test_unit_templates_are_fixed_and_do_not_use_shell_interpolation(self):
        unit_dir = Path(__file__).resolve().parents[2] / "deployment" / "systemd"
        units = list(unit_dir.glob("*.service")) + list(unit_dir.glob("*.timer"))
        self.assertEqual(len(units), 7)
        for unit in units:
            content = unit.read_text(encoding="utf-8")
            self.assertIn("%i", content)
            self.assertNotIn("$(", content)
        intraday = (unit_dir / "pmqms-customer-backup@.timer").read_text(encoding="utf-8")
        self.assertEqual(intraday.count("OnCalendar="), 6)
        self.assertIn("Persistent=true", intraday)
        self.assertIn("RandomizedDelaySec=30min", intraday)
        self.assertIn("OnCalendar=*-*-01 01:30:00 UTC", (unit_dir / "pmqms-customer-backup-monthly@.timer").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
