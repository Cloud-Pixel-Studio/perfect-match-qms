# Changelog

## 0.4.0 - 2026-08-14

- Added `pm_qms_audit` with audit programs, audits, scope, criteria, planning,
  audit evidence, findings, controlled workflows, overdue indicators, and tests.
- Added auditor independence metadata with confirmation and documented override
  handling before an audit can move to ready.
- Added audit finding classifications for conformity, observation, opportunity
  for improvement, and internal nonconformity.
- Added controlled audit finding to NCR integration with source audit, source
  finding, audit evidence, and downstream NCR-to-CAPA continuity.
- Extended control instance and process views with audit/finding relationships
  and open finding metrics.
- Updated CI and DEV script targets for Mission 05 validation.
- Added Mission 05 architecture, security, testing, plan, and ADR documentation.

## 0.3.0 - 2026-08-14

- Added `pm_qms_risk` with risk/opportunity records, configurable scoring thresholds, workflow actions, overdue logic, attachments, and tests.
- Added `pm_qms_ncr` with nonconformity records, containment, investigation, verification, closure controls, relationships, and tests.
- Added `pm_qms_capa` with CAPA headers, 5 Why entries, multiple actions, effectiveness review, NCR/Risk source creation, and tests.
- Added `pm.qms.event` for lightweight operational workflow history across critical transitions.
- Hardened direct state changes for control instances and operational workflows.
- Added Mission 04 DEV script targets, CI workflow, addon validation, secret scan, and DEV backup/restore scripts.
- Added CI, backup/recovery, security, architecture, and ADR documentation for Mission 04.

## 0.2.0 - 2026-08-14

- Added `pm.qms.control.instance` to separate reusable Perfect Match framework controls from client implementation status.
- Added `pm_qms_documents` with controlled documents, document revisions, approval workflow, and attachment linkage.
- Added `pm_qms_evidence` with actual evidence records, evidence review workflow, and evidence completion counts.
- Added multi-company tests for control instances, documents, revisions, and evidence.
- Added security architecture documentation and ADRs for security, implementation separation, and document revisions.
- Added Mission 03 DEV script targets for install, update, and tests.

## 0.1.0 - 2026-08-14

- Added isolated Odoo 19 DEV Docker Compose stack with PostgreSQL 15 under `deployment/docker/dev/`.
- Added `deployment/scripts/odoo-dev.sh` for secrets, config validation, startup, install, and tests.
- Generated DEV runtime secrets outside Git under `/opt/perfect-match/secrets/odoo-dev/`.
- Scaffolded `pm_qms_core` as the first Odoo addon.
- Added QMS organization, process, proprietary control, implementation activity, evidence requirement, and external mapping models.
- Added QMS User, QMS Manager, and QMS Administrator groups with access rights and company-boundary record rules.
- Added sequence data, menus, native Odoo views, and post-install tests.
- Added DEV environment, architecture, testing documentation, and ADR-010.
- Validated `pm_qms_core` install and tests on Odoo 19.

## 0.0.1 - 2026-08-14

- Created engineering repository structure.
- Added agent instructions and planning framework.
- Added product, architecture, security, deployment, workflow, and IP policy documentation.
- Added initial ADRs.
- Added Plane project-management source files.
- Added initial 52-item engineering backlog.
- Added placeholder Odoo addon, standard pack, framework, deployment, and test directories.
