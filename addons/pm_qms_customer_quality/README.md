# Perfect Match QMS Customer Quality

Customer and supplier quality orchestration for Perfect Match QMS.

This addon adds customer complaints, quality alerts, structured root-cause
analysis, 8D cases, supplier issues, and SCAR workflow. It intentionally does not
replace the existing NCR or CAPA engines. Complaints, 8D cases, supplier issues,
and SCAR records provide operational context and controlled workflow around the
authoritative QMS records.

Design constraints:

- Customers and suppliers are `res.partner` records.
- References to orders, parts, lots, shipments, invoices, work orders, and other
  business objects are future-compatible text references.
- No dependency on Sales, Purchase, Stock, MRP, Odoo Quality, portals, or email
  marketing features.
