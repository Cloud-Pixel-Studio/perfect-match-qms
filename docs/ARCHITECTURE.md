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
