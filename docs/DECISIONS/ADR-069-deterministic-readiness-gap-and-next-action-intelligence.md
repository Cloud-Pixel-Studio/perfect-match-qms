# ADR-069: Deterministic Readiness Gap and Next-Action Intelligence

## Status

Accepted for Mission 25.9 implementation.

## Context

Implementation teams need a concise explanation of why a control is not ready
and a practical next action. Existing readiness counts and states are the
authoritative inputs, but a single gap reason does not show all active blockers
or route the user to the exact task or evidence record.

## Decision

Add a reusable deterministic evaluation on the existing
pm.qms.implementation.control model. It returns ephemeral blocker and action
values and powers readonly control guidance and the transient Readiness Center.
The evaluation uses the existing required activity, task, formal evidence, and
requirement records.

The precedence is work before paperwork: start implementation, overdue and
open required activities, evidence review, evidence correction, missing formal
evidence, final review, then manual review. The Readiness Center ranks results
deterministically and limits the default result to twelve actions.

Evidence actions route to an exact evidence record when one exists. Missing
evidence routes to a filtered evidence list for the control and requirement.
No route creates records, changes workflow state, accepts evidence, or bypasses
access controls.

Completed readiness assessment items snapshot the blocker and action text.
Historical snapshots remain immutable and are not recomputed from live state.

## Consequences

The implementation engine stays generic and standard-neutral. ISO 9001 and
future framework packs can use the same behavior without moving standard
content into the generic addon. Guidance is explainable and reviewable, but it
is not an automated certification decision. Existing readiness percentages,
N/A handling, and gap reasons remain unchanged.
