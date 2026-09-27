# ISO 9001:2026 customer transition playbook

## Purpose and boundaries

This playbook routes a customer through the existing ISO 9001:2026 scenario, gap-assessment, transition-action, readiness-review, migration-package, execution-record, and record-reconciliation workflows.

It is planning and governance guidance. It does not install or upgrade PMQMS, connect to a customer system, import or alter customer records, perform a migration, or determine conformity or certification. A licensed copy of the applicable standard must be reviewed by an authorized human. Do not reproduce its publication text in PMQMS records, source code, tests, or this playbook.

Keep three baselines distinct:

1. the customer’s quality-management-system scope and source edition;
2. the PMQMS software version and deployment environment;
3. the customer’s target ISO 9001 edition and intended scope.

A PMQMS software upgrade does not by itself transition a customer’s QMS to ISO 9001:2026. If both are needed, approve and control them as separate workstreams with separate backups, change windows, verification, and rollback decisions.

## Scenario routing

Record the applicable scenario in the ISO 9001 transition-scenario workflow before creating an assessment. Select one primary route; record additional scope or deployment conditions as related project risks and constraints.

| Scenario type | Use when | Route and boundary |
| --- | --- | --- |
| New implementation | The customer has no established QMS to transition. | Use the active 2026 target profile as the implementation baseline. Do not invent source records or migration counts. Plan initial records and processes through the implementation project. |
| 2015 to 2026 transition | The existing QMS is based on ISO 9001:2015. | Preserve the 2015 profile, evidence, and completed history. Assess against the approved 2026 profile; reconcile each migrated, reused, skipped, rejected, or manually reviewed source record. |
| Legacy or incomplete system migration | The source is an older, non-standard, incomplete, or unverified QMS. | Inventory what can be evidenced, classify unknown provenance as manual review, and do not infer an ISO edition or claim prior conformity. Preserve the source system and its records. |
| Recertification | The work is a recertification cycle without an edition or scope transition. | Keep the existing edition and scope explicit. Route any edition transition or scope change through a separate linked assessment and approval. Certification-body requirements remain outside this product workflow. |
| Scope expansion | Products, services, processes, locations, or organizational boundaries are changing. | Freeze the current approved scope as the baseline, document additions and exclusions, assess their impact, and verify affected actions before release. |
| Multi-site rollout | An approved QMS is being extended across sites. | Define the company-wide scope and site-specific applicability, owners, evidence, and rollout sequence. Preserve company/site boundaries and verify each site before declaring the project complete. |
| Integrated management system | The customer coordinates ISO 9001 with other management systems. | This workflow covers ISO 9001 only. Track interfaces and dependencies in the project; do not imply that other standards or their requirements are implemented by this ISO 9001 add-on. |
| Partial implementation | The customer intentionally limits the initial rollout. | Record included sites/processes and exclusions, justify non-applicability, and report readiness only for the controlled scope. Do not present a partial rollout as organization-wide completion. |

If the source edition, ownership, scope, or records cannot be established, pause at intake and resolve the uncertainty before approving a migration package.

## Roles

Assign named people in the customer’s authorized company context. A person may hold more than one project role only where the workflow’s independence rules allow it.

- **Executive sponsor / customer process owner:** approves scope, risk tolerance, funding, and the maintenance window.
- **QMS transition lead:** coordinates the assessment, action plan, inventory, and status review.
- **Process owners:** provide source-system facts, complete assigned actions, and confirm operational readiness.
- **Migration operator:** performs the separately authorized external activity and records its evidence and reconciliation.
- **Independent reviewer:** approves the readiness/package gates and independently verifies closeout. The operator cannot approve or close their own work.
- **Technical lead:** owns environment compatibility, backup, restore rehearsal, access, and technical post-checks.
- **Records custodian:** confirms source retention, retention obligations, evidence access, and preservation controls.

Use PMQMS’s role and company access controls; technical administration is not business approval.

## Stage gates

### Gate 0 — Intake and route

Capture the customer, company, scope, current QMS edition/status, PMQMS software version, source platforms, target platform, sites, processes, external constraints, and desired outcome as controlled project references.

Choose the scenario above. If the PMQMS software is also changing, create a separate software-upgrade plan. Record the relationship between workstreams without combining their approval or rollback evidence.

**Hold if:** source edition or scope is unknown, no accountable sponsor exists, required licensed-standard review is unavailable, or the proposed work mixes unrelated product deployment and QMS transition without separate controls.

### Gate 1 — Source inventory and preservation plan

Create a controlled inventory outside free-text PMQMS notes. Record only non-secret references and aggregate planning metadata in PMQMS. Keep raw exports, personal data, credentials, database dumps, and attachments in their approved controlled repositories.

For each source category, identify its system, record owner, approximate count, date range, retention requirements, relationships, target treatment, and evidence reference. Define how the historical source remains accessible and protected after transition.

**Accept when:** inventory scope is reviewed, owners are assigned, exclusions are explicit, preservation and retention controls are approved, and sensitive artifacts remain outside PMQMS.

### Gate 2 — Edition-specific assessment

Create the assessment from the selected active scenario and target profile. An authorized reviewer evaluates each Perfect Match-authored assessment area using the available evidence and the licensed standard outside the application.

Use the supported assessment outcomes (conforming, partial, gap, or not applicable). Every partial/gap requires a corrective plan, accountable owner, and due date. Every not-applicable decision requires a documented, scope-specific rationale.

Do not copy standard text into assessment fields. Cite controlled evidence by non-secret reference.

**Accept when:** every area has an evidence-based disposition, required justifications and action plans are complete, and the assessment is completed and frozen.

### Gate 3 — Transition actions and follow-up

Generate actions only from partial/gap findings. Confirm each action has an accountable owner, target date, priority, project link, and progress plan. Owners record progress; completion requires a summary and evidence; a different authorized verifier closes the action.

Review due, overdue, blocked, and returned actions on a regular project cadence. Escalate overdue critical actions to the sponsor and transition lead. Do not close an action solely because a target date passed or a software update completed.

**Accept when:** all actions required to proceed are independently verified, or an authorized readiness review explicitly chooses to continue controlled actions with documented residual risk. The latter is not authorization to execute a migration package.

### Gate 4 — Independent readiness decision

Prepare the readiness review from the completed assessment. Snapshot the action state and counts. The submitter and reviewer must be different authorized users.

The reviewer records one controlled decision:

- **Hold transition** while material prerequisites or risks remain unresolved.
- **Continue controlled actions** when remediation must continue before package approval.
- **Proceed to internal review** only after all transition actions are completed and independently verified.

A review decision is a governance gate, not a conformity or certification statement.

### Gate 5 — Migration package and technical preflight

Prepare the versioned package only from an approved readiness review with the internal-review decision. Record:

- scope, sites, processes, included source categories, and exclusions;
- source inventory reference and compatibility findings;
- target environment reference and approved software versions;
- isolated dry-run steps and acceptance results;
- backup reference, SHA-256, accessibility, and successful restoration rehearsal;
- rollback owner, steps, decision point, maximum recovery window, and acceptance criteria;
- independent reviewer and proposed maintenance window.

The package must be independently approved before an execution record is prepared. Any changed package input invalidates the prior approval and requires a new preflight/review.

**Hold if:** backup restoration has not been proven, the isolated rehearsal failed, unresolved compatibility issues lack disposition, the target is not isolated from production during rehearsal, or rollback cannot meet the approved recovery criteria.

### Gate 6 — Execution authorization

Prepare the controlled execution record from the approved package. Assign an operator and a different independent reviewer. Before authorization, refresh environment preflight evidence, verify the approved backup and restoration test, verify isolated dry-run evidence, and record explicit authorization and the target reference.

The reviewer authorizes only the unchanged, integrity-checked controls. The operator records start only after the approved window begins. PMQMS records the governance workflow; the separately operated migration remains outside PMQMS.

### Gate 7 — External execution and record reconciliation

During the separately authorized activity, keep immutable logs and evidence in approved repositories. Enter one reconciliation line for each inventoried source record or approved source unit, using opaque non-secret identifiers only.

Use the supported dispositions consistently:

- **Created:** a new target record was created; include its target reference.
- **Reused:** an existing target record was verified and reused; include its target reference.
- **Skipped:** intentionally excluded under the approved scope; document why.
- **Rejected:** not migrated because a defined validation or policy gate failed; document disposition and owner.
- **Manual review:** requires a human decision; it remains open until a controlled resolution exists.

Explicitly attest that each historical source remains preserved. Do not mark a record complete while its disposition is unknown. Reconciliation counts are derived from ledger rows; they are not estimates entered as totals.

### Gate 8 — Post-checks, rollback decision, and closeout

Compare approved source and target inventories at the agreed level. Verify record counts by category, required relationships, critical identifiers, access/role behavior, document/evidence references, site/process scope, and application health. Record exceptions and evidence references; do not paste source content into the execution record.

The operator records the outcome, immutable-log reference and SHA-256, post-migration checks, reconciliation, and rollback decision. If rollback is executed, attach its controlled evidence. The operator submits closeout; the independent reviewer either returns it with a reason or verifies the frozen report and closes it.

## Acceptance and stop criteria

A transition may be reported as operationally accepted only when all of the following are true:

- the approved scope and target edition match the executed package;
- all required transition actions are independently verified;
- the approved backup is recoverable and the rollback decision is documented;
- every in-scope source inventory item has a reconciliation disposition;
- no unresolved manual-review item or rejected critical record is hidden in aggregate counts;
- target counts and relationships meet the package’s acceptance criteria;
- post-migration access, site/process boundaries, and required QMS workflows pass;
- the execution report and its evidence references pass independent closeout.

Stop and preserve the current state if the actual target differs from authorization, source history may be lost, integrity checks fail, a critical relationship or access boundary fails, backup/rollback evidence is unavailable, or an unapproved scope change is discovered. Record a failed or rolled-back outcome through the execution workflow; do not silently edit a frozen report.

Acceptance under this playbook means the controlled project gates were completed. It is not a claim of conformity, certification, or certification-body approval.

## Evidence and data protection

Store in PMQMS only the approved scope, decisions, non-secret references, concise rationales, workflow evidence, hashes, and controlled snapshots. Store credentials, private keys, connection strings, database dumps, raw exports, personal data, and licensed standard publication text only in their separately approved systems.

Preserve ISO 9001:2015 records as historical records when applicable. A target profile or new software version must not rewrite completed historical assessments, evidence, approvals, or reports.
