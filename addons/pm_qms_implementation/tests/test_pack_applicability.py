from pathlib import Path

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestPmQmsPackApplicability(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.env.user.write({"group_ids": [(4, cls.env.ref("pm_qms_core.group_pm_qms_manager").id)]})
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Pack Applicability Organization", "code": "PM-APP-ORG"}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Pack Applicability Process",
                "code": "PM-APP-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "Pack Applicability Control",
                "code": "PM-QMS-APP-001",
                "objective": "Apply a fictional reusable control for pack tests.",
                "process_id": cls.process.id,
                "category": "process",
            }
        )
        cls.control.action_activate()
        cls.pack_a = cls._create_pack("PM-APP-A")
        cls.pack_b = cls._create_pack("PM-APP-B")
        cls.global_activity = cls.env["pm.qms.activity"].create(
            {"control_id": cls.control.id, "name": "Global implementation activity"}
        )
        cls.scoped_a = cls.env["pm.qms.activity"].create(
            {
                "control_id": cls.control.id,
                "name": "Pack A implementation activity",
                "applicable_pack_ids": [Command.set([cls.pack_a.id])],
            }
        )
        cls.scoped_b = cls.env["pm.qms.activity"].create(
            {
                "control_id": cls.control.id,
                "name": "Pack B implementation activity",
                "applicable_pack_ids": [Command.set([cls.pack_b.id])],
            }
        )

    @classmethod
    def _create_pack(cls, code):
        pack = cls.env["pm.qms.framework.pack"].create(
            {
                "name": f"{code} Pack",
                "code": code,
                "version": "1.0",
                "company_id": cls.company.id,
                "pack_type": "core",
            }
        )
        cls.env["pm.qms.framework.pack.control"].create(
            {
                "pack_id": pack.id,
                "control_id": cls.control.id,
                "sequence": 10,
                "required": True,
            }
        )
        pack.action_activate()
        return pack

    def _project(self, packs, name):
        project = self.env["pm.qms.implementation.project"].create(
            {
                "name": name,
                "company_id": self.company.id,
                "organization_id": self.organization.id,
                "date_start": "2026-08-27",
                "target_date": "2026-09-30",
                "pack_ids": [Command.set([pack.id for pack in packs])],
            }
        )
        project._sync_framework()
        return project

    def _task_names(self, project):
        return set(project.generated_task_ids.mapped("pm_activity_id.name"))

    def test_empty_scope_remains_global(self):
        project = self._project([self.pack_a], "Global scope")
        self.assertIn(self.global_activity.name, self._task_names(project))

    def test_matching_pack_scope_generates(self):
        project = self._project([self.pack_a], "Matching scope")
        names = self._task_names(project)
        self.assertIn(self.scoped_a.name, names)

    def test_nonmatching_pack_scope_is_excluded(self):
        project = self._project([self.pack_a], "Nonmatching scope")
        names = self._task_names(project)
        self.assertNotIn(self.scoped_b.name, names)

    def test_any_matching_pack_in_multi_pack_control_generates(self):
        project = self._project([self.pack_a, self.pack_b], "Multi pack scope")
        names = self._task_names(project)
        self.assertIn(self.scoped_a.name, names)
        self.assertIn(self.scoped_b.name, names)

    def test_readiness_required_remains_separate_from_scope(self):
        self.assertTrue(self.scoped_a.readiness_required)
        self.scoped_a.write({"readiness_required": False})
        project = self._project([self.pack_a], "Readiness separation")
        task = project.generated_task_ids.filtered(
            lambda item: item.pm_activity_id == self.scoped_a
        )
        self.assertEqual(len(task), 1)
        self.assertFalse(task.pm_required)

    def test_required_matching_activity_is_required(self):
        project = self._project([self.pack_a], "Required matching")
        task = project.generated_task_ids.filtered(
            lambda item: item.pm_activity_id == self.scoped_a
        )
        self.assertTrue(task.pm_required)

    def test_nonmatching_scoped_activity_creates_no_task(self):
        project = self._project([self.pack_a], "No nonmatching task")
        self.assertFalse(
            project.generated_task_ids.filtered(
                lambda item: item.pm_activity_id == self.scoped_b
            )
        )

    def test_optional_control_matching_activity_is_not_required(self):
        pack = self.env["pm.qms.framework.pack"].create(
            {
                "name": "Optional Applicability Pack",
                "code": "PM-APP-OPTIONAL",
                "version": "1.0",
                "company_id": self.company.id,
                "pack_type": "core",
            }
        )
        self.env["pm.qms.framework.pack.control"].create(
            {
                "pack_id": pack.id,
                "control_id": self.control.id,
                "sequence": 10,
                "required": False,
            }
        )
        pack.action_activate()
        self.scoped_a.write({"applicable_pack_ids": [Command.set([pack.id])], "readiness_required": True})
        project = self._project([pack], "Optional matching")
        task = project.generated_task_ids.filtered(
            lambda item: item.pm_activity_id == self.scoped_a
        )
        self.assertEqual(len(task), 1)
        self.assertFalse(task.pm_required)

    def test_existing_global_activity_behavior_is_backward_compatible(self):
        self.assertFalse(self.global_activity.applicable_pack_ids)
        project = self._project([self.pack_b], "Legacy activity")
        self.assertIn(self.global_activity.name, self._task_names(project))

    def test_generic_modules_do_not_depend_on_iso_addon(self):
        for module in ("pm_qms_core", "pm_qms_implementation"):
            manifest = (Path(__file__).parents[2] / module / "__manifest__.py").read_text()
            self.assertNotIn("pm_qms_iso9001", manifest)
