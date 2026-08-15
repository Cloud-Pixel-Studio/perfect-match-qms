# Architecture

Perfect Match Digital QMS is implemented as a modular Odoo 19 application.
Odoo owns core QMS state, users, access control, workflow data, and business
rules. PostgreSQL persists Odoo data. Docker Compose provides the local DEV
runtime.

## Mission 02 Scope

```text
Odoo
`-- pm_qms_core
    |-- Organizations
    |-- Processes
    |-- Controls
    |-- Activities
    |-- Evidence Requirements
    `-- External Mappings
```

The first addon, `pm_qms_core`, defines the reusable foundation only. It does
not implement standard packs, AI, customer portals, audits, CAPA, risk, NCR,
KPIs, or production hosting.

## Control Model

The central object is the Perfect Match Control:

```text
pm.qms.control
```

A control is a proprietary reusable implementation object. It is not an ISO
clause, not an external requirement, and not copied standard text.

```text
Framework Definition
        |
        v
Perfect Match Controls
        |
        v
Implementation Activities
        |
        v
Evidence Requirements

External Standards
        |
        v
External Mappings
        |
        v
Perfect Match Controls
```

The standard does not define the internal data object. Perfect Match does.

## Core Relationships

- `pm.qms.organization` groups processes by company context.
- `pm.qms.process` represents management-system processes and can have parent and child processes.
- `pm.qms.control` belongs to one process and can be manually coded or sequence-coded.
- `pm.qms.activity` defines reusable implementation activities for one control.
- `pm.qms.evidence.requirement` defines expected evidence for one control.
- `pm.qms.external.mapping` references external frameworks by name, edition, and reference identifier only.

## DEV Runtime

```text
PMQMS DEV

Docker Compose
|-- odoo-dev
`-- postgres-dev
```

The DEV stack uses:

- `deployment/docker/dev/compose.yml`
- network `pmqms_dev_network`
- volume `pmqms_dev_postgres`
- volume `pmqms_dev_odoo_data`
- addon mount `/mnt/extra-addons`

It is isolated from Plane and must not reuse Plane PostgreSQL, Docker networks,
volumes, or secrets.

## Mission 03 Operational Layer

```text
PERFECT MATCH FRAMEWORK

pm.qms.control
        |
        v

CLIENT IMPLEMENTATION

pm.qms.control.instance
        |
        |-- pm.qms.document
        |       `-- pm.qms.document.revision
        |
        `-- pm.qms.evidence
```

`pm.qms.control` defines what Perfect Match expects. It is reusable
methodology.

`pm.qms.control.instance` defines how a specific organization is implementing
that control. Implementation status, applicability, owner, target dates,
document links, and evidence completion belong to the instance.

The framework control lifecycle remains separate from client implementation
readiness. The system uses implementation language such as "Implementation
Status" and "Evidence Completion"; it does not claim certification readiness.

## Documents And Evidence

- `pm.qms.document` is the stable identity of a controlled document.
- `pm.qms.document.revision` is revision history and approval state.
- `pm.qms.evidence.requirement` defines expected evidence in reusable
  methodology.
- `pm.qms.evidence` is an actual client evidence record tied to a control
  instance.

Files are linked through Odoo `ir.attachment`. The QMS models reference
attachments instead of duplicating binary content in custom tables.

## Mission 04 Operational Hardening Layer

```text
PERFECT MATCH FRAMEWORK

pm.qms.control
        |
        v

CLIENT IMPLEMENTATION

pm.qms.control.instance
        |
        |-- Evidence
        |-- Documents
        |       `-- Revisions
        |-- Risks and Opportunities
        |-- Nonconformities
        `-- CAPA
```

Risk, NCR, and CAPA are client operational records. They relate to
`pm.qms.control.instance`, not to reusable framework definitions as mutable
client state. `pm.qms.control` remains reusable Perfect Match methodology.

Mission 04 adds:

- `pm_qms_risk` with `pm.qms.risk` for risks and opportunities.
- `pm_qms_ncr` with `pm.qms.nonconformity` for detected deviations.
- `pm_qms_capa` with `pm.qms.capa`, `pm.qms.capa.action`, and
  `pm.qms.capa.why` for corrective/preventive actions.
- `pm.qms.event` as a lightweight append-only operational event log for
  compliance-sensitive workflow transitions.

Risk scoring uses a simple Perfect Match methodology: likelihood times impact,
with configurable threshold parameters for Low, Moderate, High, and Critical.
The scoring model is not external-standard content.

CAPA effectiveness is intentionally separate from implementation completion.
A CAPA moves through implementation, effectiveness review, effective or
ineffective decision, and only then closure.

## Mission 05 Internal Audit Foundation

```text
Audit Program
        |
        v
Audit
 |-- Scope
 |-- Criteria
 |-- Team and independence review
 |-- Plan Lines
 |-- Audit Evidence
 `-- Findings
        |
        v
      NCR
        |
        v
      CAPA
```

Mission 05 adds `pm_qms_audit` as a client operational addon. It depends on
`pm_qms_capa` so it can reuse the existing NCR and CAPA chain without adding
direct CAPA coupling to every finding.

The audit layer includes:

- `pm.qms.audit.program` for planned audit programs by organization and period.
- `pm.qms.audit` for individual audits with type, dates, team, objective,
  scope summary, independence metadata, conclusion, lifecycle, and summary
  counts.
- `pm.qms.audit.scope` for normalized process, organization, and control
  instance scope.
- `pm.qms.audit.criterion` for criteria using Perfect Match controls, company
  procedures, customer/regulatory references, external standard reference
  metadata, or other internal references.
- `pm.qms.audit.plan.line` for lightweight agenda and interview planning.
- `pm.qms.audit.evidence` for evidence collected during an audit.
- `pm.qms.audit.finding` for conformities, observations, opportunities for
  improvement, and internal nonconformities.

Audit records relate to `pm.qms.control.instance` and `pm.qms.process`, not to
`pm.qms.control` as mutable client state. External standards remain references
only; no external standard requirement text is stored in criteria, demo data,
tests, or documentation.

Audit completion is separate from finding, NCR, and CAPA closure. A valid state
is:

```text
Audit = Completed
Finding = Action Required
NCR = Open
CAPA = In Progress
```

This allows audit reporting to finish while corrective action remains managed
through NCR and CAPA workflows.

## Mission 06 Performance Management Foundation

```text
CLIENT QMS

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

Future:

Performance Data
      |
      v
Management Review
```

Mission 06 adds `pm_qms_kpi` as the reusable performance-management layer for
future Management Review, readiness, dashboards, AI summaries, and automation.
It does not implement Management Review.

The layer includes:

- `pm.qms.objective` for organization-specific measurable objectives.
- `pm.qms.kpi` for KPI definitions.
- `pm.qms.kpi.measurement` for historical KPI results.
- `pm.qms.customer.performance` for customer performance by period.
- `pm.qms.customer.satisfaction` for actual satisfaction measurements.
- `pm.qms.supplier.performance` for supplier quality/delivery performance.
- `pm.qms.supplier.evaluation` for supplier evaluation records with explicit
  weights and internal status classifications.

KPI definitions and KPI measurements are intentionally separate. KPI
measurements preserve target, warning, and direction snapshots so future target
changes do not rewrite historical results.

Customers and suppliers remain Odoo `res.partner` records. Performance records
reference partners and do not create duplicate customer or supplier master data.
Customer and supplier NCR counts are derived from `pm.qms.nonconformity`
records when structured `source_type` data exists.

Performance records relate to `pm.qms.control.instance` and `pm.qms.process`.
They do not attach mutable client objective, target, or result data to reusable
`pm.qms.control` framework definitions.
