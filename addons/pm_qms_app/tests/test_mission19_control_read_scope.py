from odoo import Command
from odoo.tests.common import TransactionCase


class TestMission19ControlReadScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.organization = cls.env["pm.qms.organization"].sudo().create(
            {
                "name": "M19 Read Scope Organization",
                "code": "M19-READ-ORG",
                "company_id": cls.company.id,
            }
        )
        cls.site_a = cls.env["pm.qms.site"].sudo().create(
            {
                "name": "M19 Read Scope Site A",
                "code": "M19-READ-A",
                "organization_id": cls.organization.id,
                "site_type": "manufacturing",
            }
        )
        cls.site_b = cls.env["pm.qms.site"].sudo().create(
            {
                "name": "M19 Read Scope Site B",
                "code": "M19-READ-B",
                "organization_id": cls.organization.id,
                "site_type": "inspection",
            }
        )
        cls.process_a = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M19 Read Scope Process A",
                "code": "M19-READ-P-A",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
                "site_ids": [Command.set([cls.site_a.id])],
            }
        )
        cls.process_b = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M19 Read Scope Process B",
                "code": "M19-READ-P-B",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
                "site_ids": [Command.set([cls.site_b.id])],
            }
        )
        cls.framework_process = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M19 Read Scope Framework Process",
                "code": "M19-READ-P-FRAMEWORK",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )

    def _create_scoped_user(self, login, group_xmlid, processes):
        return self.env["res.users"].sudo().with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(group_xmlid).id,
                        ]
                    )
                ],
                "qms_organization_ids": [Command.set([self.organization.id])],
                "qms_process_ids": [Command.set(processes.ids)],
            }
        )

    def _create_control(self, code, process, objective):
        return self.env["pm.qms.control"].sudo().create(
            {
                "name": code,
                "code": code,
                "objective": objective,
                "process_id": process.id,
            }
        )

    def _create_instance(self, control, process, organization=None):
        return self.env["pm.qms.control.instance"].sudo().create(
            {
                "name": f"{control.name} instance",
                "control_id": control.id,
                "organization_id": (organization or self.organization).id,
                "process_id": process.id,
            }
        )

    def test_consumed_master_control_is_readable_without_broadening_scope(self):
        consumed = self._create_control(
            "M19-C-CONSUMED",
            self.framework_process,
            "A fictional consumed master control.",
        )
        unrelated = self._create_control(
            "M19-C-UNRELATED",
            self.framework_process,
            "A fictional unrelated master control.",
        )
        wrong_process = self._create_control(
            "M19-C-WRONG",
            self.framework_process,
            "A fictional wrong-process master control.",
        )
        self._create_instance(consumed, self.process_a)
        self._create_instance(wrong_process, self.process_b)

        manager = self._create_scoped_user(
            "m19.quality.manager",
            "pm_qms_core.group_qms_quality_manager",
            self.process_a,
        )
        controls = self.env["pm.qms.control"].with_user(manager)

        self.assertTrue(controls.search([("id", "=", consumed.id)]))
        self.assertFalse(controls.search([("id", "=", unrelated.id)]))
        self.assertFalse(controls.search([("id", "=", wrong_process.id)]))
        self.assertTrue(
            controls.search([("id", "=", self._create_control(
                "M19-C-DIRECT",
                self.process_a,
                "A fictional directly scoped master control.",
            ).id)])
        )
        self.assertTrue(controls.check_access_rights("read", raise_exception=False))
        self.assertFalse(controls.check_access_rights("write", raise_exception=False))
        self.assertFalse(controls.check_access_rights("create", raise_exception=False))
        self.assertFalse(controls.check_access_rights("unlink", raise_exception=False))

    def test_process_and_company_boundaries_are_preserved(self):
        wrong_process = self._create_control(
            "M19-C-BOUNDARY-WRONG",
            self.framework_process,
            "A fictional wrong-process control.",
        )
        self._create_instance(wrong_process, self.process_b)

        other_company = self.env["res.company"].sudo().create(
            {"name": "M19 Read Scope Other Company"}
        )
        other_organization = self.env["pm.qms.organization"].sudo().create(
            {
                "name": "M19 Read Scope Other Organization",
                "code": "M19-READ-OTHER-ORG",
                "company_id": other_company.id,
            }
        )
        other_process = self.env["pm.qms.process"].sudo().create(
            {
                "name": "M19 Read Scope Other Process",
                "code": "M19-READ-OTHER-P",
                "organization_id": other_organization.id,
                "company_id": other_company.id,
            }
        )
        cross_company = self._create_control(
            "M19-C-CROSS-COMPANY",
            other_process,
            "A fictional cross-company control.",
        )
        self._create_instance(cross_company, other_process, other_organization)

        manager = self._create_scoped_user(
            "m19.boundary.manager",
            "pm_qms_core.group_qms_quality_manager",
            self.process_a,
        )
        controls = self.env["pm.qms.control"].with_user(manager)
        self.assertFalse(controls.search([("id", "=", wrong_process.id)]))
        self.assertFalse(controls.search([("id", "=", cross_company.id)]))

        process_owner = self._create_scoped_user(
            "m19.process.owner",
            "pm_qms_core.group_qms_process_owner",
            self.process_a,
        )
        process_owner_controls = self.env["pm.qms.control"].with_user(process_owner)
        self.assertFalse(process_owner_controls.search([("id", "=", wrong_process.id)]))

    def test_quality_manager_can_read_implementation_guidance_from_consumed_control(self):
        consumed = self._create_control(
            "M19-C-GUIDANCE",
            self.framework_process,
            "A fictional guidance control.",
        )
        consumed.write(
            {
                "guidance_purpose": "Purpose guidance for the implementation user.",
                "guidance_why": "Why guidance for the implementation user.",
                "implementation_guidance": "Implementation guidance for the implementation user.",
                "recommended_steps": "Recommended steps for the implementation user.",
                "evidence_guidance": "Evidence guidance for the implementation user.",
            }
        )
        instance = self._create_instance(consumed, self.process_a)
        manager = self._create_scoped_user(
            "m19.guidance.manager",
            "pm_qms_core.group_qms_quality_manager",
            self.process_a,
        )
        project = self.env["pm.qms.implementation.project"].sudo().create(
            {
                "name": "M19 Scoped Implementation",
                "company_id": self.company.id,
                "organization_id": self.organization.id,
                "project_manager_id": manager.id,
                "date_start": "2026-08-15",
                "target_date": "2026-09-30",
            }
        )
        line = self.env["pm.qms.implementation.control"].sudo().create(
            {
                "implementation_project_id": project.id,
                "control_id": consumed.id,
                "control_instance_id": instance.id,
            }
        )

        scoped_line = self.env["pm.qms.implementation.control"].with_user(manager).browse(line.id)
        self.assertTrue(scoped_line.exists())
        self.assertEqual(scoped_line.control_id, consumed)
        self.assertEqual(
            scoped_line.guidance_purpose,
            "Purpose guidance for the implementation user.",
        )
        self.assertEqual(
            scoped_line.guidance_why,
            "Why guidance for the implementation user.",
        )
        self.assertEqual(
            scoped_line.implementation_guidance,
            "Implementation guidance for the implementation user.",
        )
        self.assertEqual(
            scoped_line.recommended_steps,
            "Recommended steps for the implementation user.",
        )
        self.assertEqual(
            scoped_line.evidence_guidance,
            "Evidence guidance for the implementation user.",
        )

    def test_viewer_can_consume_guidance_but_cannot_mutate_master(self):
        consumed = self._create_control(
            "M19-C-VIEWER",
            self.framework_process,
            "A fictional viewer guidance control.",
        )
        self._create_instance(consumed, self.process_a)
        viewer = self._create_scoped_user(
            "m19.scoped.viewer",
            "pm_qms_core.group_qms_viewer",
            self.process_a,
        )
        controls = self.env["pm.qms.control"].with_user(viewer)
        self.assertTrue(controls.search([("id", "=", consumed.id)]))
        self.assertFalse(controls.check_access_rights("write", raise_exception=False))
        self.assertFalse(controls.check_access_rights("create", raise_exception=False))
        self.assertFalse(controls.check_access_rights("unlink", raise_exception=False))
