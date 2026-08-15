# pm_qms_management_review

`pm_qms_management_review` implements the Perfect Match Digital QMS Management
Review engine.

The addon creates client operational records for:

- management review headers, periods, participants, workflow, and conclusion;
- historical review inputs captured from operational QMS data;
- management decisions;
- management review follow-up actions.

## Snapshot Principle

Management Review preserves what management reviewed at the time of the review.
It is not a live dashboard.

Generated review inputs store historical values such as KPI actual result, KPI
target snapshot, objective status, audit finding state, CAPA state, NCR state,
and previous action status. Later updates to live operational records do not
rewrite completed review inputs.

## Snapshot Sources

Mission 07 uses controlled Odoo ORM logic to collect:

- objectives;
- KPI measurements;
- customer performance and satisfaction;
- supplier performance and evaluations;
- audits and open audit findings;
- risks and opportunities;
- NCR;
- CAPA;
- previous management review actions.

No arbitrary SQL, Python expression engine, or generic user-configured model
access is implemented.

## Locking Policy

- Draft and preparing reviews may regenerate system-generated inputs.
- Manual inputs are preserved during regeneration.
- Ready, in-progress, completed, and cancelled reviews are locked against
  normal snapshot regeneration.
- Completed review history requires QMS Administrator correction authority.
- Management review actions can remain open after the meeting is completed.

## Security

All persisted models have ACLs and company record rules. Snapshot records follow
the management review company and organization. Tests verify that another
company cannot read reviews, inputs, decisions, actions, or generated snapshot
content.
