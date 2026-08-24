# Perfect Match QMS Demo Guide

Open the demo at `https://demo.invperfectmatch.com/web/login?db=pmqms_demo` and
use a persona credential supplied through the Demo secret mechanism. The
technical administrator credential is kept outside Git; retrieve only its
path with `./deployment/scripts/odoo-demo.sh credentials` on the Demo VM.

The fictional company is `Apex Precision Systems, Inc.`. The demo contains one
organization and exactly three operational Sites: `APEX-HQ` Headquarters &
Quality Center, `APEX-MFG` Manufacturing Plant, and `APEX-INS` Inspection &
Distribution Center.

The Demo also carries a signed offline commercial license. Open **Perfect Match
QMS > Commercial License** as an administrator to see customer, edition,
environment short ID, validity, capacity usage, and revision history. The
canonical Demo license is intentionally sized for the three seeded Sites and
all fictional walkthrough personas. Use **Generate Activation Request** for an
offline renewal request and **Import Updated License** for a signed replacement.

| Product Area | Menu Path | Demo Record | What To Show |
| --- | --- | --- | --- |
| Dashboard | Perfect Match QMS > Dashboard | Apex metrics | Readiness, actions, customer quality, calibration, and quality cost indicators populated from source records. |
| Company Profile | Perfect Match QMS > Configuration > Company Profile | APEX - Apex Precision Systems, Inc. | QMS scope, primary quality contact, technical company context, and linked Sites. |
| Sites | Perfect Match QMS > Configuration > Sites | APEX-HQ / APEX-MFG / APEX-INS | Primary headquarters, manufacturing, inspection/distribution, archive state, and operational relationships. |
| Guided Implementation | Perfect Match QMS > Implementations | Apex Precision QMS Demo Implementation | Generated areas, controls, activities, evidence requirements, gaps, and readiness. |
| Documents | Perfect Match QMS > Documents | APEX-DOC-003 - SOP - Control of Nonconforming Outputs | Controlled document metadata and revision context using original fictional content. |
| Evidence | Perfect Match QMS > Evidence | APEX-EV-003 - Evidence - SOP - Control of Nonconforming Outputs | Evidence linked to a control instance and requirement. |
| Document Acknowledgments | Perfect Match QMS > People & Competency > Acknowledgments | Maria pending SOP acknowledgment | Revision-specific acknowledgment status and Action Center follow-up. |
| Risk | Perfect Match QMS > Risk & Improvement > Risks | APEX-RISK-001 - Single-source supplier continuity risk | Owner, mitigation plan, target/review dates, and Action Center visibility. |
| NCR | Perfect Match QMS > Risk & Improvement > NCR | APEX-NCR-001 - Incorrect hole diameter on Lot L-24017 | Detection, containment, investigation summary, severity, disposition, and CAPA relationship. |
| CAPA | Perfect Match QMS > Risk & Improvement > CAPA | APEX-CAPA-001 - Repeated inspection escape from outdated setup instruction | Root cause, 5 Why, CAPA actions, target dates, and effectiveness review date. |
| Audit | Perfect Match QMS > Audit | APEX-AUD-001 - Document control and final inspection audit | Program/audit context, scope, criteria, and findings. |
| Performance | Perfect Match QMS > Performance | APEX-KPI-001 - First-pass final inspection yield | Objective, KPI, and monthly measurement trend. |
| People | Perfect Match QMS > People & Competency > People | Olivia Parker / Daniel Brooks / Maria Lewis / James Carter / Emma Reed / Michael Stone / Victor Lee | Fictional personas, QMS responsibilities, and linked user/person records. |
| Training | Perfect Match QMS > People & Competency > Training | APEX-TRN-001 - Revised setup instruction refresher | Due, overdue, and completed training examples. |
| Qualifications | Perfect Match QMS > People & Competency > Qualifications | APEX-QUAL-001 - Final Inspection Authorization | Expired, expiring, and current qualification examples. |
| Calibration | Perfect Match QMS > Equipment & Calibration > Equipment | EQ-0001 - Digital Caliper | Current, due soon, overdue, OOT scenario context, and Site assignment. |
| OOT Impact Assessment | Perfect Match QMS > Equipment & Calibration > Impact Assessments | APEX-OOT-001 - Digital caliper impact | Quarantine, exposure window, affected evidence, and NCR/CAPA traceability. |
| Customer Complaints | Perfect Match QMS > Customer Quality > Complaints | APEX-CC-001 - Nova Aero dimensional nonconformance complaint | Response due date, containment, related NCR, and 8D relationship. |
| Quality Alerts | Perfect Match QMS > Customer Quality > Quality Alerts | APEX-QA-001 - Dimensional verification alert for Lot L-24017 | Internal alert tied to the customer/NCR scenario. |
| 8D | Perfect Match QMS > Customer Quality > 8D | APEX-8D-001 - Nova Aero dimensional complaint | End-to-end 8D problem, containment, root cause, and corrective action. |
| Supplier Issues | Perfect Match QMS > Supplier Quality > Supplier Issues | APEX-SI-001 - Orion Metals certificate discrepancy | Supplier containment need and source for SCAR. |
| SCAR | Perfect Match QMS > Supplier Quality > SCAR | APEX-SCAR-001 - Orion Metals certificate discrepancy | Supplier response, root cause, corrective action, and response due date. |
| Action Center | Perfect Match QMS > Dashboard or Action Center | My Actions | Multiple source-driven actions: risk, NCR, CAPA, audit, training, qualification, calibration, complaint, 8D, supplier issue, SCAR, and management review. |
| Cost Events | Perfect Match QMS > Cost of Quality > Cost Events | APEX-CQ-001 - Dimensional complaint quality cost story | Confirmed cost event with prevention, appraisal, internal failure, external failure, and recovery lines. |
| Cost Analytics | Perfect Match QMS > Cost of Quality > Analytics | Apex quality cost analytics | Gross quality cost, COPQ, recoveries, net cost, category breakdown, and source breakdown. |
| Management Review | Perfect Match QMS > Management Review | APEX-MR-001 - Apex QMS Management Review - Demo | Inputs, snapshot behavior where supported, decisions, and review actions. |

## Mission 19 security walkthrough

Use `Configuration > Users & Access` to inspect the fictional Demo personas.
Roles answer what a user may do; the selected organization, Sites, and
Processes answer where the user may do it. Scope is enforced by Odoo ACLs and
record rules, so a bookmarked URL or RPC call cannot bypass the same boundary.

| Persona | Role and scope | Expected walkthrough |
| --- | --- | --- |
| Olivia Parker | Quality Manager, all Apex Sites and Processes | Full QMS navigation, Users & Access, Action Center, and Cost Analytics. |
| Daniel Brooks | Quality Supervisor, `APEX-MFG` | Manufacturing records and actions; `APEX-INS` records are denied. |
| Maria Lewis | Document Controller, organization-wide | Documents, revisions, and acknowledgments; unrelated operational administration is denied. |
| James Carter | Internal Auditor, all Apex Sites and Processes | Audit programs, audits, findings, and evidence with independence controls. |
| Emma Reed | Process Owner, selected Manufacturing and Inspection processes | Assigned process obligations only; unrelated process records are denied. |
| Michael Stone | Management User, organization-wide | Dashboards, KPI, Management Review, and approved read-only Cost Analytics. |

For negative validation, sign in as Daniel or Emma, open an allowed record,
then attempt a known record from an unassigned Site or Process. The expected
result is an Odoo access denial, not merely a hidden menu. The `QMS Viewer`
role is read-only and receives only records allowed by its organization/Site/
Process scope.

Demo passwords are stored outside Git through the VM credential mechanism. Do
not place persona passwords in this guide, Plane, commits, or screenshots.

## Commercial license walkthrough

The expected Demo status is `Valid` or `Expiring`, with one operational company,
three active Sites, and named-user usage at or below the license limit. The
environment identity is provisioned outside PostgreSQL and remains stable when
the Odoo container is recreated. License failure is non-destructive: records,
attachments, exports, and backups remain available.
