# Perfect Match QMS Demo Guide

Open the demo at `https://demo.invperfectmatch.com/web/login?db=pmqms_demo` and
log in as `admin`. The credential file is kept outside Git; retrieve its path
with `./deployment/scripts/odoo-demo.sh credentials` on the demo VM.

The fictional company is `Apex Precision Systems, Inc.`. The intended site concept is Headquarters & Quality Center, Manufacturing Plant, and Inspection & Distribution Center; the current product does not yet have a dedicated Site model.

| Product Area | Menu Path | Demo Record | What To Show |
| --- | --- | --- | --- |
| Dashboard | Perfect Match QMS > Dashboard | Apex metrics | Readiness, actions, customer quality, calibration, and quality cost indicators populated from source records. |
| Guided Implementation | Perfect Match QMS > Implementations | Apex Precision QMS Demo Implementation | Generated areas, controls, activities, evidence requirements, gaps, and readiness. |
| Documents | Perfect Match QMS > Documents | APEX-DOC-003 - SOP - Control of Nonconforming Outputs | Controlled document metadata and revision context using original fictional content. |
| Evidence | Perfect Match QMS > Evidence | APEX-EV-003 - Evidence - SOP - Control of Nonconforming Outputs | Evidence linked to a control instance and requirement. |
| Document Acknowledgments | Perfect Match QMS > People & Competency > Acknowledgments | Maria pending SOP acknowledgment | Revision-specific acknowledgment status and Action Center follow-up. |
| Risk | Perfect Match QMS > Risk & Improvement > Risks | APEX-RISK-001 - Single-source supplier continuity risk | Owner, mitigation plan, target/review dates, and Action Center visibility. |
| NCR | Perfect Match QMS > Risk & Improvement > NCR | APEX-NCR-001 - Incorrect hole diameter on Lot L-24017 | Detection, containment, investigation summary, severity, disposition, and CAPA relationship. |
| CAPA | Perfect Match QMS > Risk & Improvement > CAPA | APEX-CAPA-001 - Repeated inspection escape from outdated setup instruction | Root cause, 5 Why, CAPA actions, target dates, and effectiveness review date. |
| Audit | Perfect Match QMS > Audit | APEX-AUD-001 - Document control and final inspection audit | Program/audit context, scope, criteria, and findings. |
| Performance | Perfect Match QMS > Performance | APEX-KPI-001 - First-pass final inspection yield | Objective, KPI, and monthly measurement trend. |
| People | Perfect Match QMS > People & Competency > People | Olivia Parker / Daniel Brooks / Maria Lewis | Fictional personas, QMS responsibilities, and linked user/person records. |
| Training | Perfect Match QMS > People & Competency > Training | APEX-TRN-001 - Revised setup instruction refresher | Due, overdue, and completed training examples. |
| Qualifications | Perfect Match QMS > People & Competency > Qualifications | APEX-QUAL-001 - Final Inspection Authorization | Expired, expiring, and current qualification examples. |
| Calibration | Perfect Match QMS > Equipment & Calibration > Equipment | EQ-0001 - Digital Caliper | Current, due soon, overdue, and OOT scenario context. |
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
