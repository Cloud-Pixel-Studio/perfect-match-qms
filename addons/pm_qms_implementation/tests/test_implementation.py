from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged("-at_install", "post_install")
class TestPmQmsImplementation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Implementation Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.qms_admin_group = cls.env.ref("pm_qms_core.group_pm_qms_administrator")

        cls.user = cls._create_test_user("impl_user", cls.qms_user_group)
        cls.manager = cls._create_test_user("impl_manager", cls.qms_manager_group)
        cls.admin = cls._create_test_user("impl_admin", cls.qms_admin_group)
        cls.other_user = cls._create_test_user("impl_other_user", cls.qms_user_group, cls.other_company)

        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Implementation Organization", "code": "PM-IMP-ORG", "company_id": cls.company.id}
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other Company Implementation Organization", "code": "PM-IMP-ORG2", "company_id": cls.other_company.id}
        )
        cls.same_company_other_org = cls.env["pm.qms.organization"].create(
            {"name": "Same Company Other Implementation Org", "code": "PM-IMP-ORG3", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "Implementation Process",
                "code": "PM-IMP-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other Implementation Process",
                "code": "PM-IMP-PROC2",
                "organization_id": cls.other_organization.id,
                "company_id": cls.other_company.id,
            }
        )
        cls.same_company_other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Same Company Other Implementation Process",
                "code": "PM-IMP-PROC3",
                "organization_id": cls.same_company_other_org.id,
                "company_id": cls.company.id,
            }
        )

        cls.controls = []
        for number in range(1, 13):
            control = cls.env["pm.qms.control"].create(
                {
                    "name": f"Implementation Demo Control {number}",
                    "code": f"PM-QMS-IMP-T{number:03d}",
                    "objective": f"Apply Perfect Match implementation method {number}.",
                    "description": "Original Perfect Match implementation control for generator tests.",
                    "process_id": cls.process.id,
                    "category": "process",
                }
            )
            control.action_activate()
            cls.controls.append(control)

        cls.activity = cls.env["pm.qms.activity"].create(
            {
                "control_id": cls.controls[0].id,
                "name": "Confirm implementation owner",
                "description": "Confirm the implementation owner for this control.",
                "expected_output": "Owner confirmed.",
            }
        )
        cls.second_activity = cls.env["pm.qms.activity"].create(
            {
                "control_id": cls.controls[1].id,
                "name": "Confirm implementation record",
                "description": "Confirm the implementation record for this control.",
            }
        )
        cls.evidence_requirement = cls.env["pm.qms.evidence.requirement"].create(
            {
                "control_id": cls.controls[0].id,
                "name": "Implementation owner record",
                "evidence_type": "record",
                "mandatory": True,
            }
        )

    @classmethod
    def _create_test_user(cls, login, group, company=None):
        company = company or cls.company
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.invalid",
                "company_id": company.id,
                "company_ids": [Command.set([company.id])],
                "group_ids": [Command.set([cls.base_user_group.id, group.id])],
            }
        )

    def _create_pack(self, code, controls, required=None, admin=None):
        admin = admin or self.admin
        required = required or {}
        pack = self.env["pm.qms.framework.pack"].with_user(admin).create(
            {
                "name": f"{code} Pack",
                "code": code,
                "version": "1.0",
                "company_id": self.company.id,
                "pack_type": "core",
                "description": "Fictional Perfect Match pack for implementation tests.",
            }
        )
        for index, control in enumerate(controls, start=1):
            self.env["pm.qms.framework.pack.control"].with_user(admin).create(
                {
                    "pack_id": pack.id,
                    "control_id": control.id,
                    "sequence": index * 10,
                    "required": required.get(control.id, True),
                }
            )
        pack.with_user(admin).action_activate()
        return pack

    def _generate_project(self, packs, name="Generated Implementation", organization=None, manager=None):
        manager = manager or self.manager
        organization = organization or self.organization
        wizard = self.env["pm.qms.project.generator.wizard"].with_user(manager).create(
            {
                "name": name,
                "company_id": organization.company_id.id,
                "organization_id": organization.id,
                "project_manager_id": manager.id,
                "date_start": "2026-08-15",
                "target_date": "2026-09-30",
                "implementation_type": "new_implementation",
                "pack_ids": [Command.set([pack.id for pack in packs])],
                "create_odoo_project": True,
            }
        )
        action = wizard.action_generate_implementation()
        return self.env["pm.qms.implementation.project"].browse(action["res_id"])

    def _accept_evidence(self, line):
        evidence = self.env["pm.qms.evidence"].with_user(self.manager).create(
            {
                "name": "Accepted implementation owner evidence",
                "control_instance_id": line.control_instance_id.id,
                "evidence_requirement_id": self.evidence_requirement.id,
            }
        )
        evidence.with_user(self.manager).action_submit()
        evidence.with_user(self.manager).action_accept()
        return evidence

    def _mark_ready(self, line):
        if line.control_instance_id.implementation_status != "implemented":
            line.control_instance_id.with_user(self.manager).action_mark_implemented()
        if line.control_id == self.controls[0]:
            self._accept_evidence(line)
        for task in line.task_ids.filtered(lambda item: item.pm_required and not item.is_closed):
            task.with_user(self.manager).write({"state": "1_done"})

    def test_pack_versioning_lifecycle_and_active_pack_locking(self):
        pack = self._create_pack("PM-TST-VERSION", [self.controls[0]])

        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            with self.env.cr.savepoint():
                self.env["pm.qms.framework.pack"].with_user(self.admin).create(
                    {
                        "name": "Duplicate Version Pack",
                        "code": "PM-TST-VERSION",
                        "version": "1.0",
                        "company_id": self.company.id,
                    }
                )

        next_version = self.env["pm.qms.framework.pack"].with_user(self.admin).create(
            {
                "name": "Next Version Pack",
                "code": "PM-TST-VERSION",
                "version": "1.1",
                "company_id": self.company.id,
            }
        )
        self.assertEqual(next_version.version, "1.1")

        with self.assertRaises(UserError):
            pack.control_line_ids.with_user(self.admin).write({"required": False})
        with self.assertRaises(UserError):
            self.env["pm.qms.framework.pack.control"].with_user(self.admin).create(
                {"pack_id": pack.id, "control_id": self.controls[1].id}
            )

    def test_generator_multi_pack_deduplication_source_packs_and_sync_idempotency(self):
        pack_a = self._create_pack("PM-TST-A", [self.controls[0], self.controls[1]], required={self.controls[1].id: False})
        pack_b = self._create_pack("PM-TST-B", [self.controls[1], self.controls[2]])

        project = self._generate_project([pack_a, pack_b])
        self.assertEqual(project.state, "generated")
        self.assertTrue(project.odoo_project_id)
        self.assertEqual(len(project.implementation_control_ids), 3)
        self.assertEqual(
            self.env["pm.qms.control.instance"].search_count(
                [("organization_id", "=", self.organization.id), ("control_id", "in", [c.id for c in self.controls[:3]])]
            ),
            3,
        )
        shared_line = project.implementation_control_ids.filtered(lambda line: line.control_id == self.controls[1])
        self.assertEqual(set(shared_line.pack_ids.ids), {pack_a.id, pack_b.id})
        self.assertTrue(shared_line.required)
        self.assertEqual(project.total_generated_tasks, 2)

        counts = (
            len(project.implementation_control_ids),
            project.generated_task_ids.search_count([("pm_implementation_project_id", "=", project.id)]),
            self.env["pm.qms.control.instance"].search_count([("organization_id", "=", self.organization.id)]),
        )
        project.with_user(self.manager).action_sync_framework()
        project.with_user(self.manager).action_sync_framework()
        self.assertEqual(
            counts,
            (
                len(project.implementation_control_ids),
                project.generated_task_ids.search_count([("pm_implementation_project_id", "=", project.id)]),
                self.env["pm.qms.control.instance"].search_count([("organization_id", "=", self.organization.id)]),
            ),
        )

    def test_existing_control_instance_is_reused_and_other_organization_is_ignored(self):
        existing = self.env["pm.qms.control.instance"].create(
            {
                "name": "Existing implementation instance",
                "control_id": self.controls[3].id,
                "organization_id": self.organization.id,
                "process_id": self.process.id,
            }
        )
        other_org_instance = self.env["pm.qms.control.instance"].create(
            {
                "name": "Other organization implementation instance",
                "control_id": self.controls[4].id,
                "organization_id": self.same_company_other_org.id,
                "process_id": self.same_company_other_process.id,
            }
        )
        pack = self._create_pack("PM-TST-REUSE", [self.controls[3], self.controls[4]])

        project = self._generate_project([pack])
        reused = project.implementation_control_ids.filtered(lambda line: line.control_id == self.controls[3])
        not_reused = project.implementation_control_ids.filtered(lambda line: line.control_id == self.controls[4])

        self.assertEqual(reused.control_instance_id, existing)
        self.assertNotEqual(not_reused.control_instance_id, other_org_instance)
        self.assertEqual(not_reused.control_instance_id.organization_id, self.organization)

    def test_task_completion_updates_activity_metrics_without_mutating_activity_definition(self):
        pack = self._create_pack("PM-TST-TASK", [self.controls[0]])
        project = self._generate_project([pack])
        line = project.implementation_control_ids[0]
        task = line.task_ids[0]
        original_activity_name = self.activity.name

        self.assertEqual(line.open_activity_count, 1)
        task.with_user(self.manager).write({"state": "1_done"})

        self.assertTrue(task.is_closed)
        self.assertEqual(line.completed_activity_count, 1)
        self.assertEqual(project.completed_tasks, 1)
        self.assertEqual(self.activity.name, original_activity_name)

    def test_activity_guided_semantics_and_administrative_invariant(self):
        activity = self.env["pm.qms.activity"].create(
            {
                "control_id": self.controls[2].id,
                "name": "Plan implementation communications",
                "objective": "Establish the communication plan for the implementation.",
                "why_it_matters": "The team needs a shared operating rhythm.",
                "implementation_steps": "Identify audiences, cadence, owners, and outputs.",
                "success_criteria": "The approved communication plan is available.",
            }
        )
        self.assertEqual(activity.activity_kind, "qms_implementation")
        self.assertTrue(activity.readiness_required)
        self.assertEqual(
            activity.objective,
            "Establish the communication plan for the implementation.",
        )
        self.assertEqual(
            activity.success_criteria,
            "The approved communication plan is available.",
        )

        activity.write(
            {
                "activity_kind": "project_administration",
                "readiness_required": True,
            }
        )
        self.assertFalse(activity.readiness_required)
        activity.write({"readiness_required": True})
        self.assertFalse(activity.readiness_required)

    def test_generated_task_required_flag_respects_activity_semantics(self):
        non_readiness = self.env["pm.qms.activity"].create(
            {
                "control_id": self.controls[3].id,
                "name": "Schedule implementation check-in",
                "activity_kind": "project_administration",
            }
        )
        self.assertFalse(non_readiness.readiness_required)
        optional_control = self.controls[1]
        pack = self._create_pack(
            "PM-TST-ACTIVITY-SEMANTICS",
            self.controls[:4],
            required={optional_control.id: False},
        )
        project = self._generate_project([pack])
        tasks = {
            task.pm_activity_id.id: task
            for task in project.generated_task_ids
        }

        required_task = tasks[self.activity.id]
        optional_task = tasks[self.second_activity.id]
        non_readiness_task = tasks[non_readiness.id]
        self.assertTrue(required_task.pm_required)
        self.assertFalse(optional_task.pm_required)
        self.assertFalse(non_readiness_task.pm_required)

        line = project.implementation_control_ids.filtered(
            lambda item: item.control_id == self.controls[0]
        )
        line.write({"required": False})
        self.assertFalse(required_task.pm_required)
        line.write({"required": True})
        self.assertTrue(required_task.pm_required)

        non_readiness_line = project.implementation_control_ids.filtered(
            lambda item: item.control_id == self.controls[3]
        )
        non_readiness_line.control_instance_id.with_user(self.manager).action_mark_in_progress()
        before = non_readiness_line.readiness_state
        non_readiness_task.with_user(self.manager).write({"state": "1_done"})
        self.assertEqual(non_readiness_line.readiness_state, before)
        self.assertEqual(non_readiness_line.open_activity_count, 0)

    def test_activity_actions_preserve_qms_context_and_project_task_engine(self):
        pack = self._create_pack("PM-TST-ACTUX", [self.controls[0]])
        project = self._generate_project([pack])
        line = project.implementation_control_ids[0]
        task = line.task_ids[0]
        qms_activity_action = self.env.ref("pm_qms_implementation.action_pm_qms_implementation_activities")

        self.assertEqual(task._name, "project.task")
        self.assertFalse(self.env["ir.model"].search([("model", "=", "pm.qms.task")]))
        self.assertEqual(self.env["ir.actions.actions"]._for_xml_id("project.action_view_task")["res_model"], "project.task")

        control_action = line.action_open_tasks()
        self.assertEqual(control_action["id"], qms_activity_action.id)
        self.assertEqual(control_action["res_model"], "project.task")
        self.assertIn(("pm_implementation_project_id", "=", project.id), control_action["domain"])
        self.assertIn(("pm_implementation_control_id", "=", line.id), control_action["domain"])
        self.assertIn(("pm_generated", "=", True), control_action["domain"])

        form_action = task.action_open_pm_qms_activity()
        self.assertEqual(form_action["id"], qms_activity_action.id)
        self.assertEqual(form_action["res_id"], task.id)
        self.assertEqual(form_action["views"][0], (self.env.ref("pm_qms_implementation.view_pm_qms_project_task_form").id, "form"))
        self.assertEqual(form_action["context"]["default_pm_implementation_project_id"], project.id)

        line.control_instance_id.with_user(self.manager).action_mark_implemented()
        self._accept_evidence(line)
        center = self.env["pm.qms.readiness.center"].with_user(self.manager).create(
            {"implementation_project_id": project.id}
        )
        recommended_activity = center.action_line_ids.filtered(lambda action: action.action_type == "activity")[:1]
        self.assertTrue(recommended_activity)
        readiness_action = recommended_activity.action_open_record()
        self.assertEqual(readiness_action["id"], qms_activity_action.id)
        self.assertEqual(readiness_action["res_id"], task.id)

        visible_task = self.env["project.task"].with_user(self.user).search([("id", "=", task.id)])
        self.assertEqual(visible_task, task)
        task.with_user(self.manager).write({"state": "1_done"})
        self.assertTrue(task.is_closed)

    def test_evidence_and_activity_drive_control_readiness(self):
        pack = self._create_pack("PM-TST-EVIDENCE", [self.controls[0]])
        project = self._generate_project([pack])
        line = project.implementation_control_ids[0]

        line.control_instance_id.with_user(self.manager).action_mark_implemented()
        self.assertEqual(line.readiness_state, "gap")
        self.assertEqual(line.gap_reason, "missing_evidence")

        self._accept_evidence(line)
        self.assertEqual(line.readiness_state, "partial")
        self.assertEqual(line.gap_reason, "open_required_activities")

        line.task_ids.with_user(self.manager).write({"state": "1_done"})
        self.assertEqual(line.readiness_state, "ready")
        self.assertEqual(project.readiness_percent, 100.0)

    def test_not_applicable_controls_are_excluded_from_readiness_denominator(self):
        pack = self._create_pack("PM-TST-NA", self.controls[2:12])
        project = self._generate_project([pack])
        lines = project.implementation_control_ids.sorted("sequence")

        for line in lines[:6]:
            line.control_instance_id.with_user(self.manager).action_mark_implemented()
        for line in lines[6:8]:
            line.control_instance_id.with_user(self.manager).write({"justification": "Not part of this demo scope."})
            line.control_instance_id.with_user(self.manager).action_mark_not_applicable()

        self.assertEqual(project.total_controls, 10)
        self.assertEqual(project.not_applicable_controls, 2)
        self.assertEqual(project.applicable_controls, 8)
        self.assertEqual(project.ready_controls, 6)
        self.assertAlmostEqual(project.readiness_percent, 75.0, places=2)

    def test_historical_readiness_assessment_is_immutable_after_live_improves(self):
        pack = self._create_pack("PM-TST-HIST", self.controls[5:9])
        project = self._generate_project([pack])
        lines = project.implementation_control_ids.sorted("sequence")

        for line in lines[:2]:
            line.control_instance_id.with_user(self.manager).action_mark_implemented()
        lines[2].control_instance_id.with_user(self.manager).write({"justification": "Excluded from this implementation."})
        lines[2].control_instance_id.with_user(self.manager).action_mark_not_applicable()

        action = project.with_user(self.manager).action_run_readiness_assessment()
        assessment = self.env["pm.qms.readiness.assessment"].browse(action["domain"][0][2])
        self.assertEqual(assessment.state, "completed")
        self.assertAlmostEqual(assessment.readiness_percent, 66.6667, places=2)
        gap_item = assessment.item_ids.filtered(lambda item: item.readiness_state_snapshot == "gap")
        self.assertEqual(len(gap_item), 1)

        lines[3].control_instance_id.with_user(self.manager).action_mark_implemented()
        self.assertEqual(project.readiness_percent, 100.0)
        self.assertAlmostEqual(assessment.readiness_percent, 66.6667, places=2)
        self.assertEqual(gap_item.readiness_state_snapshot, "gap")
        with self.assertRaises(AccessError):
            assessment.write({"notes": "Should not mutate completed snapshot."})
        with self.assertRaises(AccessError):
            gap_item.write({"notes": "Should not mutate completed item."})

    def test_multicompany_security_for_projects_controls_assessments_and_tasks(self):
        pack = self._create_pack("PM-TST-SEC", [self.controls[1]])
        project = self._generate_project([pack])
        action = project.with_user(self.manager).action_run_readiness_assessment()
        assessment = self.env["pm.qms.readiness.assessment"].browse(action["domain"][0][2])
        line = project.implementation_control_ids[0]
        task = project.generated_task_ids[:1]

        self.assertFalse(
            self.env["pm.qms.implementation.project"].with_user(self.other_user).search([("id", "=", project.id)])
        )
        self.assertFalse(
            self.env["pm.qms.implementation.control"].with_user(self.other_user).search([("id", "=", line.id)])
        )
        self.assertFalse(
            self.env["pm.qms.readiness.assessment"].with_user(self.other_user).search([("id", "=", assessment.id)])
        )
        self.assertFalse(
            self.env["pm.qms.readiness.assessment.item"].with_user(self.other_user).search(
                [("id", "in", assessment.item_ids.ids)]
            )
        )
        if task:
            self.assertFalse(self.env["project.task"].with_user(self.other_user).search([("id", "=", task.id)]))

    def test_completion_below_full_readiness_requires_justification_and_copy_is_blocked(self):
        pack = self._create_pack("PM-TST-COMPLETE", [self.controls[10]])
        project = self._generate_project([pack])

        project.with_user(self.manager).action_start_implementation()
        with self.assertRaises(UserError):
            project.with_user(self.manager).action_complete()

        project.with_user(self.manager).write({"completion_justification": "Closed with known residual implementation gap."})
        project.with_user(self.manager).action_complete()
        self.assertEqual(project.state, "completed")
        self.assertTrue(project.actual_completion_date)

        with self.assertRaises(UserError):
            project.copy()

    def test_pack_specific_areas_guidance_and_readiness_center(self):
        first_pack = self.env["pm.qms.framework.pack"].with_user(self.admin).create(
            {
                "name": "Area Pack A",
                "code": "PM-TST-AREA-A",
                "version": "1.0",
                "company_id": self.company.id,
            }
        )
        second_pack = self.env["pm.qms.framework.pack"].with_user(self.admin).create(
            {
                "name": "Area Pack B",
                "code": "PM-TST-AREA-B",
                "version": "1.0",
                "company_id": self.company.id,
            }
        )
        first_area = self.env["pm.qms.framework.area"].with_user(self.admin).create(
            {"name": "First Pack Area", "code": "FIRST", "pack_id": first_pack.id, "sequence": 10}
        )
        second_area = self.env["pm.qms.framework.area"].with_user(self.admin).create(
            {"name": "Second Pack Area", "code": "SECOND", "pack_id": second_pack.id, "sequence": 20}
        )
        self.controls[0].with_user(self.admin).write(
            {
                "guidance_purpose": "Use this control to keep implementation ownership visible.",
                "recommended_steps": "Confirm owner, collect evidence, and review readiness.",
            }
        )
        self.env["pm.qms.framework.pack.control"].with_user(self.admin).create(
            {"pack_id": first_pack.id, "control_id": self.controls[0].id, "area_id": first_area.id, "sequence": 20}
        )
        self.env["pm.qms.framework.pack.control"].with_user(self.admin).create(
            {"pack_id": second_pack.id, "control_id": self.controls[0].id, "area_id": second_area.id, "sequence": 10}
        )
        first_pack.with_user(self.admin).action_activate()
        second_pack.with_user(self.admin).action_activate()

        project = self._generate_project([first_pack, second_pack], name="Area Guided Implementation")
        self.assertEqual(len(project.implementation_control_ids), 1)
        line = project.implementation_control_ids
        self.assertEqual(set(line.pack_ids.ids), {first_pack.id, second_pack.id})
        self.assertEqual(set(line.area_ids.ids), {first_area.id, second_area.id})
        self.assertIn("First Pack Area", line.area_display)
        self.assertEqual(line.guidance_purpose, self.controls[0].guidance_purpose)

        line.control_instance_id.with_user(self.manager).write({"notes": "Client-specific note."})
        self.assertEqual(self.controls[0].guidance_purpose, "Use this control to keep implementation ownership visible.")

        center = self.env["pm.qms.readiness.center"].with_user(self.manager).create(
            {"implementation_project_id": project.id}
        )
        self.assertEqual(set(center.area_line_ids.mapped("area_id").ids), {first_area.id, second_area.id})
        self.assertTrue(center.action_line_ids.filtered(lambda action: action.implementation_control_id == line))
        self.assertEqual(project._recommended_next_action_values(limit=1)[0]["action_type"], "start_control")

        with self.assertRaises(UserError):
            self.env["pm.qms.framework.area"].with_user(self.manager).create(
                {"name": "Manager Cannot Author Framework Area", "code": "NOPE", "pack_id": first_pack.id}
            )

    def test_m25_8_not_applicable_excludes_live_readiness_components(self):
        pack = self._create_pack("PM-TST-NA-M258", [self.controls[0]])
        project = self._generate_project([pack])
        line = project.implementation_control_ids[0]
        self.assertEqual(line.required_evidence_count, 1)
        self.assertEqual(line.missing_evidence_count, 1)
        self.assertGreaterEqual(line.required_activity_count, 1)
        self.assertGreaterEqual(line.open_activity_count, 1)
        line.control_instance_id.with_user(self.manager).write({
            "justification": "Outside the fictional implementation scope."
        })
        line.control_instance_id.with_user(self.manager).action_mark_not_applicable()
        self.assertEqual(line.readiness_state, "not_applicable")
        self.assertEqual(line.required_evidence_count, 1)
        self.assertEqual(line.missing_evidence_count, 1)
        self.assertGreaterEqual(line.required_activity_count, 1)
        self.assertGreaterEqual(line.open_activity_count, 1)
        self.assertEqual(project.applicable_controls, 0)
        self.assertEqual(project.required_evidence, 0)
        self.assertEqual(project.open_tasks, 0)
        self.assertEqual(project.evidence_completion_percent, 100.0)
        self.assertEqual(project.activity_completion_percent, 100.0)
        action = project.with_user(self.manager).action_run_readiness_assessment()
        assessment = self.env["pm.qms.readiness.assessment"].browse(action["domain"][0][2])
        item = assessment.item_ids.filtered(lambda candidate: candidate.implementation_control_id == line)
        self.assertEqual(len(item), 1)
        self.assertEqual(item.required_evidence_snapshot, 1)
        self.assertEqual(item.missing_evidence_snapshot, 1)
        self.assertGreaterEqual(item.required_activity_snapshot, 1)
        self.assertGreaterEqual(item.open_activity_snapshot, 1)
        self.assertEqual(item.readiness_state_snapshot, "not_applicable")


    def test_m25_9_readiness_intelligence_precedence_and_routing(self):
        pack = self._create_pack("PM-TST-INTEL", [self.controls[0]])
        project = self._generate_project([pack])
        line = project.implementation_control_ids[0]

        values = line._readiness_intelligence_values()
        self.assertEqual(values["action_type"], "start_control")
        self.assertEqual(values["priority"], "high")
        self.assertIn("Implementation has not started", values["blocker_summary"])

        line.control_instance_id.with_user(self.manager).action_mark_implemented()
        values = line._readiness_intelligence_values()
        self.assertEqual(values["action_type"], "activity")
        self.assertEqual(values["res_model"], "project.task")
        self.assertEqual(values["res_id"], values["task_id"])
        self.assertIn("evidence requirement", values["blocker_summary"])

        line.task_ids.with_user(self.manager).write({"state": "1_done"})
        evidence = self.env["pm.qms.evidence"].with_user(self.manager).create({
            "name": "Under review implementation evidence",
            "control_instance_id": line.control_instance_id.id,
            "evidence_requirement_id": self.evidence_requirement.id,
            "state": "under_review",
        })
        values = line._readiness_intelligence_values()
        self.assertEqual(values["action_type"], "review_evidence")
        self.assertEqual(values["evidence_id"], evidence.id)
        self.assertEqual(values["res_id"], evidence.id)
        self.assertEqual(values["res_model"], "pm.qms.evidence")
        action = project._recommended_next_action_values(limit=1)[0]
        self.assertEqual(action["evidence_id"], evidence.id)
        self.assertEqual(action["done_when"], "The evidence meets the requirement acceptance criteria and is reviewed.")

    def test_m25_9_rejected_evidence_routes_to_exact_record(self):
        pack = self._create_pack("PM-TST-REJECTED", [self.controls[0]])
        project = self._generate_project([pack])
        line = project.implementation_control_ids[0]
        line.control_instance_id.with_user(self.manager).action_mark_implemented()
        line.task_ids.with_user(self.manager).write({"state": "1_done"})
        evidence = self.env["pm.qms.evidence"].with_user(self.manager).create({
            "name": "Rejected implementation evidence",
            "control_instance_id": line.control_instance_id.id,
            "evidence_requirement_id": self.evidence_requirement.id,
            "state": "rejected",
        })

        values = line._readiness_intelligence_values()
        self.assertEqual(values["action_type"], "evidence_correction")
        self.assertEqual(values["priority"], "high")
        self.assertEqual(values["evidence_id"], evidence.id)
        center = self.env["pm.qms.readiness.center"].with_user(self.manager).create({
            "implementation_project_id": project.id,
        })
        action = center.action_line_ids[:1]
        self.assertEqual(action.evidence_id, evidence)
        opened = action.action_open_record()
        self.assertEqual(opened["res_model"], "pm.qms.evidence")
        self.assertEqual(opened["res_id"], evidence.id)

    def test_m25_9_readiness_snapshots_include_intelligence(self):
        pack = self._create_pack("PM-TST-SNAPSHOT", [self.controls[0]])
        project = self._generate_project([pack])
        action = project.with_user(self.manager).action_run_readiness_assessment()
        assessment = self.env["pm.qms.readiness.assessment"].browse(
            action["domain"][0][2]
        )
        item = assessment.item_ids[0]
        self.assertEqual(assessment.state, "completed")
        self.assertTrue(item.blocker_summary_snapshot)
        self.assertTrue(item.recommended_next_action_snapshot)
        self.assertTrue(item.recommended_done_when_snapshot)
        blocker = item.blocker_summary_snapshot
        project.implementation_control_ids[0].control_instance_id.with_user(
            self.manager
        ).action_mark_implemented()
        self.assertEqual(item.blocker_summary_snapshot, blocker)


    def test_m25_9_ready_and_not_applicable_controls_have_no_action(self):
        pack = self._create_pack("PM-TST-NO-ACTION", self.controls[:2])
        project = self._generate_project([pack])
        first, second = project.implementation_control_ids.sorted("sequence")
        self._mark_ready(first)
        second.control_instance_id.with_user(self.manager).write({
            "justification": "Excluded from the fictional scope."
        })
        second.control_instance_id.with_user(self.manager).action_mark_not_applicable()

        actions = project._recommended_next_action_values()
        self.assertFalse(
            any(action["implementation_control_id"] == first.id for action in actions)
        )
        self.assertFalse(
            any(action["implementation_control_id"] == second.id for action in actions)
        )
