from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestM305ControlInstanceAuthorization(TransactionCase):
    """Exercise the clean-customer authorization contract without sudo in user flows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].sudo().create({"name": "M30.5 Other Company"})
        cls.base_user = cls.env.ref("base.group_user")
        cls.manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")

        cls.framework_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.5 Framework Library",
                "code": "M305-FRAMEWORK",
                "company_id": cls.company.id,
                "organization_kind": "framework",
            }
        )
        cls.customer_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.5 Customer Organization",
                "code": "M305-CUSTOMER",
                "company_id": cls.company.id,
            }
        )
        cls.other_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.5 Other Organization",
                "code": "M305-OTHER",
                "company_id": cls.company.id,
            }
        )
        cls.cross_company_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.5 Cross Company Organization",
                "code": "M305-CROSS",
                "company_id": cls.other_company.id,
            }
        )
        cls.site = cls.env["pm.qms.site"].sudo().create(
            {
                "name": "M30.5 Customer Headquarters",
                "code": "M305-HQ",
                "organization_id": cls.customer_org.id,
                "site_type": "headquarters",
            }
        )
        cls.framework_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.5 Framework Process",
                "code": "M305-FRAMEWORK-P",
                "organization_id": cls.framework_org.id,
                "company_id": cls.company.id,
            }
        )
        cls.other_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.5 Other Organization Process",
                "code": "M305-OTHER-P",
                "organization_id": cls.other_org.id,
                "company_id": cls.company.id,
            }
        )
        cls.cross_company_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.5 Cross Company Process",
                "code": "M305-CROSS-P",
                "organization_id": cls.cross_company_org.id,
                "company_id": cls.other_company.id,
            }
        )
        cls.framework_control = cls.env["pm.qms.control"].sudo().create(
            {
                "name": "M30.5 Framework Control",
                "code": "M305-CONTROL",
                "objective": "A fictional framework control for authorization testing.",
                "process_id": cls.framework_process.id,
            }
        )
        cls.framework_control_two = cls.env["pm.qms.control"].sudo().create(
            {
                "name": "M30.5 Shared Framework Control",
                "code": "M305-CONTROL-2",
                "objective": "A second fictional control sharing one source process.",
                "process_id": cls.framework_process.id,
            }
        )
        cls.pack = cls.env["pm.qms.framework.pack"].sudo().create(
            {
                "name": "ISO 9001 Initial Implementation",
                "code": "M305-ISO9001-INITIAL",
                "version": "1.1",
                "company_id": cls.company.id,
                "pack_type": "standard",
                "description": "A fictional clean-customer generation pack for authorization tests.",
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
                    "control_id": cls.framework_control_two.id,
                    "sequence": 20,
                    "required": True,
                },
            ]
        )
        cls.pack.sudo().action_activate()
        cls.env["pm.qms.activity"].sudo().create(
            [
                {
                    "name": "M30.5 Framework Activity One",
                    "control_id": cls.framework_control.id,
                    "description": "A fictional generated activity.",
                },
                {
                    "name": "M30.5 Framework Activity Two",
                    "control_id": cls.framework_control_two.id,
                    "description": "A second fictional generated activity.",
                },
            ]
        )

        def make_user(login, organization=None, *, all_processes=False, processes=None):
            return cls.env["res.users"].sudo().with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.invalid",
                    "company_id": cls.company.id,
                    "company_ids": [Command.set([cls.company.id])],
                    "group_ids": [Command.set([cls.base_user.id, cls.manager_group.id])],
                    "qms_organization_ids": [Command.set([organization.id])] if organization else [Command.clear()],
                    "qms_all_sites": True,
                    "qms_all_processes": all_processes,
                    "qms_process_ids": [Command.set(processes.ids if processes else [])],
                }
            )

        cls.all_process_manager = make_user(
            "m30.5.all.processes", cls.customer_org, all_processes=True
        )
        cls.empty_scope_manager = make_user("m30.5.empty.scope")

    def _make_user(self, login, organization=None, *, all_processes=False, processes=None):
        return self.env["res.users"].sudo().with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([self.base_user.id, self.manager_group.id])],
                "qms_organization_ids": [Command.set([organization.id])] if organization else [Command.clear()],
                "qms_all_sites": True,
                "qms_all_processes": all_processes,
                "qms_process_ids": [Command.set(processes.ids if processes else [])],
            }
        )

    def _instance_values(self, organization, process, control=None):
        return {
            "name": "M30.5 Authorization Test Instance",
            "control_id": (control or self.framework_control).id,
            "organization_id": organization.id,
            "process_id": process.id,
        }

    def test_all_process_manager_can_create_and_read_new_process_instance(self):
        manager = self.all_process_manager
        manager_env = self.env["res.users"].browse(manager.id).with_user(manager)
        self.assertTrue(manager.has_group("pm_qms_core.group_qms_quality_manager"))
        self.assertTrue(manager.has_group("pm_qms_core.group_pm_qms_manager"))
        self.assertTrue(manager.qms_scope_configured)
        self.assertTrue(manager.qms_all_processes)
        self.assertTrue(manager_env.qms_effective_organization_ids)
        self.assertFalse(manager_env.qms_effective_process_ids)
        self.assertTrue(
            self.env["pm.qms.control.instance"].with_user(manager).check_access_rights(
                "create", raise_exception=False
            )
        )

        process = self.env["pm.qms.process"].with_user(manager).create(
            {
                "name": "M30.5 Newly Materialized Process",
                "code": "M305-NEW-P",
                "organization_id": self.customer_org.id,
                "company_id": self.company.id,
            }
        )
        self.assertFalse(process.site_ids)
        self.assertIn(process, manager_env.qms_effective_process_ids)
        instance = self.env["pm.qms.control.instance"].with_user(manager).create(
            self._instance_values(self.customer_org, process)
        )
        self.assertEqual(instance.with_user(manager).read(["id"])[0]["id"], instance.id)

    def test_selected_process_manager_cannot_expand_to_unselected_process(self):
        selected_process = self.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.5 Selected Process",
                "code": "M305-SELECTED-P",
                "organization_id": self.customer_org.id,
                "company_id": self.company.id,
                "site_ids": [Command.set([self.site.id])],
            }
        )
        unselected_process = self.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.5 Unselected Process",
                "code": "M305-UNSELECTED-P",
                "organization_id": self.customer_org.id,
                "company_id": self.company.id,
            }
        )
        manager = self._make_user(
            "m30.5.selected.process", self.customer_org, processes=selected_process
        )
        self.assertEqual(manager.qms_effective_process_ids, selected_process)
        with self.assertRaises(AccessError):
            self.env["pm.qms.control.instance"].with_user(manager).create(
                self._instance_values(self.customer_org, unselected_process)
            )

    def test_out_of_scope_organization_is_denied(self):
        with self.assertRaises(AccessError):
            self.env["pm.qms.control.instance"].with_user(self.all_process_manager).create(
                self._instance_values(self.other_org, self.other_process)
            )

    def test_cross_company_process_is_denied(self):
        cross_company_control = self.env["pm.qms.control"].sudo().create(
            {
                "name": "M30.5 Cross Company Control",
                "code": "M305-CROSS-CONTROL",
                "objective": "A fictional cross-company authorization control.",
                "process_id": self.cross_company_process.id,
            }
        )
        with self.assertRaises(AccessError):
            self.env["pm.qms.control.instance"].with_user(self.all_process_manager).create(
                self._instance_values(
                    self.cross_company_org,
                    self.cross_company_process,
                    cross_company_control,
                )
            )

    def test_framework_process_is_not_a_customer_instance_target(self):
        with self.assertRaises(AccessError):
            self.env["pm.qms.control.instance"].with_user(self.all_process_manager).create(
                self._instance_values(
                    self.framework_org,
                    self.framework_process,
                    self.framework_control,
                )
            )

    def test_empty_scope_fails_closed_for_create(self):
        process = self.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.5 Empty Scope Process",
                "code": "M305-EMPTY-SCOPE-P",
                "organization_id": self.customer_org.id,
                "company_id": self.company.id,
            }
        )
        with self.assertRaises(AccessError):
            self.env["pm.qms.control.instance"].with_user(self.empty_scope_manager).create(
                self._instance_values(self.customer_org, process)
            )

    def test_unauthorized_manager_cannot_read_instance_from_unselected_process(self):
        unselected_process = self.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.5 Read Restricted Process",
                "code": "M305-READ-RESTRICTED-P",
                "organization_id": self.customer_org.id,
                "company_id": self.company.id,
            }
        )
        selected_manager = self._make_user(
            "m30.5.read.selected", self.customer_org,
            processes=self.env["pm.qms.process"].browse(),
        )
        instance = self.env["pm.qms.control.instance"].with_user(self.all_process_manager).create(
            self._instance_values(self.customer_org, unselected_process)
        )
        with self.assertRaises(AccessError):
            instance.with_user(selected_manager).read(["name"])

    def test_clean_customer_generator_from_zero_is_idempotent(self):
        manager = self.all_process_manager
        manager_env = self.env["res.users"].browse(manager.id).with_user(manager)
        self.assertFalse(manager_env.qms_effective_process_ids.filtered(lambda p: p.organization_id == self.customer_org))
        self.assertEqual(
            self.env["pm.qms.process"].sudo().search_count(
                [("organization_id", "=", self.customer_org.id)]
            ),
            0,
        )

        wizard = self.env["pm.qms.project.generator.wizard"].with_user(manager).create(
            {
                "name": "M30.5 Clean Customer Implementation",
                "company_id": self.company.id,
                "organization_id": self.customer_org.id,
                "project_manager_id": manager.id,
                "date_start": "2026-09-01",
                "target_date": "2026-10-01",
                "implementation_type": "new_implementation",
                "pack_ids": [Command.set([self.pack.id])],
                "create_odoo_project": True,
            }
        )
        project = self.env["pm.qms.implementation.project"].with_user(manager).browse(
            wizard.action_generate_implementation()["res_id"]
        )
        self.assertEqual(project.state, "generated")
        self.assertEqual(len(project.implementation_control_ids), 2)
        processes = self.env["pm.qms.process"].sudo().search(
            [("organization_id", "=", self.customer_org.id)]
        )
        self.assertEqual(len(processes), 1)
        instances = self.env["pm.qms.control.instance"].sudo().search(
            [("organization_id", "=", self.customer_org.id)]
        )
        self.assertEqual(len(instances), 2)
        target_process = processes.filtered(lambda p: p.code == "M305-CUSTOMER-M305-FRAMEWORK-P")
        self.assertEqual(target_process, processes)
        self.assertEqual(set(instances.mapped("process_id").ids), {target_process.id})
        self.assertEqual(
            self.env["project.task"].sudo().search_count(
                [("pm_implementation_project_id", "=", project.id), ("pm_generated", "=", True)]
            ),
            2,
        )

        counts = (
            len(processes),
            len(project.implementation_control_ids),
            len(instances),
            self.env["project.task"].sudo().search_count(
                [("pm_implementation_project_id", "=", project.id), ("pm_generated", "=", True)]
            ),
        )
        project.with_user(manager).action_sync_framework()
        project.with_user(manager).action_sync_framework()
        self.assertEqual(
            counts,
            (
                self.env["pm.qms.process"].sudo().search_count(
                    [("organization_id", "=", self.customer_org.id)]
                ),
                len(project.implementation_control_ids),
                self.env["pm.qms.control.instance"].sudo().search_count(
                    [("organization_id", "=", self.customer_org.id)]
                ),
                self.env["project.task"].sudo().search_count(
                    [("pm_implementation_project_id", "=", project.id), ("pm_generated", "=", True)]
                ),
            ),
        )
