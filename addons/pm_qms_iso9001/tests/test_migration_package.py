from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.pm_qms_iso9001.hooks import PROFILE_CODE, post_init_hook


@tagged("-at_install", "post_install")
class TestPmQmsIso9001MigrationPackage(TransactionCase):
    def setUp(self):
        super().setUp()
        post_init_hook(self.env)
        manager_group = self.env.ref("pm_qms_core.group_pm_qms_manager")
        self.verifier = self.env["res.users"].create(
            {
                "name": "Migration Action Verifier",
                "login": "iso.migration.verifier@example.invalid",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "groups_id": [Command.set(manager_group.ids)],
            }
        )
        self.reviewer = self.env["res.users"].create(
            {
                "name": "Migration Package Reviewer",
                "login": "iso.migration.reviewer@example.invalid",
                "company_id": self.env.company.id,
                "company_ids": [Command.set(self.env.company.ids)],
                "groups_id": [Command.set(manager_group.ids)],
            }
        )
        self.organization = self.env["pm.qms.organization"].create(
            {
                "name": "Migration Package Test Organization",
                "code": "MIG-ORG",
                "company_id": self.env.company.id,
            }
        )
        self.project = self.env["pm.qms.implementation.project"].create(
            {
                "name": "Controlled ISO migration project",
                "company_id": self.env.company.id,
                "organization_id": self.organization.id,
                "project_manager_id": self.env.user.id,
                "date_start": fields.Date.today(),
                "target_date": fields.Date.today() + timedelta(days=90),
                "implementation_type": "migration",
            }
        )
        self.scenario = self.env["pm.qms.iso9001.transition.scenario"].search(
            [
                ("code", "=", "ISO9001-2026-TRANSITION-2015"),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        self.source_profile = self.env["pm.qms.mapping.profile"].search(
            [
                ("code", "=", PROFILE_CODE),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )

    def _approved_readiness_review(self):
        assessment = self.env["pm.qms.iso9001.gap.assessment"].create(
            {
                "name": "Migration package source assessment",
                "scenario_id": self.scenario.id,
                "source_profile_id": self.source_profile.id,
            }
        )
        assessment.action_start()
        assessment.line_ids.write({"status": "conforming"})
        line = assessment.line_ids[:1]
        line.write(
            {
                "status": "gap",
                "gap_description": "Controlled source gap.",
                "action_plan": "Complete the controlled migration prerequisite.",
                "responsible_id": self.env.user.id,
                "target_date": fields.Date.today() + timedelta(days=30),
            }
        )
        assessment.action_complete()
        assessment.action_generate_transition_plan()
        action = assessment.transition_action_ids
        action.write(
            {
                "implementation_project_id": self.project.id,
                "completion_summary": "Migration prerequisite completed.",
                "verification_evidence": "Independent evidence reviewed.",
            }
        )
        action.action_start()
        action.action_submit_verification()
        action.with_user(self.verifier).action_complete()

        review = self.env["pm.qms.iso9001.transition.review"]._prepare_from_assessment(
            assessment
        )
        review.write(
            {
                "reviewer_id": self.verifier.id,
                "decision": "internal_review",
                "review_basis": "Completed action and evidence reviewed.",
                "residual_risk_summary": "No uncontrolled transition risks remain.",
                "decision_notes": "Proceed to controlled migration package preparation.",
            }
        )
        review.action_submit()
        review.with_user(self.verifier).action_approve()
        return review

    def _complete_package_inputs(self, package):
        package.write(
            {
                "reviewer_id": self.reviewer.id,
                "migration_scope": "One company, approved sites, processes, and controlled records.",
                "source_inventory": "Controlled inventory reference INV-2026-001.",
                "compatibility_notes": "No unresolved compatibility exceptions.",
                "dry_run_plan": "Run in an isolated clone and compare record relationships.",
                "backup_reference": "BACKUP-2026-001",
                "backup_sha256": "a" * 64,
                "backup_verified": True,
                "rollback_plan": "Restore the approved backup and verify relationships.",
                "rollback_acceptance_criteria": "Historical records and relationships match the baseline.",
                "execution_window": "Approved maintenance window required separately.",
            }
        )

    def test_package_requires_approved_internal_review_and_is_idempotent(self):
        review = self._approved_readiness_review()

        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        same_package = review.action_prepare_migration_package()
        self.assertEqual(same_package["res_id"], package.id)
        self.assertEqual(package.company_id, review.company_id)
        self.assertEqual(package.source_edition_snapshot, "2015")
        self.assertEqual(package.target_edition_snapshot, "2026")

        with self.assertRaises(AccessError):
            self.env["pm.qms.iso9001.migration.package"].create(
                {
                    "name": "Forged package",
                    "code": "FORGED",
                    "readiness_review_id": review.id,
                }
            )

    def test_preflight_requires_verified_backup_and_freezes_manifest(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        package.write({"reviewer_id": self.reviewer.id})
        with self.assertRaises(UserError):
            package.action_run_preflight()

        self._complete_package_inputs(package)
        package.action_run_preflight()
        self.assertEqual(package.state, "preflight_passed")
        self.assertTrue(package.manifest_snapshot)
        self.assertEqual(len(package.manifest_sha256), 64)

        package.write({"compatibility_notes": "Updated compatibility evidence."})
        self.assertEqual(package.state, "draft")
        self.assertFalse(package.manifest_snapshot)
        self.assertFalse(package.manifest_sha256)

    def test_independent_approval_and_immutability(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        self._complete_package_inputs(package)
        package.action_run_preflight()
        package.action_submit()

        with self.assertRaises(AccessError):
            package.action_approve()
        package.with_user(self.reviewer).action_approve()
        self.assertEqual(package.state, "approved")
        self.assertEqual(package.approved_by_id, self.reviewer)
        with self.assertRaises(AccessError):
            package.write({"execution_window": "Historical rewrite"})

    def test_reviewer_must_have_company_access(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        foreign_company = self.env["res.company"].create(
            {"name": "Foreign Migration Company"}
        )
        foreign_reviewer = self.env["res.users"].create(
            {
                "name": "Foreign Migration Reviewer",
                "login": "iso.foreign.migration@example.invalid",
                "company_id": foreign_company.id,
                "company_ids": [Command.set(foreign_company.ids)],
                "groups_id": [
                    Command.set(
                        self.env.ref("pm_qms_core.group_pm_qms_manager").ids
                    )
                ],
            }
        )
        with self.assertRaises(ValidationError):
            package.write({"reviewer_id": foreign_reviewer.id})

    def test_preflight_rejects_placeholders_and_zero_digest(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        package.write(
            {
                "reviewer_id": self.reviewer.id,
                "backup_reference": "BACKUP-2026-001",
                "backup_verified": True,
                "execution_window": "Controlled maintenance window.",
            }
        )
        with self.assertRaisesRegex(UserError, "planning placeholder"):
            package.action_run_preflight()

        package.write(
            {
                "migration_scope": "Approved scope.",
                "source_inventory": "INV-2026-001.",
                "compatibility_notes": "No unresolved exceptions.",
                "dry_run_plan": "Isolated rehearsal required.",
                "rollback_plan": "Restore and verify.",
                "rollback_acceptance_criteria": "Baseline integrity restored.",
            }
        )
        with self.assertRaisesRegex(UserError, "placeholder backup SHA-256"):
            package.action_run_preflight()

    def test_returned_edit_clears_snapshot_and_submitted_void_is_reviewer_only(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        self._complete_package_inputs(package)
        package.action_run_preflight()
        package.action_submit()
        package.with_user(self.reviewer).write(
            {"return_reason": "Clarify compatibility evidence."}
        )
        package.with_user(self.reviewer).action_return()
        self.assertTrue(package.manifest_snapshot)

        package.write({"compatibility_notes": "Clarified compatibility evidence."})
        self.assertEqual(package.state, "draft")
        self.assertFalse(package.manifest_snapshot)
        self.assertFalse(package.manifest_sha256)

        package.action_run_preflight()
        package.action_submit()
        with self.assertRaises(AccessError):
            package.write({"void_reason": "Unauthorized void attempt."})
        package.with_user(self.reviewer).write(
            {"void_reason": "Package superseded before execution approval."}
        )
        package.with_user(self.reviewer).action_void()
        self.assertEqual(package.state, "voided")

    def test_manifest_has_no_execution_operation(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        self.assertFalse(hasattr(package, "action_execute"))
        self.assertFalse(hasattr(package, "action_migrate"))


    def _approved_execution_record(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        self._complete_package_inputs(package)
        package.action_run_preflight()
        package.action_submit()
        package.with_user(self.reviewer).action_approve()
        execution = self.env[
            "pm.qms.iso9001.migration.execution"
        ]._prepare_from_package(package)
        execution.write(
            {
                "operator_id": self.env.user.id,
                "reviewer_id": self.reviewer.id,
                "environment_reference": "ENV-CONTROLLED-001",
                "fresh_preflight_evidence": "Fresh environment checks passed.",
                "backup_access_evidence": "Approved backup was accessible.",
                "restoration_test_evidence": "Restoration rehearsal passed.",
                "dry_run_evidence": "Isolated dry run passed.",
                "authorization_notes": "Execution authorized for the approved window.",
            }
        )
        execution.action_run_preflight()
        execution.with_user(self.reviewer).action_authorize()
        return package, execution

    def test_execution_requires_approved_package_and_is_idempotent(self):
        review = self._approved_readiness_review()
        package = self.env["pm.qms.iso9001.migration.package"]._prepare_from_review(
            review
        )
        with self.assertRaises(UserError):
            self.env[
                "pm.qms.iso9001.migration.execution"
            ]._prepare_from_package(package)

        self._complete_package_inputs(package)
        package.action_run_preflight()
        package.action_submit()
        package.with_user(self.reviewer).action_approve()
        execution = package.action_prepare_execution_record()
        same_execution = package.action_prepare_execution_record()
        self.assertEqual(execution["res_id"], same_execution["res_id"])
        with self.assertRaises(AccessError):
            self.env["pm.qms.iso9001.migration.execution"].create(
                {"name": "Forged", "code": "FORGED", "package_id": package.id}
            )

    def test_execution_has_independent_authorization_and_no_executor(self):
        package, execution = self._approved_execution_record()
        self.assertEqual(execution.state, "authorized")
        self.assertEqual(execution.package_manifest_sha256, package.manifest_sha256)
        self.assertFalse(hasattr(execution, "action_execute"))
        self.assertFalse(hasattr(execution, "action_migrate"))
        with self.assertRaises(AccessError):
            execution.with_user(self.reviewer).action_record_start()

    def test_execution_records_counts_outcome_and_independent_closeout(self):
        _package, execution = self._approved_execution_record()
        execution.action_record_start()
        execution.write(
            {
                "execution_log_reference": "LOG-IMMUTABLE-001",
                "execution_log_sha256": "b" * 64,
                "post_migration_checks": "Historical records and relationships verified.",
                "rollback_decision": "not_required",
                "outcome": "completed",
                "created_count": 12,
                "reused_count": 8,
                "skipped_count": 2,
                "rejected_count": 1,
                "manual_review_count": 3,
            }
        )
        execution.action_record_outcome()
        execution.action_submit_closeout()
        with self.assertRaises(AccessError):
            execution.action_close()
        execution.with_user(self.reviewer).write(
            {"closeout_notes": "Independent checks and counts accepted."}
        )
        execution.with_user(self.reviewer).action_close()
        self.assertEqual(execution.state, "closed")
        self.assertEqual(execution.closed_by_id, self.reviewer)
        with self.assertRaises(AccessError):
            execution.write({"post_migration_checks": "Rewrite history."})

    def test_execution_rollback_evidence_and_negative_counts_are_enforced(self):
        _package, execution = self._approved_execution_record()
        execution.action_record_start()
        with self.assertRaises(ValidationError):
            execution.write({"rejected_count": -1})
        execution.write(
            {
                "execution_log_reference": "LOG-IMMUTABLE-ROLLBACK",
                "execution_log_sha256": "c" * 64,
                "post_migration_checks": "Failure detected before closeout.",
                "rollback_decision": "executed",
                "outcome": "rolled_back",
            }
        )
        with self.assertRaisesRegex(UserError, "rollback evidence"):
            execution.action_record_outcome()
        execution.write({"rollback_evidence": "Restore completed and verified."})
        execution.action_record_outcome()
        self.assertEqual(execution.state, "recorded")

    def test_editing_preflight_controls_invalidates_snapshot(self):
        _package, execution = self._approved_execution_record()
        execution._write_workflow({"state": "returned"})
        execution.write({"dry_run_evidence": "Updated isolated dry-run evidence."})
        self.assertEqual(execution.state, "draft")
        self.assertFalse(execution.control_snapshot)
        self.assertFalse(execution.control_sha256)
