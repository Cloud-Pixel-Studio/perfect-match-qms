# ADR-070: QMS Activity & History customer record history

## Status

Accepted for implementation in the customer-facing QMS shell.

## Context

Perfect Match QMS needs a clear record-history experience for field changes,
Internal Notes, scheduled Activities, attachments, and existing business
events. Odoo already provides the storage, access checks, tracking values,
activity lifecycle, followers, and notification infrastructure required for
that experience. A second audit-log engine would split provenance and create
duplicate history.

## Decision

Use Strategy D and retain native `mail.thread`, `mail.activity.mixin`,
`mail.message`, and `mail.tracking.value` as the underlying mechanism.

- Real human authors, timestamps, and old/new values remain stored and shown as
  the real human attribution.
- The stable `base.partner_root` actor is marked for presentation only. On a
  Perfect Match customer QMS chatter surface it is presented as
  `Perfect Match QMS · System`; stored authors are not rewritten.
- The customer surface is named **QMS Activity & History**.
- Normal customer QMS users receive Internal Notes, Activities, attachments,
  and required notifications without the general-purpose Send Message or
  manual follower controls being primary entry points. The underlying mail
  infrastructure remains enabled.
- Published PM QMS notes and tracked history are protected from ordinary
  customer editing and deletion. Technical Administrators retain the existing
  exceptional diagnostic path.
- `pm.qms.event` remains the deterministic domain-event mechanism and is not
  merged with mail history.

The presentation code is scoped to `pm.qms.*` threads and the existing
`o_pm_qms_customer_shell` marker. Native Odoo behavior outside the PM QMS
customer shell is unchanged. No system user or partner is created and there
is no licensing impact.

The pinned Odoo 19 `mail.Chatter` template was inspected as part of this
decision. Its Send Message and Followers entry points are native unconditional
controls, so the addon applies the customer-history predicate only within the
PM QMS shell. Native permission and disabled-state checks remain in force;
`mail.activity`, record chatter, tracking, and required notifications are not
disabled, and non-PM chatter retains the native runtime behavior.

## Consequences

The product gets one readable customer history surface while preserving native
Odoo provenance and notification behavior. Corrections to a published note or
history entry are recorded as a new business note rather than by rewriting the
original. Future customer workflows may explicitly re-enable external message
posting when their requirements are defined.

## Boundaries

This decision does not change ISO content, standards mappings, the broad set of
tracked fields, customer data, deployment environments, or release tags. It
does not rename OdooBot globally, migrate historical authors, or introduce a
general chat product.
