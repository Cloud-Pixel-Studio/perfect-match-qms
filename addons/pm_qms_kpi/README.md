# Perfect Match QMS KPI

`pm_qms_kpi` owns the Perfect Match performance-management foundation. The
addon name stays short even though the scope includes objectives, KPI
definitions, KPI measurements, customer performance, customer satisfaction,
supplier performance, and supplier evaluations.

The addon stores client operational data. It does not place actual objectives,
KPI targets, customer results, or supplier scores on reusable Perfect Match
framework controls.

## Architecture

Reusable framework controls remain in `pm.qms.control`. Client implementation
records in `pm.qms.control.instance` may relate to objectives and KPIs:

```text
Control Instance
      |
      +-- Objective
      |      |
      |      +-- KPI
      |             |
      |             +-- Measurements
      |
      +-- Customer Performance
      |
      +-- Supplier Performance
```

Future Management Review will consume these records. Mission 06 does not create
management review snapshots or dashboards.

## Historical Integrity

`pm.qms.kpi` defines what is measured. `pm.qms.kpi.measurement` records actual
performance for a specific period. Measurements preserve target, warning, and
direction snapshots so future KPI target changes do not rewrite historical
evaluation results.

Duplicate measurements are prevented for the same KPI and period.

## Data Sources

KPI measurements support manual, system-calculated, and integration-sourced
results. The addon intentionally does not provide arbitrary SQL, Python formulas,
or executable user expressions.

## Customer And Supplier Masters

Customers and suppliers remain Odoo `res.partner` records. The addon creates
performance and evaluation records that reference partners instead of duplicating
customer or supplier master data.

Customer and supplier nonconformity counts are derived from existing
`pm.qms.nonconformity` records where `source_type` is `customer` or `supplier`.

## Supplier Scoring

Supplier evaluations use transparent configurable weights on each evaluation
record. The default weights are Perfect Match internal defaults and may be
changed per evaluation. Status classifications such as `approved`, `monitor`, or
`disqualified` are internal/customer classifications, not external standard
thresholds.
