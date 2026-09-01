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
            }
        )
        cls.capa_b = cls.env["pm.qms.capa"].sudo().create(
            {
                "name": "M28 Reproduction CAPA B",
                "organization_id": cls.organization_a.id,
                "process_id": cls.process_b.id,
                "problem_statement": "M28 fictional process B issue.",
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
            with self.assertRaises(AccessError):
                scoped.create(dict(in_scope_values, capa_id=self.capa_b.id))

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
