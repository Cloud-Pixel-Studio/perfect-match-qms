# ADR-040: External Mapping Approval And Import Strategy

Date: 2026-08-15

## Status

Accepted

## Context

External reference mappings need to be loaded efficiently, but importing a
spreadsheet should not bypass review controls or allow accidental text copying.

## Decision

Add a mapping profile model and a CSV import wizard. The wizard accepts only
metadata columns, validates every row before creating records, requires
reviewer and review date metadata for approved rows, rejects duplicate rows,
and rejects mappings outside the selected pack.

Approved mappings are locked against direct definition edits and deletion.
Only QMS Administrators can create or approve profile-bound mappings.

## Consequences

Mapping coverage is explicit, reviewable, and incomplete until a human-approved
metadata file is supplied. Import remains transactional from the user's point
of view: invalid files create no partial mapping set.
