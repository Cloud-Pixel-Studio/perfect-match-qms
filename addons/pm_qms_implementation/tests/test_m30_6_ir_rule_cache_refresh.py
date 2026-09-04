from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("-at_install", "post_install")
class TestM306IrRuleCacheRefresh(TransactionCase):
    """Keep the real clean-customer process/materialization order covered."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.base_user = cls.env.ref("base.group_user")
        cls.manager_group = cls.env.ref("pm_qms_core.group_qms_quality_manager")

        cls.framework_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.6 Framework Library",
                "code": "M306-FRAMEWORK",
                "company_id": cls.company.id,
                "organization_kind": "framework",
            }
        )
        cls.customer_org = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M30.6 Customer Organization",
                "code": "M306-CUSTOMER",
                "company_id": cls.company.id,
            }
        )
        cls.framework_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M30.6 Framework Process",
                "code": "M306-FRAMEWORK-P",
                "organization_id": cls.framework_org.id,
                "company_id": cls.company.id,
            }
        )
        cls.controls = cls.env["pm.qms.control"].sudo().create(
            [
                {
                    "name": "M30.6 Framework Control One",
                    "code": "M306-CONTROL-1",
                    "objective": "A fictional control for cache refresh coverage.",
                    "process_id": cls.framework_process.id,
                },
                {
                    "name": "M30.6 Framework Control Two",
                    "code": "M306-CONTROL-2",
                    "objective": "A second fictional control sharing one source process.",
                    "process_id": cls.framework_process.id,
                },
            ]
        )
        cls.controls.sudo().action_activate()
        cls.pack = cls.env["pm.qms.framework.pack"].sudo().create(
            {
                "name": "M30.6 ISO 9001 Initial Implementation",
                "code": "M306-ISO9001-INITIAL",
                "version": "1.1",
                "company_id": cls.company.id,
                "pack_type": "standard",
            }
        )
        cls.env["pm.qms.framework.pack.control"].sudo().create(
            [
                {
                    "pack_id": cls.pack.id,
                    "control_id": control.id,
                    "sequence": (index + 1) * 10,
                    "required": True,
                }
                for index, control in enumerate(cls.controls)
            ]
        )
        cls.pack.sudo().action_activate()
        cls.env["pm.qms.activity"].sudo().create(
            [
                {
                    "name": "M30.6 Activity One",
                    "control_id": cls.controls[0].id,
                    "description": "A fictional generated activity.",
                },
                {
                    "name": "M30.6 Activity Two",
                    "control_id": cls.controls[1].id,
                    "description": "A second fictional generated activity.",
                },
            ]
        )

    def _create_manager(self, suffix):
        return self.env["res.users"].sudo().with_context(
            no_reset_password=True
        ).create(
            {
                "name": f"M30.6 Quality Manager {suffix}",
                "login": f"m30.6.cache.manager.{suffix}",
                "email": f"m30.6.cache.manager.{suffix}@example.invalid",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([self.base_user.id, self.manager_group.id])],
                "qms_organization_ids": [Command.set([self.customer_org.id])],
                "qms_all_sites": True,
                "qms_all_processes": True,
                "qms_process_ids": [Command.clear()],
            }
        )

    def _instance_values(self, manager, control, process):
        return {
            "name": control.name,
            "control_id": control.id,
            "organization_id": self.customer_org.id,
            "process_id": process.id,
            "owner_id": manager.id,
        }

    def test_precomputed_create_rule_refreshes_after_new_process(self):
        manager = self._create_manager("direct")
        manager_env = self.env["res.users"].browse(manager.id).with_user(manager)
        rule_env = self.env["ir.rule"].with_user(manager)
        self.assertFalse(manager_env.qms_effective_process_ids)
        self.assertEqual(
            str(rule_env._compute_domain("pm.qms.control.instance", mode="create")),
            "[(0, '=', 1)]",
        )

        project = self.env["pm.qms.implementation.project"].with_user(manager).new(
            {"company_id": self.company.id, "organization_id": self.customer_org.id}
        )
        process = project._target_process_for_control(self.controls[0])

        self.assertIn(process, manager_env.qms_effective_process_ids)
        domain = rule_env._compute_domain("pm.qms.control.instance", mode="create")
        self.assertIn(("process_id", "in", [process.id]), list(domain))
        instance = self.env["pm.qms.control.instance"].with_user(manager).create(
            self._instance_values(manager, self.controls[0], process)
        )
        self.assertEqual(instance.with_user(manager).read(["id"])[0]["id"], instance.id)

    def test_generator_from_zero_refreshes_precomputed_create_rule(self):
        manager = self._create_manager("generator")
        manager_env = self.env["res.users"].browse(manager.id).with_user(manager)
        rule_env = self.env["ir.rule"].with_user(manager)
        self.assertFalse(manager_env.qms_effective_process_ids)
        self.assertEqual(
            str(rule_env._compute_domain("pm.qms.control.instance", mode="create")),
            "[(0, '=', 1)]",
        )

        wizard = self.env["pm.qms.project.generator.wizard"].with_user(manager).create(
            {
                "name": "M30.6 Cache Refresh Implementation",
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
        self.assertEqual(
            self.env["project.task"].sudo().search_count(
                [("pm_implementation_project_id", "=", project.id), ("pm_generated", "=", True)]
            ),
            2,
        )
