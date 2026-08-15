# Mission 05 Plan: Internal Audit Foundation

## Objective

Build the reusable internal audit foundation and connect it to the existing
operational QMS layer.

## Business Requirement

Perfect Match Digital QMS needs audit programs, individual audits, audit scope,
criteria, evidence, findings, and controlled handoff from internal
nonconformity findings to NCR and CAPA. Audit completion must not hide open
corrective action.

## Technical Approach

- Add `pm_qms_audit` as a separate Odoo addon depending on `pm_qms_capa`.
- Model audit programs and audits separately.
- Normalize scope, criteria, plan lines, evidence, and findings.
- Record auditor independence through confirmation metadata or documented
  override rather than simplistic organization rules.
- Create NCRs only from findings classified as internal nonconformity.
- Reuse existing NCR-to-CAPA flow for corrective action.
- Log meaningful workflow transitions in `pm.qms.event`.

## Components Affected

- New addon: `addons/pm_qms_audit/`.
- Existing NCR model gains source audit, source finding, and source audit
  evidence relationships.
- Existing control instance and process views gain audit/finding relationships
  and metrics.
- DEV script and CI workflow gain Mission 05 targets.

## Database Changes

New models:

- `pm.qms.audit.program`
- `pm.qms.audit`
- `pm.qms.audit.scope`
- `pm.qms.audit.criterion`
- `pm.qms.audit.plan.line`
- `pm.qms.audit.evidence`
- `pm.qms.audit.finding`

Extended model:

- `pm.qms.nonconformity`

## Security Implications

All new models require ACLs and company-boundary record rules. QMS Users can
read permitted audit records and create audit evidence, but cannot manage audit
workflow or issue/close findings. QMS Managers manage lifecycle actions. QMS
Administrators receive full module administration.

## Dependencies

`pm_qms_audit` depends on `pm_qms_capa`, which brings the existing NCR, risk,
evidence, documents, and core dependency chain.

## Testing Strategy

Run:

```bash
./deployment/scripts/odoo-dev.sh test-core
./deployment/scripts/odoo-dev.sh test-mission03
./deployment/scripts/odoo-dev.sh test-mission04
./deployment/scripts/odoo-dev.sh test-mission05
python3 deployment/scripts/validate-addons.py
python3 deployment/scripts/secret-scan.py
```

Mission 05 tests must cover workflow, security, multi-company isolation,
attachment isolation, independence review, finding classification, NCR handoff,
and audit/NCR/CAPA lifecycle independence.

## Acceptance Criteria

- `pm_qms_audit` installs.
- Existing Mission 02-04 tests continue to pass.
- Audit program, audit, scope, criteria, plan, evidence, and finding models
  work.
- Only internal nonconformity findings create NCRs under the normal workflow.
- Audit can complete while findings, NCRs, and CAPAs remain open.
- No external standard text is added.
- Plane items are updated through the official API.

## Rollback Considerations

Before production use, rollback is standard Odoo addon rollback in DEV: restore
a database/filestore backup or uninstall the addon before operational audit data
is created. Once audit records exist, preserve history and prefer corrective
migrations over destructive removal.
