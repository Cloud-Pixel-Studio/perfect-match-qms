# ADR-025: Customer And Supplier Performance Architecture

Date: 2026-08-15

## Status

Accepted

## Context

Perfect Match needs customer performance, customer satisfaction, supplier
performance, and supplier evaluation data. Odoo already provides partner master
data.

## Decision

Reuse `res.partner` as the customer and supplier master.

Create operational records that reference partners:

- `pm.qms.customer.performance`
- `pm.qms.customer.satisfaction`
- `pm.qms.supplier.performance`
- `pm.qms.supplier.evaluation`

Do not duplicate customer or supplier master databases.

Where structured NCR data exists, customer and supplier performance derives
counts from `pm.qms.nonconformity.source_type`.

## Consequences

Partner identity remains centralized in Odoo. Performance records can later
integrate with Odoo sales, purchase, inventory, and receipt data without a data
master migration.
