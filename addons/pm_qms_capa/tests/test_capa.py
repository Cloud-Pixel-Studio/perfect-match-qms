from lxml import etree

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_capa.models.capa_fishbone import FISHBONE_CATEGORIES, FISHBONE_GUIDANCE
from odoo.addons.pm_qms_capa.models.capa_is_is_not import IS_IS_NOT_PROMPTS
from odoo.addons.pm_qms_capa.models.capa_why import WHY_PROMPTS


@tagged("-at_install", "post_install")
class TestPmQmsCapa(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "CAPA Other Company"})
        cls.base_user_group = cls.env.ref("base.group_user")
        cls.qms_user_group = cls.env.ref("pm_qms_core.group_pm_qms_user")
        cls.qms_manager_group = cls.env.ref("pm_qms_core.group_pm_qms_manager")
        cls.organization = cls.env["pm.qms.organization"].create(
            {"name": "CAPA Organization", "code": "PM-CAPA-ORG", "company_id": cls.company.id}
        )
        cls.process = cls.env["pm.qms.process"].create(
            {
                "name": "CAPA Process",
                "code": "PM-CAPA-PROC",
                "organization_id": cls.organization.id,
                "company_id": cls.company.id,
            }
        )
        cls.control = cls.env["pm.qms.control"].create(
            {
                "name": "CAPA Control",
                "code": "PM-QMS-CAPA-001",
                "objective": "Define corrective action verification.",
                "process_id": cls.process.id,
            }
        )
        cls.requirement = cls.env["pm.qms.evidence.requirement"].create(
            {"name": "CAPA evidence requirement", "control_id": cls.control.id, "evidence_type": "record"}
        )
        cls.control_instance = cls.env["pm.qms.control.instance"].create(
            {
                "name": "CAPA implementation",
                "code": "CAPA-PM-QMS-001",
                "control_id": cls.control.id,
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
            }
        )
        cls.document = cls.env["pm.qms.document"].create(
            {
                "name": "CAPA Procedure",
                "code": "PM-CAPA-DOC-001",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "document_type": "procedure",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
            }
        )
        cls.evidence = cls.env["pm.qms.evidence"].create(
            {
                "name": "CAPA evidence",
                "control_instance_id": cls.control_instance.id,
                "evidence_requirement_id": cls.requirement.id,
                "document_ids": [(6, 0, [cls.document.id])],
            }
        )
        cls.risk = cls.env["pm.qms.risk"].create(
            {
                "name": "CAPA source risk",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "description": "Risk requiring action.",
                "mitigation_plan": "Create a corrective action plan.",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
                "related_document_ids": [(6, 0, [cls.document.id])],
            }
        )
        cls.ncr = cls.env["pm.qms.nonconformity"].create(
            {
                "name": "CAPA source NCR",
                "organization_id": cls.organization.id,
                "process_id": cls.process.id,
                "source_type": "document",
                "severity": "major",
                "description": "A superseded instruction was found.",
                "related_control_instance_ids": [(6, 0, [cls.control_instance.id])],
                "related_document_ids": [(6, 0, [cls.document.id])],
                "related_evidence_ids": [(6, 0, [cls.evidence.id])],
                "related_risk_ids": [(6, 0, [cls.risk.id])],
            }
        )
        cls.other_organization = cls.env["pm.qms.organization"].create(
            {"name": "Other CAPA Organization", "code": "PM-CAPA-ORG2", "company_id": cls.other_company.id}
        )
        cls.other_process = cls.env["pm.qms.process"].create(
            {
                "name": "Other CAPA Process",
                "code": "PM-CAPA-PROC2",
                "organization_id": cls.other_organization.id,
                "company_id": cls.other_company.id,
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
                "company_ids": [(6, 0, [company.id])],
                "group_ids": [(6, 0, [cls.base_user_group.id, group.id])],
            }
        )

    def _capa_values(self, **extra_values):
        values = {
            "name": "Distribution verification CAPA",
            "organization_id": self.organization.id,
            "process_id": self.process.id,
            "source_type": "other",
            "problem_statement": "Distribution verification needs a clear owner.",
            "root_cause_method": "5why",
            "root_cause_analysis": "The analysis identified a missing ownership control.",
            "root_cause": "The recurring owner was not assigned.",
            "action_plan": "Assign owner and verify completion.",
            "target_date": "2026-01-01",
            "effectiveness_review_date": "2026-01-15",
            "related_control_instance_ids": [(6, 0, [self.control_instance.id])],
            "related_document_ids": [(6, 0, [self.document.id])],
        }
        values.update(extra_values)
        return values

    def test_capa_why_inline_list_shows_analysis_columns(self):
        view = self.env.ref("pm_qms_capa.view_pm_qms_capa_form")
        arch = etree.fromstring(view.arch_db.encode())
        why_field = arch.xpath("//field[@name='why_ids']")
        self.assertTrue(why_field)
        why_list = why_field[0].xpath("./list")
        self.assertTrue(why_list)
        columns = why_list[0].xpath("./field/@name")
        self.assertEqual(columns, ["sequence", "prompt", "answer"])
        self.assertNotIn("question", columns)
        self.assertEqual(why_list[0].get("create"), "0")
        self.assertEqual(why_list[0].get("delete"), "0")

    def test_legacy_question_is_preserved_while_prompt_is_canonical(self):
        manager = self._create_test_user("pmqms.capa.legacy_prompt", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values(name="Legacy prompt"))
        capa.with_user(manager).action_start_analysis()
        legacy = capa.why_ids.filtered(lambda row: row.sequence == 1)
        self.env.cr.execute(
            "UPDATE pm_qms_capa_why SET question = %s WHERE id = %s",
            ("Why is it happening?", legacy.id),
        )
        self.env.invalidate_all()
        legacy = self.env["pm.qms.capa.why"].browse(legacy.id)
        self.assertEqual(legacy.question, "Why is it happening?")
        self.assertEqual(legacy.prompt, WHY_PROMPTS[1])
        self.assertEqual(capa.why_ids.mapped("prompt"), [WHY_PROMPTS[i] for i in range(1, 6)])
        self.assertTrue(self.env["pm.qms.capa.why"]._fields["prompt"].readonly)

    def test_rca_methodology_views_expose_specific_guidance(self):
        view = self.env.ref("pm_qms_capa.view_pm_qms_capa_form")
        arch = etree.fromstring(view.arch_db.encode())

        fishbone_field = arch.xpath("//field[@name='fishbone_ids']")[0]
        fishbone_columns = fishbone_field.xpath("./list/field/@name")
        self.assertEqual(
            fishbone_columns,
            ["category", "guidance", "potential_cause", "evidence_basis", "investigation_status", "rationale_finding"],
        )

        is_is_not_field = arch.xpath("//field[@name='is_is_not_ids']")[0]
        is_is_not_form_fields = is_is_not_field.xpath("./form//field/@name")
        self.assertEqual(
            set(is_is_not_form_fields),
            {
                "dimension",
                "sequence",
                "is_prompt",
                "is_value",
                "is_not_prompt",
                "is_not_value",
                "distinction_prompt",
                "distinction",
                "change_prompt",
                "change_value",
            },
        )

    def test_draft_rca_view_explains_start_workflow_and_hides_working_areas(self):
        view = self.env.ref("pm_qms_capa.view_pm_qms_capa_form")
        arch = etree.fromstring(view.arch_db.encode())

        start_buttons = arch.xpath("//header/button[@name='action_start_analysis']")
        self.assertEqual(len(start_buttons), 1)
        self.assertEqual(start_buttons[0].get("string"), "Start Root Cause Analysis")
        self.assertNotEqual(start_buttons[0].get("string"), "Analyze")

        expected_guidance = {
            "5 Why selected": "five fixed Why steps",
            "Fishbone selected": "People, Machine / Equipment",
            "Is / Is Not selected": "What, Where, When, and Extent",
            "Other method selected": "method or tool used",
        }
        for title, guidance in expected_guidance.items():
            groups = arch.xpath(f"//group[@string={title!r}]")
            self.assertEqual(len(groups), 1)
            self.assertIn("state != 'draft'", groups[0].get("invisible"))
            self.assertIn(guidance, " ".join(groups[0].itertext()))

        for title in ("5 Why Analysis", "Fishbone Analysis", "Is / Is Not Analysis", "Other Method"):
            groups = arch.xpath(f"//group[@string={title!r}]")
            self.assertEqual(len(groups), 1)
            self.assertIn("state == 'draft'", groups[0].get("invisible"))

        summary = arch.xpath("//group[@string='Common Root Cause Summary']")
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0].get("invisible"), "state == 'draft'")

    def test_capa_source_fields_are_conditional_and_root_cause_is_verified(self):
        view = self.env.ref("pm_qms_capa.view_pm_qms_capa_form")
        arch = etree.fromstring(view.arch_db.encode())
        ncr_field = arch.xpath("//field[@name='source_ncr_id']")[0]
        risk_field = arch.xpath("//field[@name='source_risk_id']")[0]

        self.assertEqual(ncr_field.get("invisible"), "source_type != 'ncr'")
        self.assertEqual(ncr_field.get("required"), "source_type == 'ncr'")
        self.assertEqual(risk_field.get("invisible"), "source_type != 'risk'")
        self.assertEqual(risk_field.get("required"), "source_type == 'risk'")
        self.assertEqual(ncr_field.get("readonly"), "state != 'draft'")
        self.assertEqual(risk_field.get("readonly"), "state != 'draft'")
        self.assertEqual(self.env["pm.qms.capa"]._fields["root_cause"].string, "Verified Root Cause")
        self.assertNotIn("o_form_label", view.arch_db)

    def test_methodology_guidance_is_full_width_before_analysis_structure(self):
        view = self.env.ref("pm_qms_capa.view_pm_qms_capa_form")
        arch = etree.fromstring(view.arch_db.encode())
        guidance_groups = arch.xpath(
            "//group[div[contains(@class, 'text-muted')]]"
        )

        self.assertEqual(len(guidance_groups), 8)
        for group in guidance_groups:
            guidance = group.xpath("./div[contains(@class, 'text-muted')]")
            self.assertEqual(len(guidance), 1)
            self.assertEqual(guidance[0].get("colspan"), "2")
            self.assertNotIn("o_form_label", guidance[0].get("class", ""))
            if group.get("string", "").endswith("Analysis"):
                children = list(group)
                self.assertLess(children.index(guidance[0]), children.index(group.xpath("./field")[0]))

    def test_source_provenance_rules_and_tenant_alignment(self):
        capa_model = self.env["pm.qms.capa"]
        capa = capa_model.create(self._capa_values(source_type="ncr", source_ncr_id=self.ncr.id))
        self.assertEqual(capa.source_ncr_id, self.ncr)

        with self.assertRaisesRegex(ValidationError, "Select the originating NCR"):
            capa_model.create(self._capa_values(source_type="ncr"))
        with self.assertRaisesRegex(ValidationError, "An originating Risk cannot"):
            capa_model.create(
                self._capa_values(source_type="ncr", source_ncr_id=self.ncr.id, source_risk_id=self.risk.id)
            )
        with self.assertRaisesRegex(ValidationError, "Originating NCR and Originating Risk are not applicable"):
            capa_model.create(self._capa_values(source_type="other", source_ncr_id=self.ncr.id))

        risk_capa = capa_model.create(self._capa_values(source_type="risk", source_risk_id=self.risk.id))
        self.assertEqual(risk_capa.source_risk_id, self.risk)
        with self.assertRaisesRegex(ValidationError, "Select the originating Risk"):
            capa_model.create(self._capa_values(source_type="risk"))
        with self.assertRaisesRegex(ValidationError, "An originating NCR cannot"):
            capa_model.create(
                self._capa_values(source_type="risk", source_ncr_id=self.ncr.id, source_risk_id=self.risk.id)
            )

        for source_type in ("audit_finding", "customer_issue", "supplier_issue", "management_decision", "other"):
            with self.assertRaisesRegex(ValidationError, "not applicable"):
                capa_model.create(self._capa_values(source_type=source_type, source_risk_id=self.risk.id))

        wrong_ncr = self.env["pm.qms.nonconformity"].create(
            {
                "name": "Wrong company NCR",
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
                "source_type": "internal",
                "description": "Wrong company source.",
                "severity": "major",
            }
        )
        with self.assertRaisesRegex(ValidationError, "Originating NCR must match"):
            capa_model.create(self._capa_values(source_type="ncr", source_ncr_id=wrong_ncr.id))

        same_company_other_org = self.env["pm.qms.organization"].create(
            {"name": "CAPA Other Organization", "code": "PM-CAPA-ORG3", "company_id": self.company.id}
        )
        same_company_other_process = self.env["pm.qms.process"].create(
            {
                "name": "CAPA Other Process",
                "code": "PM-CAPA-PROC3",
                "organization_id": same_company_other_org.id,
                "company_id": self.company.id,
            }
        )
        wrong_org_ncr = self.env["pm.qms.nonconformity"].create(
            {
                "name": "Wrong organization NCR",
                "organization_id": same_company_other_org.id,
                "process_id": same_company_other_process.id,
                "source_type": "internal",
                "description": "Wrong organization source.",
                "severity": "major",
            }
        )
        with self.assertRaisesRegex(ValidationError, "Originating NCR must match"):
            capa_model.create(self._capa_values(source_type="ncr", source_ncr_id=wrong_org_ncr.id))

        wrong_risk = self.env["pm.qms.risk"].create(
            {
                "name": "Wrong company risk",
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
                "description": "Wrong company source.",
            }
        )
        with self.assertRaisesRegex(ValidationError, "Originating risk must match"):
            capa_model.create(self._capa_values(source_type="risk", source_risk_id=wrong_risk.id))

        wrong_org_risk = self.env["pm.qms.risk"].create(
            {
                "name": "Wrong organization risk",
                "organization_id": same_company_other_org.id,
                "process_id": same_company_other_process.id,
                "description": "Wrong organization source.",
            }
        )
        with self.assertRaisesRegex(ValidationError, "Originating risk must match"):
            capa_model.create(self._capa_values(source_type="risk", source_risk_id=wrong_org_risk.id))

    def test_source_type_onchange_clears_inapplicable_relationships(self):
        capa = self.env["pm.qms.capa"].new(
            self._capa_values(source_type="ncr", source_ncr_id=self.ncr.id, source_risk_id=self.risk.id)
        )
        capa._onchange_source_type()
        self.assertFalse(capa.source_risk_id)
        capa.source_type = "risk"
        capa._onchange_source_type()
        self.assertFalse(capa.source_ncr_id)
        capa.source_type = "other"
        capa._onchange_source_type()
        self.assertFalse(capa.source_ncr_id)
        self.assertFalse(capa.source_risk_id)

    def test_source_provenance_is_editable_in_draft_and_locked_after_draft(self):
        manager = self._create_test_user("pmqms.capa.provenance", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values())
        capa.write({"source_reference": "Draft reference"})
        capa.write({"source_type": "ncr", "source_ncr_id": self.ncr.id})
        self.assertEqual(capa.source_ncr_id, self.ncr)

        for state in ("analysis", "action_planned", "implementation", "effectiveness_review", "effective", "closed"):
            capa.with_context(pm_qms_capa_workflow=True).write({"state": state})
            with self.assertRaisesRegex(UserError, "source provenance is locked"):
                capa.with_user(manager).write({"source_reference": f"Changed in {state}"})
            with self.assertRaisesRegex(UserError, "source provenance is locked"):
                capa.with_user(manager).write({"source_type": "risk"})
            with self.assertRaisesRegex(UserError, "source provenance is locked"):
                capa.with_user(manager).write({"source_ncr_id": False})

    def test_analysis_start_rejects_missing_source_provenance(self):
        capa = self.env["pm.qms.capa"].new(self._capa_values(source_type="ncr"))
        with self.assertRaisesRegex(ValidationError, "Select the originating NCR"):
            capa._validate_analysis_start()

    def test_start_analysis_validates_problem_statement_before_initialization(self):
        manager = self._create_test_user("pmqms.capa.start_validation", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(
            self._capa_values(name="Incomplete start", problem_statement="")
        )

        with self.assertRaisesRegex(UserError, "Complete the CAPA problem statement before starting root cause analysis"):
            capa.with_user(manager).action_start_analysis()
        self.assertEqual(capa.state, "draft")
        self.assertFalse(capa.why_ids)

    def test_fishbone_uses_exact_categories_and_read_only_guidance(self):
        expected_categories = {
            "people": "People",
            "machine_equipment": "Machine / Equipment",
            "method_process": "Method / Process",
            "material_inputs": "Material / Inputs",
            "measurement_data": "Measurement / Data",
            "environment": "Environment",
        }
        self.assertEqual(FISHBONE_CATEGORIES, expected_categories)
        self.assertEqual(len(FISHBONE_CATEGORIES), 6)
        self.assertNotIn("other", FISHBONE_CATEGORIES)
        self.assertNotIn("equipment", FISHBONE_CATEGORIES)
        self.assertNotIn("process", FISHBONE_CATEGORIES)
        self.assertNotIn("materials", FISHBONE_CATEGORIES)
        self.assertNotIn("measurement", FISHBONE_CATEGORIES)
        self.assertEqual(set(FISHBONE_GUIDANCE), set(expected_categories))
        self.assertTrue(all(FISHBONE_GUIDANCE.values()))
        self.assertTrue(self.env["pm.qms.capa.fishbone"]._fields["guidance"].readonly)

    def test_is_is_not_has_all_field_specific_prompts_and_optional_change(self):
        expected_prompts = {
            "what": {
                "is": "What object, process, or characteristic is affected?",
                "is_not": "What comparable object, process, or characteristic could be affected but is not?",
                "distinction": "What is different between the affected and unaffected cases?",
                "change": "What changed that could explain the distinction?",
            },
            "where": {
                "is": "Where is the problem observed?",
                "is_not": "Where could the problem occur but does not?",
                "distinction": "What differs between those locations?",
                "change": "What changed between those conditions or locations?",
            },
            "when": {
                "is": "When is or was the problem observed?",
                "is_not": "When could the problem occur but does not?",
                "distinction": "What differs between those times or operating conditions?",
                "change": "What changed around the time the problem began?",
            },
            "extent": {
                "is": "How many, how much, or how frequently is affected?",
                "is_not": "What comparable population, quantity, or frequency is unaffected?",
                "distinction": "What pattern separates the affected and unaffected cases?",
                "change": "Has the magnitude, frequency, or pattern changed?",
            },
        }
        self.assertEqual(IS_IS_NOT_PROMPTS, expected_prompts)
        fields = self.env["pm.qms.capa.is.is.not"]._fields
        for field_name in ("is_prompt", "is_not_prompt", "distinction_prompt", "change_prompt"):
            self.assertTrue(fields[field_name].readonly)
        self.assertFalse(fields["change_value"].required)

    def test_capa_creation_5why_multiple_actions_effectiveness_and_history(self):
        manager = self._create_test_user("pmqms.capa.manager", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values())
        action_1 = self.env["pm.qms.capa.action"].with_user(manager).create(
            {"capa_id": capa.id, "name": "Assign owner", "target_date": "2026-01-01"}
        )
        action_2 = self.env["pm.qms.capa.action"].with_user(manager).create(
            {"capa_id": capa.id, "name": "Verify distribution points", "target_date": "2026-01-01"}
        )

        self.assertRegex(capa.code, r"^PM-CAPA-\d{5}$")
        self.assertEqual(len(capa.why_ids), 0)
        self.assertEqual(capa.action_count, 2)
        self.assertTrue(action_1.is_overdue)

        capa.with_user(manager).action_start_analysis()
        self.assertEqual(len(capa.why_ids), 5)
        self.assertEqual(capa.why_ids.mapped("sequence"), [1, 2, 3, 4, 5])
        self.assertEqual(capa.why_ids[0].question, "Why did the problem occur?")
        capa.why_ids[0].with_user(manager).write({"answer": "Ownership was unclear."})
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        action_1.with_user(manager).action_start()
        action_1.with_user(manager).action_complete()
        action_2.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()

        capa.with_user(manager).write({"effectiveness_notes": "The follow-up check shows the action worked."})
        capa.with_user(manager).action_mark_effective()
        capa.with_user(manager).action_close()

        self.assertEqual(capa.state, "closed")
        self.assertEqual(capa.effectiveness_result, "effective")
        events = self.env["pm.qms.event"].search([("res_model", "=", "pm.qms.capa"), ("res_id", "=", capa.id)])
        self.assertGreaterEqual(len(events), 6)

    def test_ineffective_capa_can_reopen_without_destroying_result(self):
        manager = self._create_test_user("pmqms.capa.manager2", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values(name="Ineffective CAPA"))
        action = self.env["pm.qms.capa.action"].with_user(manager).create({"capa_id": capa.id, "name": "Initial action"})

        capa.with_user(manager).action_start_analysis()
        capa.why_ids.filtered(lambda row: row.sequence == 1).with_user(manager).write({"answer": "The assigned owner was unclear."})
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        action.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()
        capa.with_user(manager).write({"effectiveness_notes": "The issue repeated during verification."})
        capa.with_user(manager).action_mark_ineffective()

        self.assertEqual(capa.effectiveness_result, "ineffective")
        capa.with_user(manager).action_reopen_actions()
        self.assertEqual(capa.state, "action_planned")
        self.assertEqual(capa.effectiveness_result, "ineffective")

    def test_ncr_and_risk_create_structured_capa(self):
        capa_from_ncr_action = self.ncr.action_create_capa()
        capa_from_ncr = self.env["pm.qms.capa"].browse(capa_from_ncr_action["res_id"])
        self.assertEqual(capa_from_ncr.source_ncr_id, self.ncr)
        self.assertEqual(capa_from_ncr.source_type, "ncr")
        self.assertEqual(capa_from_ncr.related_control_instance_ids, self.control_instance)

        capa_from_risk_action = self.risk.action_create_capa()
        capa_from_risk = self.env["pm.qms.capa"].browse(capa_from_risk_action["res_id"])
        self.assertEqual(capa_from_risk.source_risk_id, self.risk)
        self.assertEqual(capa_from_risk.source_type, "risk")
        self.assertEqual(capa_from_risk.action_plan, self.risk.mitigation_plan)

    def test_capa_security_company_isolation_and_closure_controls(self):
        qms_user = self._create_test_user("pmqms.capa.user", self.qms_user_group)
        other_user = self._create_test_user("pmqms.capa.other", self.qms_user_group, self.other_company)
        capa = self.env["pm.qms.capa"].with_user(qms_user).create(self._capa_values(name="User CAPA"))

        with self.assertRaises(AccessError):
            capa.with_user(qms_user).action_close()
        with self.assertRaises(AccessError):
            capa.with_user(qms_user).write({"state": "closed"})
        self.assertFalse(self.env["pm.qms.capa"].with_user(other_user).search([("id", "=", capa.id)]))

        other_control = self.env["pm.qms.control"].create(
            {
                "name": "Other CAPA Control",
                "code": "PM-QMS-CAPA-OTHER",
                "objective": "Other company only.",
                "process_id": self.other_process.id,
            }
        )
        other_instance = self.env["pm.qms.control.instance"].create(
            {
                "name": "Other CAPA implementation",
                "code": "OTHER-CAPA-PM-QMS-001",
                "control_id": other_control.id,
                "organization_id": self.other_organization.id,
                "process_id": self.other_process.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["pm.qms.capa"].create(
                self._capa_values(name="Cross company CAPA", related_control_instance_ids=[(6, 0, [other_instance.id])])
            )

    def test_integration_chain_preserves_framework_control(self):
        manager = self._create_test_user("pmqms.capa.integration", self.qms_manager_group)
        original_control_state = self.control.state
        original_control_name = self.control.name

        self.evidence.with_user(manager).action_submit()
        self.evidence.with_user(manager).action_review()
        self.evidence.with_user(manager).action_accept()
        self.ncr.action_open()
        self.ncr.with_user(manager).action_start_investigation()
        self.ncr.with_user(manager).action_require_action()
        capa = self.env["pm.qms.capa"].browse(self.ncr.action_create_capa()["res_id"])
        action = self.env["pm.qms.capa.action"].with_user(manager).create({"capa_id": capa.id, "name": "Verify after next review"})
        capa.with_user(manager).write(
            {
                "root_cause_analysis": "The analysis identified an unassigned distribution check.",
                "root_cause": "The controlled distribution check was not assigned.",
            }
        )
        capa.with_user(manager).action_start_analysis()
        capa.why_ids.filtered(lambda row: row.sequence == 1).with_user(manager).write({"answer": "The check had no named owner."})
        capa.with_user(manager).action_plan_actions()
        capa.with_user(manager).action_start_implementation()
        action.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()
        capa.with_user(manager).write({"effectiveness_notes": "Next review showed current instructions in use."})
        capa.with_user(manager).action_mark_effective()
        capa.with_user(manager).action_close()

        self.assertEqual(capa.source_ncr_id, self.ncr)
        self.assertEqual(capa.related_control_instance_ids, self.control_instance)
        self.assertEqual(self.control.state, original_control_state)
        self.assertEqual(self.control.name, original_control_name)
        self.assertNotIn("risk_ids", self.control._fields)
        self.assertNotIn("nonconformity_ids", self.control._fields)
        self.assertNotIn("capa_ids", self.control._fields)

    def test_5why_fixed_slots_are_idempotent_and_protected(self):
        manager = self._create_test_user("pmqms.capa.fixed", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values(name="Fixed slots"))
        capa.with_user(manager).action_start_analysis()
        capa.with_user(manager).action_start_analysis()
        self.assertEqual(len(capa.why_ids), 5)
        self.assertEqual(set(capa.why_ids.mapped("sequence")), {1, 2, 3, 4, 5})
        with self.assertRaises(UserError):
            capa.why_ids[0].with_user(manager).unlink()
        with self.assertRaises(UserError):
            capa.why_ids[0].with_user(manager).write({"sequence": 2})
        with self.assertRaises(UserError):
            self.env["pm.qms.capa.why"].with_user(manager).create(
                {"capa_id": capa.id, "sequence": 1, "question": "Not a fixed prompt"}
            )

    def test_5why_plan_gate_requires_contiguous_answers_and_common_summary(self):
        manager = self._create_test_user("pmqms.capa.gate", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values(name="5 Why gate"))
        capa.with_user(manager).action_start_analysis()
        capa.why_ids.filtered(lambda row: row.sequence == 2).with_user(manager).write({"answer": "Skipped Why 1"})
        with self.assertRaises(UserError):
            capa.with_user(manager).action_plan_actions()
        capa.why_ids.filtered(lambda row: row.sequence == 1).with_user(manager).write({"answer": "Initial condition"})
        capa.with_user(manager).action_plan_actions()
        self.assertEqual(capa.state, "action_planned")

    def test_fishbone_requires_confirmed_evidence_and_supports_multiple_categories(self):
        manager = self._create_test_user("pmqms.capa.fishbone", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(
            self._capa_values(name="Fishbone", root_cause_method="fishbone")
        )
        capa.with_user(manager).action_start_analysis()
        fishbone = self.env["pm.qms.capa.fishbone"].with_user(manager)
        first_cause = fishbone.create(
            {"capa_id": capa.id, "category": "method_process", "potential_cause": "Unclear handoff"}
        )
        second_cause = fishbone.create(
            {"capa_id": capa.id, "category": "method_process", "potential_cause": "Missing review"}
        )
        self.assertEqual(first_cause.guidance, FISHBONE_GUIDANCE["method_process"])
        self.assertEqual(second_cause.guidance, first_cause.guidance)
        with self.assertRaises(UserError):
            capa.with_user(manager).action_plan_actions()
        confirmed = fishbone.create(
            {
                "capa_id": capa.id,
                "category": "measurement_data",
                "potential_cause": "Signal not checked",
                "evidence_basis": "Fictional inspection sample",
                "rationale_finding": "The check was absent from the local workflow.",
                "investigation_status": "confirmed",
            }
        )
        capa.with_user(manager).action_plan_actions()
        self.assertEqual(capa.state, "action_planned")
        self.assertEqual(confirmed.capa_id, capa)

    def test_is_is_not_initializes_four_fixed_dimensions_and_gates_plan(self):
        manager = self._create_test_user("pmqms.capa.isnot", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(
            self._capa_values(name="Is Is Not", root_cause_method="is_is_not")
        )
        capa.with_user(manager).action_start_analysis()
        self.assertEqual(set(capa.is_is_not_ids.mapped("dimension")), {"what", "where", "when", "extent"})
        with self.assertRaises(UserError):
            capa.with_user(manager).action_plan_actions()
        capa.is_is_not_ids.with_user(manager).write(
            {
                "is_value": "Observed condition",
                "is_not_value": "Excluded condition",
                "distinction": "Verified boundary",
            }
        )
        capa.with_user(manager).action_plan_actions()
        self.assertEqual(capa.state, "action_planned")
        with self.assertRaises(UserError):
            capa.is_is_not_ids[0].with_user(manager).unlink()

    def test_other_method_requires_named_tool_and_method_lock(self):
        manager = self._create_test_user("pmqms.capa.other", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(
            self._capa_values(name="Other method", root_cause_method="other", other_method_name="Barrier review")
        )
        capa.with_user(manager).action_start_analysis()
        with self.assertRaises(UserError):
            capa.with_user(manager).write({"root_cause_method": "5why"})
        capa.with_user(manager).action_plan_actions()
        self.assertEqual(capa.state, "action_planned")

    def test_rca_is_locked_in_implementation_and_refinable_after_ineffective_reopen(self):
        manager = self._create_test_user("pmqms.capa.lock", self.qms_manager_group)
        capa = self.env["pm.qms.capa"].with_user(manager).create(self._capa_values(name="RCA lock"))
        capa.with_user(manager).action_start_analysis()
        capa.why_ids.filtered(lambda row: row.sequence == 1).with_user(manager).write({"answer": "Condition"})
        capa.with_user(manager).action_plan_actions()
        action = self.env["pm.qms.capa.action"].with_user(manager).create({"capa_id": capa.id, "name": "Contain"})
        capa.with_user(manager).action_start_implementation()
        with self.assertRaises(UserError):
            capa.with_user(manager).write({"root_cause": "Changed after implementation"})
        action.with_user(manager).action_complete()
        capa.with_user(manager).action_complete_implementation()
        capa.with_user(manager).write({"effectiveness_notes": "The cause persisted."})
        capa.with_user(manager).action_mark_ineffective()
        capa.with_user(manager).action_reopen_actions()
        capa.with_user(manager).write({"root_cause_analysis": "Refined after ineffective review."})
        with self.assertRaises(UserError):
            capa.with_user(manager).write({"root_cause_method": "fishbone"})
