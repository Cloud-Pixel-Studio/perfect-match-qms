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
   fixture and direct record operations across public, portal, customer, and
   technical personas.
2. Keep QMS Viewer read-only for business records and transient dashboard
   helpers; enforce cross-company, cross-organization, owner, and dashboard
   organization isolation through ACLs and global record rules.
3. Remove the unintended implication from QMS Licensing Administrator to QMS
   Administrator with an idempotent `Command.unlink` update. Licensing
   administration remains a distinct workflow role; framework master-data and
   user administration remain unavailable.
4. Keep portal/public QMS access unsupported in v1.0 rather than adding a new
   route or controller. The test covers direct model, direct-ID, attachment,
   and message-post side channels.
5. Inventory all `sudo()` calls for conservative follow-up review, separating
   existing production call sites from disposable test setup. Each production
   site records its caller, input provenance, pre-sudo scope, output/mutation,
   audit behavior, regression evidence, risk and follow-up; no M27 site adds
   privilege.
6. Generate authorization evidence from an explicit runtime-case registry.
   Source-only model rows remain risk-classified review items; P0/P1 rows are
   emitted only when a named runtime boundary test executes them. Native
   report/import/export HTTP behavior is not falsely certified and is deferred
   to the appropriate endpoint-validation mission.
7. Keep mail.thread, mail.activity, chatter, followers, attachments and
   workflow behavior unchanged in this mission.
8. Cover the entitlement service organization-capacity `sudo()` boundary with
   a disposable two-company ORM test that counts only active operational
   organizations for the requested company and returns counts rather than
   records. Compute unresolved P0/P1 and deferred-P2 evidence from inventory
   rows; never publish hardcoded zeroes.

## Consequences

The licensing role has a narrower authority boundary and an update-idempotency
regression test protects it. The affected runtime addons are versioned at
`pm_qms_app` `19.0.1.4.5` and `pm_qms_license` `19.0.1.0.1`. Security fixture tests document tenant, role,
direct-ID, transient-helper, portal/public, owner, organization, framework
administration, and native action behavior. The deterministic authorization
inventory and exact production sudo call-site inventory are included as review
evidence; existing production sudo sites remain bounded P2 follow-up where
appropriate, not a new M27 privilege.

## Non-goals

M27 does not add portal functionality, change customer records, change Demo or
production, alter ISO content, modify RC11, or redesign mail infrastructure.
