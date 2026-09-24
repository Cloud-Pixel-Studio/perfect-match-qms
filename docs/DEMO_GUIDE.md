# Perfect Match QMS Demo Guide

Open the demo at `https://demo.invperfectmatch.com/web/login?db=pmqms_demo` and
use a persona credential supplied through the Demo secret mechanism. The
technical administrator credential is kept outside Git; retrieve only its
path with `./deployment/scripts/odoo-demo.sh credentials` on the Demo VM.

The guided Demo2 company is `Apex Precision Electronics, Inc.`. It contains one
organization and exactly three operational sites: `APEX-HQ` Manufacturing
Plant, `APEX-MFG` Electrical Test Laboratory, and `APEX-INS` Warehouse &
Receiving. The complete menu-by-menu fixture contract is in
[`DEMO_COVERAGE_MATRIX.md`](../deployment/demo/DEMO_COVERAGE_MATRIX.md).

The Demo also carries a signed offline commercial license. Open **Perfect Match
QMS > Configuration > Commercial License** as an administrator to see customer, edition,
environment short ID, validity, capacity usage, and revision history. The
canonical Demo license is intentionally sized for the three seeded Sites and
all fictional walkthrough personas. Use **Generate Activation Request** for an
offline renewal request and **Import Updated License** for a signed replacement.

The Demo installs the ISO 9001 standard add-on. Open **Perfect Match QMS >
Standards > ISO 9001 > Overview** to see the active ISO 9001 / 2015 profile and
its current zero-approved-mapping state. The Demo does not implement or display
any other management-system standard.

| Product Area | Menu Path | Demo Record | What To Show |
| --- | --- | --- | --- |
| Dashboard | Perfect Match QMS > Dashboard | Apex metrics | Readiness, actions, customer quality, calibration, and quality cost indicators populated from source records. |
| Company Profile | Perfect Match QMS > Configuration > Company Profile | APEX - Apex Precision Electronics, Inc. | QMS scope, primary quality contact, technical company context, and linked sites. |
| Sites | Perfect Match QMS > Configuration > Sites | APEX-HQ / APEX-MFG / APEX-INS | Manufacturing plant, electrical test laboratory, warehouse/receiving, and assigned processes. |
| Guided Implementation | Perfect Match QMS > Implementation | Apex Precision Electronics QMS Guided Implementation | Quality Pack controls, synchronized activities, evidence requirements, gaps, and a readiness snapshot. |
| Documents | Perfect Match QMS > Assurance > Documents | APEX-DOC-001 through APEX-DOC-013 | Quality manual, ESD, receiving, SMT, electrical test, calibration, traceability, NCR/CAPA and audit instructions with controlled revisions. |
| Evidence | Perfect Match QMS > Implementation > Evidence | synthetic inspection, test and certificate references | Evidence linked to documents, audit criteria, controls and related quality records. |
| Document Acknowledgments | Perfect Match QMS > Assurance > People & Competency > Acknowledgments | Maria pending SOP acknowledgment | Revision-specific acknowledgment status and Action Center follow-up. |
| Risk | Perfect Match QMS > Quality Operations > Risk & Improvement > Risks | APEX-RISK-001 through APEX-RISK-008 | Supplier continuity, ESD, counterfeit, solder, calibration, traceability and test escape risks with owners and mitigation. |
| NCR | Perfect Match QMS > Quality Operations > Risk & Improvement > NCR | APEX-NCR-001 / APEX-NCR-002 | Electrical-test escape and SMT solder-wetting nonconformities with containment and source links. |
| CAPA | Perfect Match QMS > Quality Operations > Risk & Improvement > CAPA | APEX-CAPA-001 through APEX-CAPA-003 | Draft, implementation and closed workflows with 5 Why/Fishbone, actions, effectiveness and linked sources. |
| Audit | Perfect Match QMS > Audit | APEX-AUD-001 - Document control and final inspection audit | Program/audit context, scope, criteria, and findings. |
| Performance | Perfect Match QMS > Performance | APEX-KPI-001 - First-pass final inspection yield | Objective, KPI, and monthly measurement trend. |
| People | Perfect Match QMS > Assurance > People & Competency > People | Olivia Parker / Daniel Brooks / Maria Lewis / James Carter / Emma Reed / Michael Stone / Victor Lee | Fictional personas, QMS responsibilities, and linked user/person records. |
| Training | Perfect Match QMS > Assurance > People & Competency > Training | APEX-TRN-001 - Revised setup instruction refresher | Due, overdue, and completed training examples. |
| Qualifications | Perfect Match QMS > Assurance > People & Competency > Qualifications | APEX-QUAL-001 - Final Inspection Authorization | Expired, expiring, and current qualification examples. |
| Calibration | Perfect Match QMS > Equipment & Calibration > Equipment | EQ-0001 through EQ-0004 | Current, due-soon, overdue, quarantined and out-for-calibration states by site. |
| OOT Impact Assessment | Perfect Match QMS > Equipment & Calibration > Impact Assessments | APEX-OOT-001 - electrical safety analyzer impact | Quarantine, affected test lot, measurement lines, and NCR/CAPA traceability. |
| Customer Complaints | Perfect Match QMS > Customer Quality > Complaints | APEX-CC-001 - Nova Aero electrical-performance complaint | Response due date, containment, related NCR, alert, costs and 8D. |
| Quality Alerts | Perfect Match QMS > Customer Quality > Quality Alerts | APEX-QA-001 - electrical retest alert | Preserve test logs and verify current test configuration. |
| 8D | Perfect Match QMS > Customer Quality > 8D | APEX-8D-001 - Nova Aero electrical complaint | End-to-end 8D problem, containment, root cause, and corrective action. |
| Supplier Issues | Perfect Match QMS > Supplier Quality > Supplier Issues | APEX-SI-001 - Orion Metals certificate discrepancy | Supplier containment need and source for SCAR. |
| SCAR | Perfect Match QMS > Supplier Quality > SCAR | APEX-SCAR-001 - Orion Metals certificate discrepancy | Supplier response, root cause, corrective action, and response due date. |
| Action Center | Perfect Match QMS > Dashboard or Action Center | My Actions | Multiple source-driven actions: risk, NCR, CAPA, audit, training, qualification, calibration, complaint, 8D, supplier issue, SCAR, and management review. |
| Cost Events | Perfect Match QMS > Performance > Cost of Quality > Cost Events | APEX-CQ-001 / APEX-CQ-002 | Confirmed canonical cost events, exactly 4 and 2 lines respectively. |
| Cost Analytics | Perfect Match QMS > Performance > Cost of Quality > Analytics | Apex quality cost analytics | Gross quality cost, COPQ, recoveries, net cost, category breakdown, and source breakdown. |
| Management Review | Perfect Match QMS > Performance > Management Review | APEX-MR-001 - Apex QMS Management Review - Demo | Inputs, snapshot behavior where supported, decisions, and review actions. |

## Mission 19 security walkthrough

Use `Configuration > Users & Access` to inspect the fictional Demo personas.
Roles answer what a user may do; the selected organization, Sites, and
Processes answer where the user may do it. Scope is enforced by Odoo ACLs and
record rules, so a bookmarked URL or RPC call cannot bypass the same boundary.

| Persona | Role and scope | Expected walkthrough |
| --- | --- | --- |
| Olivia Parker | Quality Manager, all Apex Sites and Processes | Full QMS navigation, Users & Access, Action Center, and Cost Analytics. |
| Daniel Brooks | Quality Supervisor, `APEX-HQ` | Manufacturing plant records and actions; `APEX-MFG` laboratory and `APEX-INS` warehouse records are denied. |
| Maria Lewis | Document Controller, organization-wide | Documents, revisions, and acknowledgments; unrelated operational administration is denied. |
| James Carter | Internal Auditor, all Apex Sites and Processes | Audit programs, audits, findings, and evidence with independence controls. |
| Emma Reed | Process Owner, selected plant and electrical-laboratory processes (`APEX-HQ` / `APEX-MFG`) | Assigned process obligations only; unrelated process records are denied. |
| Michael Stone | Management User, organization-wide | Dashboards, KPI, Management Review, and approved read-only Cost Analytics. |

For negative validation, sign in as Daniel or Emma, open an allowed record,
then attempt a known record from an unassigned Site or Process. The expected
result is an Odoo access denial, not merely a hidden menu. The `QMS Viewer`
role is read-only and receives only records allowed by its organization/Site/
Process scope.

Demo passwords are stored outside Git through the VM credential mechanism. Do
not place persona passwords in this guide, project-management systems, commits,
or screenshots.

## Commercial license walkthrough

The expected Demo status is `Valid` or `Expiring`, with one operational company,
three active Sites, and named-user usage at or below the license limit. The
environment identity is provisioned outside PostgreSQL and remains stable when
the Odoo container is recreated. License failure is non-destructive: records,
attachments, exports, and backups remain available.
