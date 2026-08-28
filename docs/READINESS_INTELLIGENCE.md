# Deterministic Readiness Intelligence

Perfect Match QMS presents readiness gaps and one recommended next action per
applicable, non-ready implementation control. The result is explainable
guidance derived from the current control, required activities, and formal
evidence state. It does not use AI and it does not change workflow state.

## Decision order

The engine evaluates these blockers in order:

1. implementation not started
2. overdue required activity
3. open required activity
4. submitted or under-review evidence
5. rejected or expired evidence
6. missing accepted formal evidence
7. implementation final review
8. other manual review

The blocker summary can list multiple active factors, while the recommended
action selects the first actionable factor. Ready and not-applicable controls
produce no action.

## Routing and ranking

An activity action opens its exact generated Odoo task. An evidence follow-up
opens its exact evidence record. Missing formal evidence opens the evidence list
filtered to the exact control instance and requirement; it never creates a
record automatically. Review and start actions open the implementation control.

The Readiness Center ranks overdue items first, then gap and partial state,
earliest open task deadline, area sequence, control sequence, and record ID.
It shows at most 12 actions by default. Priority is high for overdue, gap, and
rejected/expired evidence; normal for open or review work; low only for the
fallback manual-review case.

The activity success criteria are the preferred done-when text, with expected
output as fallback. Evidence actions use the requirement acceptance criteria.
These are guidance only and do not accept evidence or complete workflow steps.

## Historical snapshots

Completed readiness assessments copy the blocker summary, recommended action,
and done-when text into their item snapshots. Completed assessments do not
recompute those values when the live implementation changes.

## Boundaries

The engine is generic and lives in pm_qms_implementation. It remains
standard-neutral and works with any compatible framework pack. It reuses the
existing implementation control, project, readiness center, evidence, and
task models; it does not add a Step, Phase, Template, AI, or dependency model.
No certification or compliance guarantee is implied.
