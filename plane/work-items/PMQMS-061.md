# PMQMS-061 - Full Product Demo Environment

Priority: HIGH
Project: PMQMS PLATFORM
Module: Reporting
Cycle: Backlog
Labels: odoo, demo, deployment, testing, documentation, architecture
Dependencies: PMQMS-060

## Objective

Create a dedicated disposable full-product Perfect Match QMS demo environment separate from the Oliva Torras pilot.

## Description

Add demo-only deployment support, safe reset, idempotent fictional Apex Precision Systems seed data, validation scripts, demo documentation, and a dedicated architecture decision. The demo must populate the current product surface without inserting demo data into Oliva or fabricating Action Center rows directly.

## Acceptance Criteria

- Demo stack uses database `pmqms_demo`, containers `pmqms-odoo-demo` and `pmqms-postgres-demo`, port `8170`, and separate volumes, secrets, filestore, and backup path.
- Reset refuses non-demo databases and deletes only demo volumes.
- Demo seed creates fictional Apex records through Odoo ORM and is idempotent.
- Demo covers implementation, documents, evidence, risk, NCR, CAPA, audit, performance, people, training, qualifications, calibration, customer quality, supplier quality, Action Center, Cost of Quality, management review, and dashboard data.
- Action Center rows are generated from authoritative source records only.
- Cost of Quality contains confirmed events covering prevention, appraisal, internal failure, external failure, and recoveries.
- Oliva pilot remains unmodified by demo creation and contains no Apex demo contamination.
- Demo guide, coverage matrix, environment runbook, and ADR are complete.
- Automated validation, full QMS regression, HTTP health checks, secret scan, content safety, and CI pass before DONE.
