# ISO 9001:2026 Transition Action Plan

## Purpose

Perfect Match QMS converts completed edition-gap assessments into controlled
transition actions. This creates a traceable execution layer without copying
licensed standard text and without rewriting the historical assessment.

## Controlled flow

1. A QMS Manager completes an ISO 9001 edition gap assessment.
2. **Generate Transition Plan** creates one action for every area classified as
   partially addressed or gap.
3. Generation is idempotent: each assessment area can create only one action.
4. The action snapshots the focus area, gap description, remediation plan,
   source disposition, owner, target date, and company.
5. The responsible team records progress, completion summary, and verification
   evidence.
6. A QMS Manager submits the action for verification and then verifies closure.
7. Completed actions become immutable historical records.

Conforming and not-applicable areas do not generate transition actions.

## Workflow

| State | Meaning | Required transition |
| --- | --- | --- |
| Draft | Generated from the completed assessment | Start or submit for verification |
| In Progress | Remediation work is underway | Submit for verification |
| Verification | Completion evidence awaits review | Verify and complete |
| Completed | Closure was verified and timestamped | Immutable |
| Cancelled | Action was withdrawn before completion | No further transition |

Submission requires both a completion summary and verification evidence.

## Priority

- A source status of **Gap** generates an **Urgent** action.
- A source status of **Partially Addressed** generates a **High** action.
- Managers may adjust priority, owner, date, progress notes, and an optional
  implementation-project link before completion.

## Authorization and isolation

- QMS users and viewers have read-only access.
- QMS Managers and Administrators manage the workflow.
- Direct record creation is rejected; actions are generated only from a
  completed assessment.
- Workflow and snapshot fields cannot be written directly, including through
  caller-supplied RPC context.
- Global company rules isolate records by the immutable company snapshot.
- A linked implementation project must belong to the same company.

## Historical integrity

The completed gap assessment remains unchanged. Transition actions retain their
own source snapshots and closure audit fields, so later execution updates do not
alter the assessment used to authorize the plan.

This feature supports planning and evidence management. It does not claim
certification, conformity, or approval by ISO or any certification body.
