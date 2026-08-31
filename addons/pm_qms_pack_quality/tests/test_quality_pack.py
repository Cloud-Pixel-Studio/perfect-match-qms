import base64

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_pack_quality.hooks import seed_quality_guided_readiness


@tagged("-at_install", "post_install")
class TestPmQmsQualityPack(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Quality Pack Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.qms_admin_group = cls.env.ref("pm_qms_core.group_pm_qms_administrator")
        cls.manager = cls._create_test_user("quality_manager", cls.qms_manager_group)
        cls.admin = cls._create_test_user("quality_admin", cls.qms_admin_group)
        cls.other_user = cls._create_test_user("quality_other", cls.qms_user_group, cls.other_company)
        cls.other_admin = cls._create_test_user("quality_other_admin", cls.qms_admin_group, cls.other_company)

        cls.quality_pack = cls.env["pm.qms.framework.pack"].search(
            [
                ("code", "=", "PM-QMS-QUALITY"),
                ("version", "=", "1.0"),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "Quality Demo Organization", "code": "PM-QUAL-DEMO", "company_id": cls.company.id}
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

    def _csv_payload(self, rows):
        header = "pm_control_code,standard_name,edition,reference,mapping_type,review_status,reviewed_by,review_date,notes"
        body = "\n".join(",".join(row) for row in rows)
        return base64.b64encode(f"{header}\n{body}\n".encode()).decode()

    def _example_profile(self, suffix="A"):
        profile = self.env["pm.qms.mapping.profile"].with_user(self.admin).create(
            {
                "name": f"Example Standard Mapping {suffix}",
                "code": f"PM-QMS-QUALITY-EXAMPLE-{suffix}",
                "company_id": self.company.id,
                "pack_id": self.quality_pack.id,
                "standard_name": "Example Standard",
                "edition": f"Edition {suffix}",
                "publisher": "Example Publisher",
                "notes": "Human-approved example mapping metadata for tests only.",
            }
        )
        profile.with_user(self.admin).action_activate()
        return profile

    def _generate_project(self, packs=None):
        packs = packs or self.quality_pack
        wizard = self.env["pm.qms.project.generator.wizard"].with_user(self.manager).create(
            {
                "name": "Quality Pack Demo Implementation",
                "company_id": self.company.id,
                "organization_id": self.organization.id,
                "project_manager_id": self.manager.id,
                "date_start": "2026-08-15",
                "target_date": "2026-11-30",
                "implementation_type": "new_implementation",
                "pack_ids": [Command.set(packs.ids)],
                "create_odoo_project": True,
            }
        )
        action = wizard.action_generate_implementation()
        return self.env["pm.qms.implementation.project"].browse(action["res_id"])

    def _mark_line_ready(self, line):
        line.control_instance_id.with_user(self.manager).action_mark_implemented()
        for requirement in line.control_id.evidence_requirement_ids.filtered(lambda req: req.mandatory and req.active):
            evidence = self.env["pm.qms.evidence"].with_user(self.manager).create(
                {
                    "name": f"Accepted evidence for {line.control_id.code}",
                    "control_instance_id": line.control_instance_id.id,
                    "evidence_requirement_id": requirement.id,
                }
            )
            evidence.action_submit()
            evidence.action_accept()
        line.task_ids.filtered(lambda task: task.pm_required).with_user(self.manager).write({"state": "1_done"})

    def test_quality_pack_seed_structure_and_content_quality(self):
        self.assertTrue(self.quality_pack)
        self.assertEqual(self.quality_pack.state, "active")
        self.assertEqual(self.quality_pack.pack_type, "standard")
        controls = self.quality_pack.control_line_ids.mapped("control_id")
        self.assertEqual(len(controls), 37)
        quality_activities = controls.mapped("implementation_activity_ids").filtered(
            lambda activity: not activity.applicable_pack_ids
            or self.quality_pack in activity.applicable_pack_ids
        )
        self.assertEqual(len(quality_activities.filtered("active")), 74)
        self.assertEqual(len(controls.mapped("evidence_requirement_ids").filtered(lambda req: req.active and req.mandatory)), 37)
        self.assertEqual(len(controls.mapped("code")), len(set(controls.mapped("code"))))
        self.assertGreaterEqual(self.quality_pack.area_count, 6)
        self.assertFalse(self.quality_pack.control_line_ids.filtered(lambda line: not line.area_id))

        forbidden = ("ISO requires", "This International Standard", "certification guarantee", "certification probability")
        for control in controls:
            self.assertTrue(control.objective, control.code)
            self.assertTrue(control.description, control.code)
            self.assertTrue(control.pm_control_domain, control.code)
            self.assertTrue(control.pm_supported_capability, control.code)
            self.assertTrue(control.guidance_purpose, control.code)
            self.assertTrue(control.implementation_guidance, control.code)
            self.assertTrue(control.evidence_guidance, control.code)
            self.assertTrue(control.implementation_activity_ids.filtered("active"), control.code)
            self.assertTrue(control.evidence_requirement_ids.filtered(lambda req: req.active and req.mandatory), control.code)
            combined = " ".join(
                [
                    control.name or "",
                    control.objective or "",
                    control.description or "",
                    " ".join(control.implementation_activity_ids.mapped("name")),
                    " ".join(control.evidence_requirement_ids.mapped("name")),
                ]
            )
            for pattern in forbidden:
                self.assertNotIn(pattern, combined)

        with self.assertRaises(UserError):
            self.quality_pack.control_line_ids[:1].with_user(self.admin).write({"required": False})

    def test_mapping_profile_infrastructure_stays_standard_neutral(self):
        profile = self._example_profile("NEUTRAL")
        self.assertEqual(profile.state, "active")
        self.assertEqual(profile.standard_name, "Example Standard")
        self.assertEqual(profile.mapped_control_count, 0)
        self.assertEqual(profile.mapping_completeness_percent, 0.0)

    def test_mapping_import_validation_approval_and_security(self):
        profile = self._example_profile()
        controls = self.quality_pack.control_line_ids.mapped("control_id").sorted("code")
        payload = self._csv_payload(
            [
                [
                    controls[0].code,
                    "Example Standard",
                    "Edition A",
                    "X.1",
                    "direct",
                    "approved",
                    self.admin.login,
                    "2026-08-15",
                    "Human reviewed metadata.",
                ],
                [
                    controls[1].code,
                    "Example Standard",
                    "Edition A",
                    "X.2",
                    "supporting",
                    "reviewed",
                    self.admin.login,
                    "2026-08-15",
                    "Human reviewed metadata.",
                ],
            ]
        )
        wizard = self.env["pm.qms.mapping.import.wizard"].with_user(self.admin).create(
            {"mapping_profile_id": profile.id, "csv_file": payload, "filename": "approved.csv"}
        )
        wizard.action_import()
        self.assertEqual(profile.mapped_control_count, 1)
        self.assertEqual(profile.pending_mapping_count, 1)

        with self.assertRaises(AccessError):
            self.env["pm.qms.external.mapping"].with_user(self.manager).create(
                {
                    "mapping_profile_id": profile.id,
                    "control_id": controls[2].id,
                    "reference": "X.3",
                    "mapping_type": "partial",
                }
            )

        reviewed = profile.mapping_ids.filtered(lambda mapping: mapping.review_status == "reviewed")
        reviewed.with_user(self.admin).action_approve()
        self.assertEqual(profile.mapped_control_count, 2)

        duplicate = self.env["pm.qms.mapping.import.wizard"].with_user(self.admin).create(
            {"mapping_profile_id": profile.id, "csv_file": payload, "filename": "duplicate.csv"}
        )
        with self.assertRaises(UserError):
            duplicate.action_import()

    def test_mapping_import_rejects_text_columns_and_missing_references(self):
        profile = self._example_profile("B")
        controls = self.quality_pack.control_line_ids.mapped("control_id").sorted("code")
        bad_header = (
            "pm_control_code,standard_name,edition,reference,mapping_type,review_status,reviewed_by,review_date,notes,requirement_text\n"
        )
        bad_row = f"{controls[0].code},Example Standard,Edition B,X.1,direct,draft,,,,Not allowed\n"
        wizard = self.env["pm.qms.mapping.import.wizard"].with_user(self.admin).create(
            {
                "mapping_profile_id": profile.id,
                "csv_file": base64.b64encode((bad_header + bad_row).encode()).decode(),
                "filename": "bad.csv",
            }
        )
        with self.assertRaises(UserError):
            wizard.action_import()

        missing_reference = self._csv_payload(
            [[controls[0].code, "Example Standard", "Edition B", "", "direct", "draft", "", "", ""]]
        )
        wizard = self.env["pm.qms.mapping.import.wizard"].with_user(self.admin).create(
            {"mapping_profile_id": profile.id, "csv_file": missing_reference, "filename": "missing.csv"}
        )
        with self.assertRaises(UserError):
            wizard.action_import()

    def test_quality_pack_generates_project_tasks_and_readiness(self):
        project = self._generate_project()
        controls = self.quality_pack.control_line_ids.mapped("control_id")
        quality_activities = controls.mapped("implementation_activity_ids").filtered(
            lambda activity: not activity.applicable_pack_ids
            or self.quality_pack in activity.applicable_pack_ids
        )
        self.assertEqual(project.state, "generated")
        self.assertEqual(len(project.implementation_control_ids), len(controls))
        self.assertEqual(project.total_generated_tasks, len(quality_activities.filtered("active")))
        self.assertEqual(project.readiness_percent, 0.0)
        self.assertFalse(project.implementation_control_ids.filtered(lambda line: not line.area_ids))
        center = self.env["pm.qms.readiness.center"].with_user(self.manager).create(
            {"implementation_project_id": project.id}
        )
        self.assertEqual(len(center.area_line_ids), self.quality_pack.area_count)
        self.assertTrue(center.action_line_ids)

        lines = project.implementation_control_ids.sorted("sequence")
        self._mark_line_ready(lines[0])
        lines[1].control_instance_id.with_user(self.manager).write({"justification": "Not part of this fictional demo scope."})
        lines[1].control_instance_id.with_user(self.manager).action_mark_not_applicable()
        self.assertEqual(lines[0].readiness_state, "ready")
        self.assertEqual(lines[1].readiness_state, "not_applicable")
        self.assertEqual(project.not_applicable_controls, 1)
        self.assertGreater(project.readiness_percent, 0.0)
        self.assertLess(project.readiness_percent, 100.0)

    def test_quality_guided_seed_syncs_existing_project_areas(self):
        project = self._generate_project()
        project.implementation_control_ids.write({"area_ids": [Command.clear()]})
        self.assertTrue(project.implementation_control_ids.filtered(lambda line: not line.area_ids))

        seed_quality_guided_readiness(self.env)

        self.assertFalse(project.implementation_control_ids.filtered(lambda line: not line.area_ids))
        center = self.env["pm.qms.readiness.center"].with_user(self.manager).create(
            {"implementation_project_id": project.id}
        )
        self.assertEqual(len(center.area_line_ids), self.quality_pack.area_count)

    def test_shared_control_deduplication_with_quality_pack(self):
        shared_control = self.quality_pack.control_line_ids.mapped("control_id").sorted("code")[0]
        second_pack = self.env["pm.qms.framework.pack"].with_user(self.admin).create(
            {
                "name": "Fictional Shared Control Pack",
                "code": "PM-QMS-SHARED-TEST",
                "version": "1.0",
                "company_id": self.company.id,
                "pack_type": "custom",
            }
        )
        self.env["pm.qms.framework.pack.control"].with_user(self.admin).create(
            {"pack_id": second_pack.id, "control_id": shared_control.id, "sequence": 10, "required": True}
        )
        second_pack.with_user(self.admin).action_activate()

        project = self._generate_project(self.quality_pack | second_pack)
        shared_lines = project.implementation_control_ids.filtered(lambda line: line.control_id == shared_control)
        self.assertEqual(len(shared_lines), 1)
        self.assertEqual(set(shared_lines.pack_ids.ids), {self.quality_pack.id, second_pack.id})
        self.assertEqual(
            self.env["pm.qms.control.instance"].search_count(
                [("organization_id", "=", self.organization.id), ("control_id", "=", shared_control.id)]
            ),
            1,
        )

    def test_historical_readiness_assessment_remains_immutable_after_live_changes(self):
        project = self._generate_project()
        lines = project.implementation_control_ids.sorted("sequence")
        self._mark_line_ready(lines[0])
        action = project.with_user(self.manager).action_run_readiness_assessment()
        assessment = self.env["pm.qms.readiness.assessment"].browse(action["domain"][0][2])
        original_percent = assessment.readiness_percent
        original_gap_count = assessment.gap_controls

        self._mark_line_ready(lines[1])
        self.assertGreater(project.readiness_percent, original_percent)
        self.assertEqual(assessment.readiness_percent, original_percent)
        self.assertEqual(assessment.gap_controls, original_gap_count)
        with self.assertRaises(AccessError):
            assessment.write({"notes": "Do not rewrite history."})

    def test_mapping_metadata_does_not_own_operational_execution_records(self):
        profile_v1 = self._example_profile("C1")
        profile_v2 = self._example_profile("C2")
        control = self.quality_pack.control_line_ids.mapped("control_id").sorted("code")[0]
        self.env["pm.qms.external.mapping"].with_user(self.admin).create(
            {
                "mapping_profile_id": profile_v1.id,
                "control_id": control.id,
                "reference": "A.1",
                "mapping_type": "direct",
            }
        ).action_approve()
        project = self._generate_project()
        line = project.implementation_control_ids.filtered(lambda item: item.control_id == control)
        self._mark_line_ready(line)
        evidence_count = self.env["pm.qms.evidence"].search_count([("control_instance_id", "=", line.control_instance_id.id)])

        self.env["pm.qms.external.mapping"].with_user(self.admin).create(
            {
                "mapping_profile_id": profile_v2.id,
                "control_id": control.id,
                "reference": "B.1",
                "mapping_type": "supporting",
            }
        ).action_approve()
        self.assertEqual(line.control_instance_id.implementation_status, "implemented")
        self.assertEqual(
            self.env["pm.qms.evidence"].search_count([("control_instance_id", "=", line.control_instance_id.id)]),
            evidence_count,
        )
        self.assertEqual(line.readiness_state, "ready")

    def test_multicompany_mapping_and_pack_isolation(self):
        profile = self._example_profile("COMPANY")
        self.assertFalse(
            self.env["pm.qms.mapping.profile"].with_user(self.other_user).search([("id", "=", profile.id)])
        )
        self.assertFalse(
            self.env["pm.qms.framework.pack"].with_user(self.other_user).search([("id", "=", self.quality_pack.id)])
        )
        project = self._generate_project()
        self.assertFalse(
            self.env["pm.qms.implementation.project"].with_user(self.other_user).search([("id", "=", project.id)])
        )

    def test_viewer_mapping_and_profile_access_stays_read_only_and_company_bound(self):
        profile_a = self._example_profile("VIEWER-A")
        control_a = self.quality_pack.control_line_ids.sorted("id")[0].control_id
        mapping_a = self.env["pm.qms.external.mapping"].with_user(self.admin).create(
            {
                "mapping_profile_id": profile_a.id,
                "control_id": control_a.id,
                "reference": "VIEW-A-1",
                "mapping_type": "supporting",
            }
        )

        organization_b = self.env["pm.qms.organization"].with_user(self.other_admin).create(
            {"name": "Viewer Boundary Organization B", "code": "VIEWER-B-ORG", "company_id": self.other_company.id}
        )
        process_b = self.env["pm.qms.process"].with_user(self.other_admin).create(
            {
                "name": "Viewer Boundary Process B",
                "code": "VIEWER-B-PROC",
                "organization_id": organization_b.id,
                "company_id": self.other_company.id,
            }
        )
        control_b = self.env["pm.qms.control"].with_user(self.other_admin).create(
            {
                "name": "Viewer Boundary Control B",
                "code": "VIEWER-B-CTRL",
                "objective": "A fictional cross-company control for access tests.",
                "process_id": process_b.id,
                "category": "process",
            }
        )
        control_b.with_user(self.other_admin).action_activate()
        pack_b = self.env["pm.qms.framework.pack"].with_user(self.other_admin).create(
            {
                "name": "Viewer Boundary Pack B",
                "code": "VIEWER-B-PACK",
                "version": "1.0",
                "company_id": self.other_company.id,
                "pack_type": "standard",
            }
        )
        self.env["pm.qms.framework.pack.control"].with_user(self.other_admin).create(
            {"pack_id": pack_b.id, "control_id": control_b.id, "sequence": 10, "required": True}
        )
        pack_b.with_user(self.other_admin).action_activate()
        profile_b = self.env["pm.qms.mapping.profile"].with_user(self.other_admin).create(
            {
                "name": "Viewer Boundary Profile B",
                "code": "VIEWER-B-PROFILE",
                "company_id": self.other_company.id,
                "pack_id": pack_b.id,
                "standard_name": "Fictional Standard",
                "edition": "Edition B",
                "publisher": "Fictional Publisher",
            }
        )
        profile_b.with_user(self.other_admin).action_activate()
        mapping_b = self.env["pm.qms.external.mapping"].with_user(self.other_admin).create(
            {
                "mapping_profile_id": profile_b.id,
                "control_id": control_b.id,
                "reference": "VIEW-B-1",
                "mapping_type": "supporting",
            }
        )

        viewer = self._create_test_user("quality_viewer_boundary", self.env.ref("pm_qms_core.group_qms_viewer"))
        profile_model = self.env["pm.qms.mapping.profile"].with_user(viewer)
        mapping_model = self.env["pm.qms.external.mapping"].with_user(viewer)
        self.assertEqual(profile_model.search_count([("id", "=", profile_a.id)]), 1)
        self.assertEqual(profile_model.search_count([("id", "=", profile_b.id)]), 0)
        self.assertEqual(mapping_model.search_count([("id", "=", mapping_a.id)]), 1)
        self.assertEqual(mapping_model.search_count([("id", "=", mapping_b.id)]), 0)
        with self.assertRaises(AccessError):
            mapping_model.create(
                {
                    "mapping_profile_id": profile_a.id,
                    "control_id": control_a.id,
                    "reference": "VIEW-A-DENIED",
                }
            )
        with self.assertRaises(AccessError):
            mapping_a.write({"note": "Viewer cannot write mappings."})
        with self.assertRaises(AccessError):
            mapping_a.unlink()

    def test_m25_8_quality_requirements_have_stable_keys_and_criteria(self):
        requirements = self.quality_pack.control_line_ids.mapped(
            "control_id.evidence_requirement_ids"
        ).filtered(lambda requirement: requirement.active and requirement.mandatory)
        self.assertEqual(len(requirements), 37)
        self.assertEqual(len(set(requirements.mapped("definition_key"))), 37)
        criteria_by_code = {
            requirement.control_id.code: tuple(
                line.strip()
                for line in (requirement.acceptance_criteria or "").splitlines()
                if line.strip()
            )
            for requirement in requirements
        }
        self.assertEqual(len(criteria_by_code), 37)
        self.assertTrue(all(2 <= len(criteria) <= 5 for criteria in criteria_by_code.values()))
        self.assertEqual(len(set(criteria_by_code.values())), 37)
        semantic_indicators = {
            "PM-QMP-CMP-001": ("competence", "capability"),
            "PM-QMP-AWR-001": ("awareness", "communicated"),
            "PM-QMP-DSG-001": ("design", "applicable"),
            "PM-QMP-OPS-002": ("instructions", "current"),
            "PM-QMP-TRC-001": ("traceability", "identification"),
            "PM-QMP-PROP-001": ("property", "protection"),
            "PM-QMP-PRE-001": ("preservation", "handling", "storage"),
            "PM-QMP-CUST-001": ("customer", "requirement", "captured"),
            "PM-QMP-REQ-001": ("review", "commitment", "capability", "feasibility", "decision"),
            "PM-QMP-SUP-001": ("supplier", "qualification"),
            "PM-QMP-SUP-002": ("provider", "monitoring"),
            "PM-QMP-SAT-001": ("customer", "perception"),
            "PM-QMP-AUD-001": ("audit", "findings"),
            "PM-QMP-MRV-001": ("leadership", "decisions"),
        }
        for code, indicators in semantic_indicators.items():
            content = " ".join(criteria_by_code[code]).lower()
            for indicator in indicators:
                self.assertIn(indicator, content)
        for code in ("PM-QMP-NCO-001", "PM-QMP-NCR-001", "PM-QMP-RCA-001", "PM-QMP-CAPA-001"):
            self.assertIn("genuine", " ".join(criteria_by_code[code]).lower())

        pre_content = " ".join(criteria_by_code["PM-QMP-PRE-001"]).lower()
        self.assertNotIn("operational readiness", pre_content)
        self.assertNotIn("prerequisites before work", pre_content)

        customer_content = " ".join(criteria_by_code["PM-QMP-CUST-001"]).lower()
        requirement_review_content = " ".join(criteria_by_code["PM-QMP-REQ-001"]).lower()
        self.assertIn("capture", customer_content)
        for forbidden in ("feasibility", "capacity", "acceptance decision"):
            self.assertNotIn(forbidden, customer_content)
        self.assertIn("review", requirement_review_content)
        self.assertIn("commitment", requirement_review_content)
        self.assertIn("decision", requirement_review_content)
        self.assertNotEqual(customer_content, requirement_review_content)

        combined = " ".join(" ".join(criteria) for criteria in criteria_by_code.values()).lower()
        for forbidden in ("iso 14001", "iso 45001", "certification guarantee", "raw prompt"):
            self.assertNotIn(forbidden, combined)
