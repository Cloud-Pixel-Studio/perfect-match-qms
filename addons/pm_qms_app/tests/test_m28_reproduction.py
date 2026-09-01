import base64
from datetime import datetime, timedelta, timezone

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_license.services.license_service import effective_temporal_state


@tagged("-at_install", "post_install", "m28_reproduction")
class TestM28Reproduction(TransactionCase):
    """Disposable DEV reproductions for the M28 authorization findings."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.organization_a = cls.env["pm.qms.organization"].sudo().create(
            {"name": "M28 Reproduction Organization A", "code": "M28-REPRO-A", "company_id": cls.company.id}
        )
        cls.organization_b = cls.env["pm.qms.organization"].sudo().create(
            {"name": "M28 Reproduction Organization B", "code": "M28-REPRO-B", "company_id": cls.company.id}
        )
        cls.process_a = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M28 Reproduction Process A",
                "code": "M28-REPRO-PROCESS-A",
                "organization_id": cls.organization_a.id,
                "company_id": cls.company.id,
            }
        )
        cls.process_b = cls.env["pm.qms.process"].sudo().create(
            {
                "name": "M28 Reproduction Process B",
                "code": "M28-REPRO-PROCESS-B",
                "organization_id": cls.organization_a.id,
                "company_id": cls.company.id,
            }
        )
        cls.capa_a = cls.env["pm.qms.capa"].sudo().create(
            {
                "name": "M28 Reproduction CAPA A",
                "organization_id": cls.organization_a.id,
                "process_id": cls.process_a.id,
                "problem_statement": "M28 fictional process A issue.",
                "state": "analysis",
            }
        )
        cls.capa_b = cls.env["pm.qms.capa"].sudo().create(
            {
                "name": "M28 Reproduction CAPA B",
                "organization_id": cls.organization_a.id,
                "process_id": cls.process_b.id,
                "problem_statement": "M28 fictional process B issue.",
                "state": "analysis",
            }
        )
        cls.review_a = cls.env["pm.qms.management.review"].sudo().create(
            {
                "name": "M28 Reproduction Review A",
                "organization_id": cls.organization_a.id,
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            }
        )
        cls.review_b = cls.env["pm.qms.management.review"].sudo().create(
            {
                "name": "M28 Reproduction Review B",
                "organization_id": cls.organization_b.id,
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            }
        )
        cls.input_a = cls.env["pm.qms.management.review.input"].sudo().create(
            {
                "review_id": cls.review_a.id,
                "category": "other",
                "title": "M28 Reproduction Input A",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            }
        )
        cls.input_b = cls.env["pm.qms.management.review.input"].sudo().create(
            {
                "review_id": cls.review_b.id,
                "category": "other",
                "title": "M28 Reproduction Input B",
                "period_start": "2026-01-01",
                "period_end": "2026-01-31",
            }
        )
        cls.viewer = cls.env["res.users"].sudo().with_context(no_reset_password=True).create(
            {
                "name": "M28 Reproduction Scoped User",
                "login": "m28.reproduction.scoped",
                "company_id": cls.company.id,
                "company_ids": [Command.set([cls.company.id])],
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("pm_qms_core.group_qms_quality_manager").id,
                        ]
                    )
                ],
                "qms_organization_ids": [Command.set([cls.organization_a.id])],
                "qms_all_sites": True,
                "qms_process_ids": [Command.set([cls.process_a.id])],
            }
        )

    def test_same_company_child_record_isolated_for_all_record_access(self):
        visible = self.env["pm.qms.management.review.input"].with_user(self.viewer).search([])
        self.assertIn(self.input_a, visible)
        self.assertNotIn(self.input_b, visible)
        self.assertNotIn(
            self.input_b.id,
            [record_id for record_id, _label in self.env["pm.qms.management.review.input"].with_user(self.viewer).name_search("M28 Reproduction Input B")],
        )
        grouped = self.env["pm.qms.management.review.input"].with_user(self.viewer).read_group(
            [], ["__count"], ["review_id"]
        )
        self.assertTrue(grouped)
        self.assertTrue(all(group.get("review_id", [False])[0] != self.review_b.id for group in grouped))
        with self.assertRaises(AccessError):
            self.input_b.with_user(self.viewer).read(["title"])
        with self.assertRaises(AccessError):
            self.input_b.with_user(self.viewer).write({"title": "M28 unauthorized edit"})
        with self.assertRaises(AccessError):
            self.input_b.with_user(self.viewer).unlink()
        created = self.env["pm.qms.management.review.input"].with_user(self.viewer).create(
            {
                "review_id": self.review_a.id,
                "category": "other",
                "title": "M28 Reproduction In-Scope Create",
                "period_start": "2026-02-01",
                "period_end": "2026-02-28",
            }
        )
        self.assertEqual(created.organization_id, self.organization_a)
        with self.assertRaises(AccessError):
            self.env["pm.qms.management.review.input"].with_user(self.viewer).create(
                {
                    "review_id": self.review_b.id,
                    "category": "other",
                    "title": "M28 Reproduction Out-of-Scope Create",
                    "period_start": "2026-02-01",
                    "period_end": "2026-02-28",
                }
            )

    def _expired_license(self):
        now = datetime.now().replace(microsecond=0)
        return self.env["pm.qms.license"].sudo().create(
            {
                "license_id": "M28-REPRO-EXPIRED",
                "license_revision": 1,
                "customer_name": "M28 Reproduction Customer",
                "edition": "professional",
                "environment_id": "m28-reproduction-environment",
                "company_limit": 1,
                "site_limit": 1,
                "named_user_limit": 1,
                "issued_at": now - timedelta(days=40),
                "not_before": now - timedelta(days=30),
                "expires_at": now - timedelta(days=1),
                "perpetual": False,
                "key_id": "m28-reproduction-key",
                "signature": "m28-reproduction-signature",
                "payload_json": "{}",
                "state": "valid",
                "is_current": True,
                "fingerprint": "m28-reproduction-fingerprint",
                "public_key_fingerprint": "m28-reproduction-public-key",
            }
        )

    def test_expired_stored_license_cannot_authorize_capacity(self):
        license_record = self._expired_license()
        with self.assertRaises(UserError):
            self.env["pm.qms.entitlement.service"]._license_or_raise()
        self.assertEqual(license_record.state, "valid")
        self.assertEqual(license_record.effective_state, "expired")
        self.assertEqual(self.env["pm.qms.license"].current_status()["status"], "expired")
        self.assertLess(fields.Datetime.to_datetime(license_record.expires_at), fields.Datetime.now())

    def test_capa_children_inherit_parent_process_scope(self):
        child_specs = (
            ("pm.qms.capa.action", {"capa_id": self.capa_a.id, "name": "M28 scoped action A"}, {"name": "M28 action edit"}),
            ("pm.qms.capa.why", {"capa_id": self.capa_a.id, "sequence": 1, "question": "M28 why A"}, {"answer": "M28 answer"}),
            (
                "pm.qms.capa.fishbone",
                {"capa_id": self.capa_a.id, "category": "people", "potential_cause": "M28 cause A"},
                {"potential_cause": "M28 cause edit"},
            ),
            (
                "pm.qms.capa.is.is.not",
                {"capa_id": self.capa_a.id, "dimension": "what", "sequence": 1},
                {"is_value": "M28 value edit"},
            ),
        )
        for model_name, in_scope_values, write_values in child_specs:
            context = {"pm_qms_capa_initialize": True} if model_name.endswith(("why", "is.is.not")) else {}
            Child = self.env[model_name].with_context(**context)
            if model_name.endswith(".is.is.not"):
                dimensions = (("what", 1), ("where", 2), ("when", 3), ("extent", 4))
                in_scope = Child.sudo().create(
                    [dict(in_scope_values, dimension=dimension, sequence=sequence) for dimension, sequence in dimensions]
                )
                out_scope = Child.sudo().create(
                    [
                        dict(in_scope_values, capa_id=self.capa_b.id, dimension=dimension, sequence=sequence)
                        for dimension, sequence in dimensions
                    ]
                )
                in_scope = in_scope.filtered(lambda row: row.dimension == "what")
                out_scope = out_scope.filtered(lambda row: row.dimension == "what")
            else:
                in_scope = Child.sudo().create(in_scope_values)
                out_scope_values = dict(in_scope_values, capa_id=self.capa_b.id)
                out_scope = Child.sudo().create(out_scope_values)
            scoped = self.env[model_name].with_user(self.viewer)
            self.assertIn(in_scope, scoped.search([]))
            self.assertNotIn(out_scope, scoped.search([]))
            if "name" in in_scope_values:
                self.assertNotIn(out_scope.id, [record_id for record_id, _label in scoped.name_search("M28")])
            with self.assertRaises(AccessError):
                out_scope.with_user(self.viewer).read()
            with self.assertRaises(AccessError):
                out_scope.with_user(self.viewer).write(write_values)
            with self.assertRaises(Exception) as unlink_error:
                out_scope.with_user(self.viewer).unlink()
            self.assertIsInstance(unlink_error.exception, (AccessError, UserError))
            if model_name.endswith((".why", ".is.is.not")):
                with self.assertRaises(AccessError):
                    out_scope.with_user(self.viewer).check_access_rule("create")
            else:
                with self.assertRaises(AccessError):
                    scoped.with_context(**context).create(dict(in_scope_values, capa_id=self.capa_b.id))

        action_a = self.capa_a.action_ids[:1]
        action_b = self.capa_b.action_ids[:1]
        message_a = action_a.sudo().message_post(body="M28 CAPA process A message", subtype_xmlid="mail.mt_note")
        message_b = action_b.sudo().message_post(body="M28 CAPA process B message", subtype_xmlid="mail.mt_note")
        activity_a = action_a.sudo().activity_schedule(
            "mail.mail_activity_data_todo", summary="M28 CAPA activity A", user_id=self.viewer.id
        )
        activity_b = action_b.sudo().activity_schedule(
            "mail.mail_activity_data_todo", summary="M28 CAPA activity B", user_id=self.viewer.id
        )
        attachment_a = self.env["ir.attachment"].sudo().create(
            {"name": "m28-capa-a.txt", "type": "binary", "datas": base64.b64encode(b"A").decode(), "res_model": action_a._name, "res_id": action_a.id}
        )
        attachment_b = self.env["ir.attachment"].sudo().create(
            {"name": "m28-capa-b.txt", "type": "binary", "datas": base64.b64encode(b"B").decode(), "res_model": action_b._name, "res_id": action_b.id}
        )
        self.assertIn(message_a, self.env["mail.message"].with_user(self.viewer).search([("model", "=", action_a._name)]))
        self.assertNotIn(message_b, self.env["mail.message"].with_user(self.viewer).search([("model", "=", action_b._name)]))
        self.assertIn(activity_a, self.env["mail.activity"].with_user(self.viewer).search([("res_model", "=", action_a._name)]))
        self.assertNotIn(activity_b, self.env["mail.activity"].with_user(self.viewer).search([("res_model", "=", action_b._name)]))
        self.assertTrue(attachment_a.with_user(self.viewer).read(["name"]))
        with self.assertRaises(AccessError):
            attachment_b.with_user(self.viewer).read(["name"])

    def test_expired_license_blocks_all_new_capacity_hooks(self):
        self._expired_license()
        service = self.env["pm.qms.entitlement.service"]
        seed_context = {"pmqms_license_seed": True}
        organization = self.env["pm.qms.organization"].with_context(**seed_context).sudo().create(
            {
                "name": "M28 Reproduction Expired Organization",
                "code": "M28-REPRO-EXPIRED-ORG",
                "company_id": self.company.id,
            }
        )
        site = self.env["pm.qms.site"].with_context(**seed_context).sudo().create(
            {
                "name": "M28 Reproduction Expired Site",
                "code": "M28-REPRO-EXPIRED-SITE",
                "company_id": self.company.id,
                "organization_id": organization.id,
                "site_type": "office",
            }
        )
        user = self.env["res.users"].sudo().with_context(no_reset_password=True, **seed_context).create(
            {
                "name": "M28 Reproduction Expired Named User",
                "login": "m28.reproduction.expired.user",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([self.env.ref("base.group_user").id])],
            }
        )
        with self.assertRaises(UserError):
            service.enforce_organization(organization)
        with self.assertRaises(UserError):
            service.enforce_sites(site)
        with self.assertRaises(UserError):
            service.enforce_named_users(user)

    def test_license_temporal_boundaries_recompute_without_reimport(self):
        now = datetime.now().replace(microsecond=0)
        License = self.env["pm.qms.license"].sudo()
        cases = [
            ("M28-REPRO-NOT-YET", now + timedelta(days=1), now + timedelta(days=40), "not_yet_valid"),
            ("M28-REPRO-EXPIRING", now - timedelta(days=1), now + timedelta(days=2), "expiring"),
            ("M28-REPRO-EXPIRED", now - timedelta(days=40), now - timedelta(seconds=1), "expired"),
        ]
        for license_id, not_before, expires_at, expected in cases:
            record = License.create(
                {
                    "license_id": license_id,
                    "license_revision": 1,
                    "customer_name": "M28 Reproduction Customer",
                    "edition": "professional",
                    "environment_id": "m28-reproduction-environment",
                    "company_limit": 1,
                    "site_limit": 1,
                    "named_user_limit": 1,
                    "issued_at": now,
                    "not_before": not_before,
                    "expires_at": expires_at,
                    "perpetual": False,
                    "key_id": "m28-reproduction-key",
                    "signature": "m28-reproduction-signature",
                    "payload_json": "{}",
                    "state": "valid",
                    "is_current": False,
                    "fingerprint": license_id,
                    "public_key_fingerprint": license_id,
                }
            )
            self.assertEqual(record.effective_state, expected)

        perpetual = License.create(
            {
                "license_id": "M28-REPRO-PERPETUAL",
                "license_revision": 1,
                "customer_name": "M28 Reproduction Customer",
                "edition": "professional",
                "environment_id": "m28-reproduction-environment",
                "company_limit": 1,
                "site_limit": 1,
                "named_user_limit": 1,
                "issued_at": now - timedelta(days=400),
                "not_before": now - timedelta(days=400),
                "perpetual": True,
                "key_id": "m28-reproduction-key",
                "signature": "m28-reproduction-signature",
                "payload_json": "{}",
                "state": "valid",
                "is_current": False,
                "fingerprint": "M28-REPRO-PERPETUAL",
                "public_key_fingerprint": "M28-REPRO-PERPETUAL",
            }
        )
        self.assertEqual(perpetual.effective_state, "valid")

    def test_license_temporal_boundaries_include_exact_edges(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(
            effective_temporal_state(
                "valid", now, now + timedelta(days=31), False, now=now
            ),
            "valid",
        )
        self.assertEqual(
            effective_temporal_state(
                "valid", now - timedelta(days=1), now + timedelta(days=30), False, now=now
            ),
            "expiring",
        )
        self.assertEqual(
            effective_temporal_state(
                "valid", now - timedelta(days=1), now, False, now=now
            ),
            "expired",
        )
        self.assertEqual(
            effective_temporal_state(
                "valid", now + timedelta(seconds=1), now + timedelta(days=31), False, now=now
            ),
            "not_yet_valid",
        )
        self.assertEqual(
            effective_temporal_state(
                "invalid_signature", now - timedelta(days=1), now - timedelta(days=1), False, now=now
            ),
            "invalid_signature",
        )

    def test_native_mail_and_attachment_routes_follow_child_scope(self):
        message_a = self.input_a.sudo().message_post(
            body="M28 fictional child message A.", subtype_xmlid="mail.mt_note"
        )
        message_b = self.input_b.sudo().message_post(
            body="M28 fictional child message B.", subtype_xmlid="mail.mt_note"
        )
        activity_a = self.input_a.sudo().activity_schedule(
            "mail.mail_activity_data_todo",
            summary="M28 fictional child activity A",
            date_deadline=fields.Date.today(),
            user_id=self.viewer.id,
        )
        activity_b = self.input_b.sudo().activity_schedule(
            "mail.mail_activity_data_todo",
            summary="M28 fictional child activity B",
            date_deadline=fields.Date.today(),
            user_id=self.viewer.id,
        )
        attachment_a = self.env["ir.attachment"].sudo().create(
            {
                "name": "m28-child-a.txt",
                "type": "binary",
                "datas": base64.b64encode(b"M28 fictional child A").decode(),
                "res_model": self.input_a._name,
                "res_id": self.input_a.id,
                "mimetype": "text/plain",
            }
        )
        attachment_b = self.env["ir.attachment"].sudo().create(
            {
                "name": "m28-child-b.txt",
                "type": "binary",
                "datas": base64.b64encode(b"M28 fictional child B").decode(),
                "res_model": self.input_b._name,
                "res_id": self.input_b.id,
                "mimetype": "text/plain",
            }
        )
        child_message = self.env["mail.message"].with_user(self.viewer).search(
            [("model", "=", self.input_a._name), ("res_id", "in", [self.input_a.id, self.input_b.id])]
        )
        self.assertIn(message_a, child_message)
        self.assertNotIn(message_b, child_message)
        with self.assertRaises(AccessError):
            message_b.with_user(self.viewer).read(["body"])
        allowed_child_documents = self.env["mail.message"].with_user(self.viewer)._filter_records_for_message_operation(
            self.input_a._name, {self.input_a.id: [message_a.id], self.input_b.id: [message_b.id]}, "read"
        )
        self.assertIn(self.input_a, allowed_child_documents)
        self.assertNotIn(self.input_b, allowed_child_documents)
        child_activity = self.env["mail.activity"].with_user(self.viewer).search(
            [("res_model", "=", self.input_a._name), ("res_id", "in", [self.input_a.id, self.input_b.id])]
        )
        self.assertIn(activity_a, child_activity)
        self.assertNotIn(activity_b, child_activity)
        self.assertEqual(
            self.env["mail.activity"].with_user(self.viewer).search_count(
                [("res_model", "=", self.input_a._name), ("res_id", "in", [self.input_a.id, self.input_b.id])]
            ),
            1,
        )
        self.assertTrue(activity_a.with_user(self.viewer).read(["summary"]))
        with self.assertRaises(AccessError):
            activity_b.with_user(self.viewer).read(["summary"])
        with self.assertRaises(AccessError):
            activity_b.with_user(self.viewer).write({"summary": "M28 unauthorized edit"})
        with self.assertRaises(AccessError):
            activity_b.with_user(self.viewer).unlink()
        self.assertTrue(attachment_a.with_user(self.viewer).read(["name", "datas"]))
        with self.assertRaises(AccessError):
            attachment_b.with_user(self.viewer).read(["name", "datas"])

    def test_m28_child_scope_rules_cover_required_record_families(self):
        expected_rule_ids = (
            "rule_m28_event_scope",
            "rule_m28_capa_action_scope",
            "rule_m28_capa_why_scope",
            "rule_m28_capa_fishbone_scope",
            "rule_m28_capa_is_is_not_scope",
            "rule_m28_management_review_input_scope",
            "rule_m28_management_review_decision_scope",
            "rule_m28_management_review_action_scope",
            "rule_m28_audit_scope_scope",
            "rule_m28_audit_criterion_scope",
            "rule_m28_audit_plan_line_scope",
            "rule_m28_audit_evidence_scope",
            "rule_m28_audit_finding_scope",
            "rule_m28_calibration_measurement_scope",
            "rule_m28_calibration_impact_scope",
            "rule_m28_calibration_affected_reference_scope",
            "rule_m28_person_role_assignment_scope",
            "rule_m28_role_competency_requirement_scope",
            "rule_m28_competency_assessment_scope",
            "rule_m28_competency_matrix_scope",
            "rule_m28_training_event_scope",
            "rule_m28_training_record_scope",
            "rule_m28_qualification_record_scope",
            "rule_m28_role_document_requirement_scope",
            "rule_m28_document_acknowledgment_scope",
        )
        for rule_id in expected_rule_ids:
            rule = self.env.ref(f"pm_qms_app.{rule_id}")
            self.assertTrue(getattr(rule, "global"), rule_id)
            self.assertIn("qms_effective_organization_ids", rule.domain_force, rule_id)

    def test_management_review_audit_event_and_native_mail_runtime_isolation(self):
        """Exercise organization and process boundaries on the remaining M28 surfaces."""
        def assert_isolated(model_name, in_scope, out_scope, create_values, write_values, groupby="organization_id"):
            scoped = self.env[model_name].with_user(self.viewer)
            self.assertIn(in_scope, scoped.search([]), model_name)
            self.assertNotIn(out_scope, scoped.search([]), model_name)
            self.assertEqual(scoped.search_count([("id", "in", [in_scope.id, out_scope.id])]), 1, model_name)
            if groupby in scoped._fields:
                groups = scoped.read_group([("id", "in", [in_scope.id, out_scope.id])], ["__count"], [groupby])
                self.assertTrue(groups, model_name)
                self.assertTrue(all(group.get(groupby, [False])[0] != getattr(out_scope, groupby).id for group in groups), model_name)
            with self.assertRaises(AccessError, msg=f"read:{model_name}"):
                out_scope.with_user(self.viewer).read()
            with self.assertRaises(AccessError, msg=f"create:{model_name}"):
                scoped.create(create_values)
            try:
                out_scope.with_user(self.viewer).write(write_values)
            except (AccessError, UserError):
                pass
            else:
                self.fail(f"write:{model_name} was not rejected")
            try:
                out_scope.with_user(self.viewer).unlink()
            except (AccessError, UserError):
                pass
            else:
                self.fail(f"unlink:{model_name} was not rejected")

        Decision = self.env["pm.qms.management.review.decision"].sudo()
        decision_a = Decision.create(
            {"review_id": self.review_a.id, "name": "M28 Decision A", "description": "Fictional decision A"}
        )
        decision_b = Decision.create(
            {"review_id": self.review_b.id, "name": "M28 Decision B", "description": "Fictional decision B"}
        )
        assert_isolated(
            "pm.qms.management.review.decision",
            decision_a,
            decision_b,
            {"review_id": self.review_b.id, "name": "M28 Decision denied", "description": "Denied"},
            {"description": "M28 unauthorized decision edit"},
        )

        Action = self.env["pm.qms.management.review.action"].sudo()
        action_a = Action.create({"review_id": self.review_a.id, "name": "M28 Action A"})
        action_b = Action.create({"review_id": self.review_b.id, "name": "M28 Action B"})
        assert_isolated(
            "pm.qms.management.review.action",
            action_a,
            action_b,
            {"review_id": self.review_b.id, "name": "M28 Action denied"},
            {"description": "M28 unauthorized action edit"},
        )

        Audit = self.env["pm.qms.audit"].sudo()
        audit_a = Audit.create(
            {
                "name": "M28 Audit A",
                "organization_id": self.organization_a.id,
                "planned_start": "2026-03-01",
                "planned_end": "2026-03-02",
                "objective": "Fictional audit objective A",
            }
        )
        audit_process_b = Audit.create(
            {
                "name": "M28 Audit Process B",
                "organization_id": self.organization_a.id,
                "planned_start": "2026-03-03",
                "planned_end": "2026-03-04",
                "objective": "Fictional audit objective process B",
            }
        )
        audit_b = Audit.create(
            {
                "name": "M28 Audit B",
                "organization_id": self.organization_b.id,
                "planned_start": "2026-03-05",
                "planned_end": "2026-03-06",
                "objective": "Fictional audit objective B",
            }
        )
        Scope = self.env["pm.qms.audit.scope"].sudo()
        scope_a = Scope.create({"audit_id": audit_a.id, "organization_id": self.organization_a.id, "process_id": self.process_a.id, "description": "Scope A"})
        scope_process_b = Scope.create({"audit_id": audit_process_b.id, "organization_id": self.organization_a.id, "process_id": self.process_b.id, "description": "Scope process B"})
        scope_b = Scope.create({"audit_id": audit_b.id, "organization_id": self.organization_b.id, "description": "Scope B"})
        assert_isolated(
            "pm.qms.audit.scope", scope_a, scope_process_b,
            {"audit_id": audit_process_b.id, "organization_id": self.organization_a.id, "process_id": self.process_b.id, "description": "Denied process scope"},
            {"description": "M28 unauthorized scope edit"},
            groupby="process_id",
        )
        assert_isolated(
            "pm.qms.audit.scope", scope_a, scope_b,
            {"audit_id": audit_b.id, "organization_id": self.organization_b.id, "description": "Denied organization scope"},
            {"description": "M28 unauthorized organization scope edit"},
        )

        Criterion = self.env["pm.qms.audit.criterion"].sudo()
        criterion_a = Criterion.create({"audit_id": audit_a.id, "name": "M28 Criterion A"})
        criterion_b = Criterion.create({"audit_id": audit_b.id, "name": "M28 Criterion B"})
        assert_isolated(
            "pm.qms.audit.criterion", criterion_a, criterion_b,
            {"audit_id": audit_b.id, "name": "M28 Denied Criterion"},
            {"name": "M28 unauthorized criterion edit"},
        )

        PlanLine = self.env["pm.qms.audit.plan.line"].sudo()
        plan_a = PlanLine.create({"audit_id": audit_a.id, "process_id": self.process_a.id, "activity": "Plan A"})
        plan_process_b = PlanLine.create({"audit_id": audit_process_b.id, "process_id": self.process_b.id, "activity": "Plan process B"})
        plan_b = PlanLine.create({"audit_id": audit_b.id, "activity": "Plan B"})
        assert_isolated(
            "pm.qms.audit.plan.line", plan_a, plan_process_b,
            {"audit_id": audit_process_b.id, "process_id": self.process_b.id, "activity": "Denied process plan"},
            {"activity": "M28 unauthorized plan edit"},
            groupby="process_id",
        )
        assert_isolated(
            "pm.qms.audit.plan.line", plan_a, plan_b,
            {"audit_id": audit_b.id, "activity": "Denied organization plan"},
            {"activity": "M28 unauthorized organization plan edit"},
        )

        Evidence = self.env["pm.qms.audit.evidence"].sudo()
        evidence_a = Evidence.create({"audit_id": audit_a.id, "name": "M28 Evidence A", "description": "Evidence A"})
        evidence_b = Evidence.create({"audit_id": audit_b.id, "name": "M28 Evidence B", "description": "Evidence B"})
        assert_isolated(
            "pm.qms.audit.evidence", evidence_a, evidence_b,
            {"audit_id": audit_b.id, "name": "M28 Denied Evidence", "description": "Denied"},
            {"description": "M28 unauthorized evidence edit"},
        )
        attachment_a = self.env["ir.attachment"].sudo().create(
            {"name": "m28-audit-a.txt", "type": "binary", "datas": base64.b64encode(b"audit A").decode(), "res_model": evidence_a._name, "res_id": evidence_a.id}
        )
        attachment_b = self.env["ir.attachment"].sudo().create(
            {"name": "m28-audit-b.txt", "type": "binary", "datas": base64.b64encode(b"audit B").decode(), "res_model": evidence_b._name, "res_id": evidence_b.id}
        )
        self.assertTrue(attachment_a.with_user(self.viewer).read(["name", "datas"]))
        with self.assertRaises(AccessError):
            attachment_b.with_user(self.viewer).read(["name"])
        with self.assertRaises(AccessError):
            attachment_b.with_user(self.viewer).read(["datas"])

        Finding = self.env["pm.qms.audit.finding"].sudo()
        finding_a = Finding.create({"audit_id": audit_a.id, "name": "M28 Finding A", "title": "Finding A", "objective_evidence": "Evidence A", "process_id": self.process_a.id})
        finding_process_b = Finding.create({"audit_id": audit_process_b.id, "name": "M28 Finding process B", "title": "Finding process B", "objective_evidence": "Evidence process B", "process_id": self.process_b.id})
        finding_b = Finding.create({"audit_id": audit_b.id, "name": "M28 Finding B", "title": "Finding B", "objective_evidence": "Evidence B"})
        assert_isolated(
            "pm.qms.audit.finding", finding_a, finding_process_b,
            {"audit_id": audit_process_b.id, "name": "M28 Denied Finding", "title": "Denied", "objective_evidence": "Denied", "process_id": self.process_b.id},
            {"description": "M28 unauthorized finding edit"},
            groupby="process_id",
        )
        assert_isolated(
            "pm.qms.audit.finding", finding_a, finding_b,
            {"audit_id": audit_b.id, "name": "M28 Denied Organization Finding", "title": "Denied", "objective_evidence": "Denied"},
            {"description": "M28 unauthorized organization finding edit"},
        )

        Event = self.env["pm.qms.event"].sudo()
        event_a = Event.create({"name": "M28 Event A", "user_id": self.viewer.id, "company_id": self.company.id, "organization_id": self.organization_a.id, "res_model": evidence_a._name, "res_id": evidence_a.id, "record_name": "Evidence A"})
        event_b = Event.create({"name": "M28 Event B", "user_id": self.viewer.id, "company_id": self.company.id, "organization_id": self.organization_b.id, "res_model": evidence_b._name, "res_id": evidence_b.id, "record_name": "Evidence B"})
        assert_isolated(
            "pm.qms.event", event_a, event_b,
            {"name": "M28 Denied Event", "user_id": self.viewer.id, "company_id": self.company.id, "organization_id": self.organization_b.id, "res_model": evidence_b._name, "res_id": evidence_b.id},
            {"name": "M28 event mutation"},
        )

        partner = self.env["res.partner"].sudo().create({"name": "M28 Native Mail Partner"})
        native_activity = partner.activity_schedule(
            "mail.mail_activity_data_todo", summary="M28 native non-QMS activity", user_id=self.viewer.id
        )
        native_activities = self.env["mail.activity"].with_user(self.viewer).search([("id", "=", native_activity.id)])
        self.assertIn(native_activity, native_activities)
        self.assertEqual(
            self.env["mail.activity"].with_user(self.viewer).search_count([("id", "=", native_activity.id)]), 1
        )
        self.assertTrue(native_activity.with_user(self.viewer).read(["summary"]))
        native_activity.with_user(self.viewer).write({"summary": "M28 native non-QMS activity updated"})
        native_activity.with_user(self.viewer).unlink()

    def test_site_scoped_children_do_not_cross_site_within_organization(self):
        """Site-bound child records must inherit the user's selected site scope."""
        site_a = self.env["pm.qms.site"].sudo().create(
            {"name": "M28 Site A", "code": "M28-SITE-A", "organization_id": self.organization_a.id, "site_type": "office"}
        )
        site_b = self.env["pm.qms.site"].sudo().create(
            {"name": "M28 Site B", "code": "M28-SITE-B", "organization_id": self.organization_a.id, "site_type": "warehouse"}
        )
        self.process_a.sudo().write({"site_ids": [Command.set([site_a.id])]})
        self.process_b.sudo().write({"site_ids": [Command.set([site_b.id])]})
        site_user = self.env["res.users"].sudo().with_context(no_reset_password=True).create(
            {
                "name": "M28 Site Scoped User",
                "login": "m28.site.scoped",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([self.env.ref("base.group_user").id, self.env.ref("pm_qms_core.group_qms_quality_manager").id])],
                "qms_organization_ids": [Command.set([self.organization_a.id])],
                "qms_site_ids": [Command.set([site_a.id])],
                "qms_process_ids": [Command.set([self.process_a.id])],
            }
        )
        manager = self.env["res.users"].sudo().with_context(no_reset_password=True).create(
            {
                "name": "M28 Site Scoped Manager",
                "login": "m28.site.manager",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "group_ids": [Command.set([self.env.ref("base.group_user").id, self.env.ref("pm_qms_core.group_pm_qms_manager").id])],
                "qms_organization_ids": [Command.set([self.organization_a.id])],
                "qms_site_ids": [Command.set([site_a.id])],
                "qms_process_ids": [Command.set([self.process_a.id])],
            }
        )

        Equipment = self.env["pm.qms.equipment"].sudo()
        equipment_a = Equipment.create(
            {"name": "M28 Gage A", "code": "M28-GAGE-A", "organization_id": self.organization_a.id, "site_id": site_a.id, "process_id": self.process_a.id}
        )
        equipment_b = Equipment.create(
            {"name": "M28 Gage B", "code": "M28-GAGE-B", "organization_id": self.organization_a.id, "site_id": site_b.id, "process_id": self.process_b.id}
        )
        Event = self.env["pm.qms.calibration.event"].sudo()
        event_a = Event.create({"equipment_id": equipment_a.id, "calibration_date": "2026-08-01"})
        event_b = Event.create({"equipment_id": equipment_b.id, "calibration_date": "2026-08-01"})
        Measurement = self.env["pm.qms.calibration.measurement.line"].sudo()
        measurement_a = Measurement.create({"event_id": event_a.id, "parameter": "M28 parameter A"})
        measurement_b = Measurement.create({"event_id": event_b.id, "parameter": "M28 parameter B"})
        Assessment = self.env["pm.qms.calibration.impact.assessment"].sudo()
        assessment_a = Assessment.create({"equipment_id": equipment_a.id, "event_id": event_a.id})
        assessment_b = Assessment.create({"equipment_id": equipment_b.id, "event_id": event_b.id})
        Affected = self.env["pm.qms.calibration.affected.reference"].sudo()
        affected_a = Affected.create({"assessment_id": assessment_a.id, "name": "M28 affected A"})
        affected_b = Affected.create({"assessment_id": assessment_b.id, "name": "M28 affected B"})

        Person = self.env["pm.qms.person"].sudo()
        person_a = Person.create({"name": "M28 Person A", "organization_id": self.organization_a.id, "site_id": site_a.id})
        person_b = Person.create({"name": "M28 Person B", "organization_id": self.organization_a.id, "site_id": site_b.id})
        person_c = Person.create({"name": "M28 Person C", "organization_id": self.organization_a.id, "site_id": site_b.id})
        role = self.env["pm.qms.role"].sudo().create({"name": "M28 Role", "code": "M28-ROLE", "company_id": self.company.id})
        competency = self.env["pm.qms.competency"].sudo().create({"name": "M28 Competency", "code": "M28-COMP", "company_id": self.company.id})
        requirement = self.env["pm.qms.role.competency.requirement"].sudo().create({"role_id": role.id, "competency_id": competency.id})
        Assignment = self.env["pm.qms.person.role.assignment"].sudo()
        assignment_a = Assignment.create({"person_id": person_a.id, "role_id": role.id})
        assignment_b = Assignment.create({"person_id": person_b.id, "role_id": role.id})
        AssessmentPerson = self.env["pm.qms.competency.assessment"].sudo()
        competency_a = AssessmentPerson.create({"person_id": person_a.id, "competency_id": competency.id})
        competency_b = AssessmentPerson.create({"person_id": person_b.id, "competency_id": competency.id})
        Matrix = self.env["pm.qms.competency.matrix.line"].sudo()
        matrix_a = Matrix.search([("person_id", "=", person_a.id), ("requirement_id", "=", requirement.id)], limit=1)
        matrix_b = Matrix.search([("person_id", "=", person_b.id), ("requirement_id", "=", requirement.id)], limit=1)
        Course = self.env["pm.qms.training.course"].sudo()
        course = Course.create({"name": "M28 Course", "code": "M28-COURSE", "company_id": self.company.id})
        Training = self.env["pm.qms.training.record"].sudo()
        training_a = Training.create({"person_id": person_a.id, "course_id": course.id})
        training_b = Training.create({"person_id": person_b.id, "course_id": course.id})
        QualificationType = self.env["pm.qms.qualification.type"].sudo()
        qualification_type = QualificationType.create({"name": "M28 Qualification", "code": "M28-QUAL", "company_id": self.company.id})
        Qualification = self.env["pm.qms.qualification.record"].sudo()
        qualification_a = Qualification.create({"person_id": person_a.id, "qualification_type_id": qualification_type.id})
        qualification_b = Qualification.create({"person_id": person_b.id, "qualification_type_id": qualification_type.id})
        Document = self.env["pm.qms.document"].sudo()
        document = Document.create(
            {
                "name": "M28 Controlled Procedure",
                "code": "M28-DOC-SCOPE",
                "organization_id": self.organization_a.id,
                "process_id": self.process_a.id,
            }
        )
        revision = self.env["pm.qms.document.revision"].sudo().create(
            {"document_id": document.id, "revision": "M28-A"}
        )
        Acknowledgment = self.env["pm.qms.document.acknowledgment"].sudo()
        acknowledgment_a = Acknowledgment.create({"person_id": person_a.id, "revision_id": revision.id})
        acknowledgment_b = Acknowledgment.create({"person_id": person_b.id, "revision_id": revision.id})

        site_scoped_records = (
            (
                "pm.qms.calibration.measurement.line",
                measurement_a,
                measurement_b,
                {"event_id": event_b.id, "parameter": "M28 unauthorized measurement"},
                {"notes": "M28 unauthorized edit"},
            ),
            (
                "pm.qms.calibration.impact.assessment",
                assessment_a,
                assessment_b,
                {"equipment_id": equipment_b.id, "event_id": event_b.id},
                {"notes": "M28 unauthorized edit"},
            ),
            (
                "pm.qms.calibration.affected.reference",
                affected_a,
                affected_b,
                {"assessment_id": assessment_b.id, "name": "M28 unauthorized reference"},
                {"description": "M28 unauthorized edit"},
            ),
            (
                "pm.qms.person.role.assignment",
                assignment_a,
                assignment_b,
                {"person_id": person_b.id, "role_id": role.id, "effective_date": "2026-09-02"},
                {"notes": "M28 unauthorized edit"},
            ),
            (
                "pm.qms.competency.assessment",
                competency_a,
                competency_b,
                {"person_id": person_c.id, "competency_id": competency.id},
                {"notes": "M28 unauthorized edit"},
            ),
            (
                "pm.qms.competency.matrix.line",
                matrix_a,
                matrix_b,
                {"person_id": person_c.id, "role_id": role.id, "requirement_id": requirement.id},
                {"person_id": person_a.id},
            ),
            (
                "pm.qms.training.record",
                training_a,
                training_b,
                {"person_id": person_c.id, "course_id": course.id},
                {"notes": "M28 unauthorized edit"},
            ),
            (
                "pm.qms.qualification.record",
                qualification_a,
                qualification_b,
                {"person_id": person_c.id, "qualification_type_id": qualification_type.id},
                {"notes": "M28 unauthorized edit"},
            ),
            (
                "pm.qms.document.acknowledgment",
                acknowledgment_a,
                acknowledgment_b,
                {"person_id": person_c.id, "revision_id": revision.id},
                {"person_id": person_c.id},
            ),
        )
        for model_name, in_scope, out_scope, create_values, write_values in site_scoped_records:
            scoped = self.env[model_name].with_user(site_user)
            self.assertIn(in_scope, scoped.search([]), model_name)
            self.assertNotIn(out_scope, scoped.search([]), model_name)
            self.assertEqual(scoped.search_count([]), 1, model_name)
            with self.assertRaises(AccessError, msg=model_name):
                out_scope.with_user(site_user).read()
            with self.assertRaises(AccessError, msg=model_name):
                scoped.create(create_values)
            with self.assertRaises(AccessError, msg=model_name):
                out_scope.with_user(site_user).write(write_values)
            with self.assertRaises(AccessError, msg=model_name):
                out_scope.with_user(site_user).unlink()
            with self.assertRaises(AccessError, msg=f"manager:{model_name}"):
                out_scope.with_user(manager).read()
