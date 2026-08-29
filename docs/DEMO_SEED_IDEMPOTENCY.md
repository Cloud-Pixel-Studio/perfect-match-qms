# Demo Seed Idempotency

The Demo seed reconciles stable fictional customer records instead of creating
date-specific copies on every run.

## Run the focused checks

From the repository root:

```bash
python -m unittest discover -s deployment/demo/tests -p 'test_*.py'
```

The tests exercise the identity rules without connecting to an Odoo database.
They verify that a date change updates an existing training or qualification
record while preserving its identifier, and that organization/company scope
remains part of the identity.

## Runtime behavior

Training identity is scoped by person, course, organization, and company.
Qualification identity is scoped by person, qualification type, organization,
and company. Due and expiration dates are mutable values, not identity keys.

The validator checks the twelve canonical Apex process codes exactly once and
reports duplicate canonical training or qualification records. Existing Demo
duplicates are reported for separate cleanup authorization; this change does
not delete or rewrite Demo business data.

Action Center rows are transient user-scoped work items. Their global table
count is not used as a corruption signal; validation uses the supported
refresh/source behavior instead.

## Scope boundary

This tooling does not add an Odoo model or database constraint. It does not
import, clean, or reseed the canonical Demo as part of development tests.
