# ADR-073: M27 Security Hardening and Authorization Boundaries

## Status

Accepted for controlled DEV implementation; merge and production deployment
remain separately authorized gates.

## Context

Perfect Match QMS requires tenant and organization isolation, read-only QMS
Viewer behavior, a separate licensing administration role, and explicit
evidence for direct-record and RPC-style access. The v1.0 product has no
supported portal/public QMS surface. M27 must strengthen these boundaries
without changing Demo data, RC11, ISO content, or mail/chatter architecture.

## Decision

1. Test authorization with a disposable two-company, two-organization DEV ORM
   fixture and direct record operations.
2. Keep QMS Viewer read-only for business records and transient dashboard
   helpers; enforce cross-company and cross-organization isolation through the
   existing ACL and record-rule model.
3. Remove the unintended implication from QMS Licensing Administrator to QMS
   Administrator. Licensing administration remains a distinct workflow role;
   framework master-data and user administration remain unavailable.
4. Keep portal/public QMS access unsupported in v1.0 rather than adding a new
   route or controller.
5. Inventory all `sudo()` calls for conservative follow-up review. Privileged
   reads/writes must remain narrow, scoped, and independent of customer-facing
   record aggregation.
6. Keep mail.thread, mail.activity, chatter, followers, attachments and
   workflow behavior unchanged in this mission.

## Consequences

The licensing role has a narrower authority boundary and a regression test
protects it. Security fixture tests document tenant, role, direct-ID, and
transient-helper behavior. Existing production sudo call sites are explicitly
visible in the M27 evidence package for later call-site review.

## Non-goals

M27 does not add portal functionality, change customer records, change Demo or
production, alter ISO content, modify RC11, or redesign mail infrastructure.
