# ADR-074: M28 Tenant Isolation and Entitlement Integrity

## Status

Accepted for controlled DEV implementation; Demo, production, and customer
deployment remain separate authorized gates.

## Context

M28 closes two authorization classes that are independent but related at the
tenant boundary:

1. License term state must be evaluated from the current clock on every
   entitlement decision. A stored `valid` value cannot keep an expired or
   not-yet-valid license usable.
2. A user scoped to one organization must not reach a same-company record in a
   sibling organization through child records, autocomplete, grouping, mail,
   activities, or attachments.

The canonical Demo and its business data are outside this decision. Historical
release tags and ISO content are also outside this decision.

## Decision

1. `effective_temporal_state()` is the single temporal calculation used by
   license status, the license view, and entitlement enforcement. Signed
   payload fields remain unchanged; temporal status is recomputed at read and
   enforcement time.
2. The existing locked current-license row remains the serialization point for
   capacity checks. Organization, site, and named-user creation cannot proceed
   for missing, invalid, wrong-environment, not-yet-valid, or expired terms.
3. M28 adds global organization/process scope rules to the explicitly listed
   QMS child models. Parent-derived stored organization fields are used where
   the model already provides them; no new model or scope field is introduced.
4. `mail.message` and `ir.attachment` continue to use Odoo's native related
   document checks. `mail.activity` receives a narrow `pm.qms.*` extension so
   assignment to the current user cannot bypass the related QMS document
   boundary. Activities on non-QMS models retain native behavior.
5. Customer-style instances remain isolated by the existing deployment
   foundation: unique database, filestore volume, bridge network, loopback
   port, environment identity, secret directory, and license directory per
   instance. No customer instance follows a live Git branch or upstream Odoo
   release.

## Evidence boundary

The M28 regression creates fictional same-company organizations and child
records in disposable DEV only. It covers direct search, name search, grouped
read, direct read, write, unlink, in-scope create, out-of-scope create, native
message/attachment/activity access, and exact license term boundaries. The
authorization matrix records the intended model/persona/operation contract.

This evidence is ORM/runtime evidence. It does not claim that arbitrary custom
HTTP controllers are isolated; endpoint validation remains an explicit later
test when such a route exists.

## Consequences

Existing QMS data remains readable when a license expires, but new commercial
capacity cannot be activated. Child records cannot be used as a side channel
around their owning organization. The implementation has a small mail activity
extension because Odoo's normal assigned-user activity exception is too broad
for scoped QMS records.

## Non-goals

M28 does not modify Demo, customer data, ISO content, RC11, Plane, mail
infrastructure, or the customer seed. It does not add portal routes, new QMS
models, or a second licensing architecture.
