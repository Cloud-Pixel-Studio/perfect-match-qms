# Formal Evidence Acceptance

M25.8 adds reviewer-facing acceptance criteria to reusable Perfect Match QMS
evidence requirements.

## Runtime behavior

A requirement can have a stable definition key and a short list of observable
conditions. Evidence records expose the requirement description and acceptance
criteria as read-only context. A reviewer still uses the normal evidence
workflow to submit, review, accept, reject, or expire evidence.

Live readiness ignores inactive requirements, inactive evidence, and expired
evidence. Controls marked Not Applicable are excluded from evidence and
required-activity readiness denominators. Historical readiness assessments keep
their immutable snapshots.

## Development

The quality pack update is idempotent. It first matches a definition key, then
adopts exactly one legacy record with the same control and name. Zero or
ambiguous matches are handled explicitly; incompatible ownership is rejected.

The ISO 9001 add-on contains a reference-only evidence crosswalk. It carries
activity keys, generic control codes, evidence definition keys, and policy
metadata only.

No historical source package, source-derived dataset, customer data, user
data, chatter, raw prompt, or standard requirement text is committed.
