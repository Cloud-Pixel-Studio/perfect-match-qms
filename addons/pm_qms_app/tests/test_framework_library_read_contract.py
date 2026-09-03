from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestFrameworkLibraryReadContract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.quality_manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")

        cls.framework_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.4 Framework Library",
                "code": "M304-FRAMEWORK",
                "company_id": cls.company.id,
                "organization_kind": "framework",
            }
        )
        cls.customer_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.4 Customer Organization",
                "code": "M304-CUSTOMER",
                "company_id": cls.company.id,
            }
        )
        cls.other_customer_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.4 Other Customer Organization",
                "code": "M304-OTHER-CUSTOMER",
                "company_id": cls.company.id,
            }
        )
        cls.framework_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.4 Framework Process",
                "code": "M304-FRAMEWORK-PROCESS",
                "organization_id": cls.framework_org.id,
                "company_id": cls.company.id,
            }
        )
        cls.other_customer_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.4 Other Customer Process",
                "code": "M304-OTHER-PROCESS",
                "organization_id": cls.other_customer_org.id,
                "company_id": cls.company.id,
            }
        )
        cls.framework_control = cls.env["pm.qms.control"].sudo().create(
            {
                "name": "M30.4 Framework Control",
                "code": "M304-FRAMEWORK-CONTROL",
                "objective": "A fictional technical framework control for security tests.",
                "description": "A fictional reusable framework source.",
                "process_id": cls.framework_process.id,
            }
        )
        cls.other_customer_control = cls.env["pm.qms.control"].sudo().create(
            {
                "name": "M30.4 Other Customer Control",
                "code": "M304-OTHER-CONTROL",
                "objective": "A fictional out-of-scope operational control.",
                "process_id": cls.other_customer_process.id,
            }
        )
        cls.framework_activity = cls.env["pm.qms.activity"].sudo().create(
            {
                "name": "M30.4 Framework Activity",
                "control_id": cls.framework_control.id,
                "description": "A fictional activity consumed by the generator.",
            }
        )
        cls.second_framework_control = cls.env["pm.qms.control"].sudo().create(
            {
                "name": "M30.4 Second Framework Control",
                "code": "M304-FRAMEWORK-CONTROL-2",
                "objective": "A second fictional control sharing the source process.",
                "process_id": cls.framework_process.id,
            }
        )
        cls.pack = cls.env["pm.qms.framework.pack"].sudo().create(
            {
                "name": "M30.4 Framework Pack",
                "code": "M304-FRAMEWORK-PACK",
                "version": "1.0",
                "company_id": cls.company.id,
                "pack_type": "core",
                "description": "A fictional pack for the framework read contract test.",
            }
        )
        cls.env["pm.qms.framework.pack.control"].sudo().create(
            [
                {
                    "pack_id": cls.pack.id,
                    "control_id": cls.framework_control.id,
                    "sequence": 10,
                    "required": True,
                },
                {
                    "pack_id": cls.pack.id,
                    "control_id": cls.second_framework_control.id,
                    "sequence": 20,
                    "required": True,
                },
            ]
        )
        cls.pack.sudo().action_activate()

        cls.manager = cls.env["res.users"].sudo().with_context(no_reset_password=True).create(
            {
                "name": "M30.4 Quality Manager",
                "login": "m30.4.quality.manager",
                "email": "m30.4.quality.manager@example.invalid",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, cls.quality_manager_group.id])],
                "qms_organization_ids": [Command.set([cls.customer_org.id])],
                "qms_all_sites": True,
                "qms_all_processes": True,
                "qms_process_ids": [Command.clear()],
            }
        )
        cls.other_company = cls.env["res.company"].sudo().create({"name": "M30.4 Other Company"})
        cls.other_framework_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.4 Other Framework Library",
                "code": "M304-OTHER-FRAMEWORK",
                "company_id": cls.other_company.id,
                "organization_kind": "framework",
            }
        )
        cls.other_framework_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.4 Other Framework Process",
                "code": "M304-OTHER-FRAMEWORK-PROCESS",
                "organization_id": cls.other_framework_org.id,
                "company_id": cls.other_company.id,
            }
        )
        cls.other_framework_control = cls.env["pm.qms.control"].sudo().create(
            {
                "name": "M30.4 Other Framework Control",
                "code": "M304-OTHER-FRAMEWORK-CONTROL",
                "objective": "A fictional cross-company framework source.",
                "process_id": cls.other_framework_process.id,
            }
        )

    @property
    def manager_env(self):
        return self.env.user.browse(self.manager.id).with_user(self.manager)

    def test_same_company_framework_library_and_dependencies_are_readable(self):
        manager = self.manager_env
        self.assertTrue(self.framework_org.with_user(self.manager).read(["name", "organization_kind"]))
        self.assertEqual(
            self.env["pm.qms.process"].with_user(self.manager).search(
                [("id", "=", self.framework_process.id)]
            ),
            self.framework_process,
        )
        self.assertEqual(
            self.env["pm.qms.control"].with_user(self.manager).search(
                [("id", "=", self.framework_control.id)]
            ),
            self.framework_control,
        )
        self.assertEqual(
            self.env["pm.qms.activity"].with_user(self.manager).search(
                [("id", "=", self.framework_activity.id)]
            ),
            self.framework_activity,
        )
        self.assertEqual(
            self.pack.with_user(self.manager).control_line_ids.control_id,
            self.framework_control | self.second_framework_control,
        )
        self.assertNotIn(self.framework_org, manager.qms_organization_ids)
        self.assertNotIn(self.framework_org, manager.qms_effective_organization_ids)
        self.assertNotIn(self.framework_process, manager.qms_effective_process_ids)

    def test_framework_sources_are_read_only_to_quality_manager(self):
        with self.assertRaises(AccessError):
            self.framework_org.with_user(self.manager).write({"description": "must remain immutable"})
        with self.assertRaises(AccessError):
            self.framework_process.with_user(self.manager).write({"description": "must remain immutable"})
        with self.assertRaises(AccessError):
            self.framework_control.with_user(self.manager).write({"description": "must remain immutable"})
        with self.assertRaises(AccessError):
            self.framework_process.with_user(self.manager).unlink()
        with self.assertRaises(AccessError):
            self.framework_control.with_user(self.manager).unlink()
        with self.assertRaises(AccessError):
            self.env["pm.qms.process"].with_user(self.manager).create(
                {
                    "name": "M30.4 Unauthorized Framework Process",
                    "code": "M304-UNAUTHORIZED-PROCESS",
                    "organization_id": self.framework_org.id,
                    "company_id": self.company.id,
                }
            )
        with self.assertRaises(AccessError):
            self.env["pm.qms.control"].with_user(self.manager).create(
                {
                    "name": "M30.4 Unauthorized Framework Control",
                    "code": "M304-UNAUTHORIZED-CONTROL",
                    "objective": "This fixture must not be created.",
                    "process_id": self.framework_process.id,
                }
            )

    def test_cross_company_framework_library_is_hidden(self):
        for model_name, record in (
            ("pm.qms.organization", self.other_framework_org),
            ("pm.qms.process", self.other_framework_process),
            ("pm.qms.control", self.other_framework_control),
        ):
            with self.subTest(model=model_name):
                self.assertFalse(
                    self.env[model_name].with_user(self.manager).search([("id", "=", record.id)])
                )

    def test_operational_scope_remains_separate_from_framework_library(self):
        for model_name, record in (
            ("pm.qms.organization", self.other_customer_org),
            ("pm.qms.process", self.other_customer_process),
            ("pm.qms.control", self.other_customer_control),
        ):
            with self.subTest(model=model_name):
                self.assertFalse(
                    self.env[model_name].with_user(self.manager).search([("id", "=", record.id)])
                )
        self.assertEqual(self.manager_env.qms_organization_ids, self.customer_org)
        self.assertNotIn(self.framework_org, self.manager_env.qms_effective_organization_ids)

    def test_quality_manager_generates_and_syncs_framework_library_idempotently(self):
        Process = self.env["pm.qms.process"].sudo()
        ControlInstance = self.env["pm.qms.control.instance"].sudo()
        ImplementationControl = self.env["pm.qms.implementation.control"].sudo()
        Task = self.env["project.task"].sudo()
        self.assertEqual(Process.search_count([("organization_id", "=", self.customer_org.id)]), 0)

        wizard = self.env["pm.qms.project.generator.wizard"].with_user(self.manager).create(
            {
                "name": "M30.4 Clean Customer Implementation",
                "company_id": self.company.id,
                "organization_id": self.customer_org.id,
                "project_manager_id": self.manager.id,
                "date_start": "2026-09-01",
                "target_date": "2026-10-01",
                "implementation_type": "new_implementation",
                "pack_ids": [Command.set([self.pack.id])],
                "create_odoo_project": True,
            }
        )
        action = wizard.action_generate_implementation()
        project = self.env["pm.qms.implementation.project"].with_user(self.manager).browse(action["res_id"])

        target_processes = Process.search(
            [
                ("code", "=", f"{self.customer_org.code}-{self.framework_process.code}"),
                ("organization_id", "=", self.customer_org.id),
            ]
        )
        self.assertEqual(len(target_processes), 1)
        self.assertEqual(len(project.implementation_control_ids), 2)
        instances = ControlInstance.search([("organization_id", "=", self.customer_org.id)])
        self.assertEqual(len(instances), 2)
        self.assertEqual(set(instances.mapped("process_id").ids), {target_processes.id})
        self.assertGreater(
            Task.search_count(
                [("pm_implementation_project_id", "=", project.id), ("pm_generated", "=", True)]
            ),
            0,
        )

        counts = (
            Process.search_count([("organization_id", "=", self.customer_org.id)]),
            ImplementationControl.search_count([("implementation_project_id", "=", project.id)]),
            ControlInstance.search_count([("organization_id", "=", self.customer_org.id)]),
            Task.search_count(
                [("pm_implementation_project_id", "=", project.id), ("pm_generated", "=", True)]
            ),
        )
        project.action_sync_framework()
        project.action_sync_framework()
        self.assertEqual(
            counts,
            (
                Process.search_count([("organization_id", "=", self.customer_org.id)]),
                ImplementationControl.search_count([("implementation_project_id", "=", project.id)]),
                ControlInstance.search_count([("organization_id", "=", self.customer_org.id)]),
                Task.search_count(
                    [("pm_implementation_project_id", "=", project.id), ("pm_generated", "=", True)]
                ),
            ),
        )
        self.assertNotIn(self.framework_org, self.manager_env.qms_effective_organization_ids)
        self.assertNotIn(self.framework_process, self.manager_env.qms_effective_process_ids)
