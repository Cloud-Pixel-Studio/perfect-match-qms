# Customer and Supplier Quality

Mission 16 adds the Perfect Match customer and supplier quality layer through `pm_qms_customer_quality`.

## Scope

The addon supports:

- Customer complaints with response due dates, containment, customer response tracking, and closure controls.
- Temporary quality alerts connected to complaints, NCRs, supplier issues, or SCARs.
- Root-cause analysis with structured why/cause lines and approval workflow.
- 8D cases with D0-D8 sections, team assignment, root-cause linkage, CAPA linkage, effectiveness review, and closure controls.
- Supplier issues with containment, optional SCAR requirement, NCR linkage, and SCAR linkage.
- SCAR records with supplier response history, revision return, response acceptance, effectiveness review, and closure controls.

## Architecture Rules

NCR and CAPA remain authoritative. Customer complaints, supplier issues, 8D cases, and SCARs do not replace them. The workflow creates NCR/CAPA records only through explicit actions and reuses existing links when a record already exists.

Customers and suppliers are `res.partner` records. Operational references such as product, order, purchase, lot, serial, and shipment references are stored as text so the addon remains independent from sale, purchase, stock, MRP, and Odoo Quality.

## Navigation

After installation, users with QMS access can use:

- Quality Management > Customer Quality > Complaints
- Quality Management > Customer Quality > Quality Alerts
- Quality Management > Customer Quality > Root Cause Analysis
- Quality Management > Customer Quality > 8D Cases
- Quality Management > Supplier Quality > Supplier Issues
- Quality Management > Supplier Quality > SCAR

The main QMS dashboard includes open and overdue customer/supplier quality counters. Management review snapshots include customer quality and supplier quality inputs.

## Pilot Policy

The addon includes fictional demo records for development/demo databases only. Pilot updates must use `--without-demo=all`; the Oliva pilot must not receive fictional customer complaints, supplier issues, SCARs, 8D cases, or quality alerts.
