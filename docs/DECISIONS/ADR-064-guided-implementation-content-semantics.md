# ADR-064: Guided Implementation Content Semantics

Status: Accepted

## Context

Perfect Match guided implementation content needs activity-level semantics
without adding a second template, phase, step, evidence, or readiness model.
The generic implementation engine must remain usable by future standards and
must keep project administration separate from QMS readiness.

## Decisions

- `pm.qms.framework.pack` code and version remain the methodology and template
  version boundary.
- `pm.qms.framework.area` represents an implementation phase inside a pack.
- `pm.qms.activity` is extended rather than replaced.
- Activities carry generic objective, rationale, implementation guidance,
  success criteria, classification, and readiness participation semantics.
- `readiness_required` defaults to true for backward compatibility.
- Activities classified as `project_administration` are never readiness
  requirements.
- Generated task `pm_required` is true only when both the implementation
  control and activity require readiness.
- No Step model or dependency model is introduced at this stage.
- The existing readiness engine remains the single readiness calculation path.
- The generic engine remains standard-neutral.
- ISO-specific content remains in `pm_qms_iso9001` and is not loaded here.

## Consequences

Existing activities continue to participate in readiness by default. New
administrative or supporting activities can exist operationally without
inflating or blocking QMS readiness. Future ISO content can reuse the same
generic activity semantics while remaining versioned by its framework pack.
