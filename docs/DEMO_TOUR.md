# Perfect Match QMS Demo Tour

This tour uses fictional manufacturing data for Apex Precision Electronics, Inc.
It is intended for sales demonstrations, Quality Managers, implementation
consultants, and product acceptance testers.

## 1. Dashboard

Purpose: see overall QMS health.

Question answered: How is my QMS doing?

Use the stat buttons and the performance, evidence, risk, action, people,
equipment, and customer-quality sections to identify attention areas.

## 2. Action Center

Purpose: see prioritized work in one place.

Question answered: What needs my attention?

Open an action to follow its source record, owner, due date, and current state.

## 3. ISO 9001 Initial Implementation

The implementation project organizes the work into phases, controls, and
guided activities. It answers: What are we implementing?

## 4. Guided Activity

Use the Objective, Why It Matters, Implementation Steps, Expected Output,
Evidence Expectations, and Success Criteria sections to complete work in a
consistent way.

## 5. Implementation Control

An implementation control brings together operational guidance, readiness
state, evidence status, blockers, next action, and Done When criteria.

## 6. Evidence

Evidence records describe what supports a control and how it is accepted.
Submission, review, rejection, expiration, and acceptance are distinct states.
Uploaded does not mean accepted.

## 7. Readiness Center

Use Ready, Partial, Gap, and N/A states with the recommended next action to
understand implementation progress and focus effort.

## 8. Readiness Assessment

An assessment records an immutable historical snapshot of implementation,
evidence, activity, and control readiness at a point in time.

## 9. NCR, RCA, and Corrective Action

Nonconformities, root-cause analysis, and corrective actions represent
different parts of the improvement workflow and can be followed through their
related records.

## 10. Internal Audit

Use audit plans, criteria, evidence, findings, and follow-up actions to review
objective evidence against defined criteria.

## 11. KPI and Performance

Objectives describe desired results. KPIs measure performance toward those
results. Review the owner, process, target, current result, frequency, trend,
and related action.

## 12. Equipment and Calibration

Monitoring resources show identity, organization, site, responsible person,
lifecycle state, calibration requirement, due information, events, and related
records where available.

## 13. Management Review

Management Review brings together QMS performance, customer and supplier
information, audit results, risks, resources, changes, and improvement signals
for leadership decisions and actionable follow-up.

## 14. Configuration

Configuration provides customer-facing access to the company profile, sites,
processes, Users & Access, and Commercial License. Use the scope summary to
understand organizations, sites, processes, role, and effective access.

## Guided Apex electronics walkthrough

Use this order to tell one connected story instead of opening unrelated sample
records. Every name, lot, measurement, supplier, and result is fictional.

1. **Set the operating context.** In Company Profile and Sites, introduce Apex,
   the manufacturing plant (`APEX-HQ`), electrical test laboratory
   (`APEX-MFG`), and receiving warehouse (`APEX-INS`). In Processes, show the
   chain from approved supplier and receiving through ESD, SMT, assembly,
   electrical test, calibration, nonconforming product, CAPA, traceability,
   and dispatch.
2. **Show controlled work.** Open the Quality Manual, then the ESD, receiving,
   SMT, electrical-test, calibration, traceability, NCR/CAPA, and audit
   documents. Each revision demonstrates purpose, owner, effective/review
   dates, change summary, acceptance evidence, approval state, and a linked
   synthetic evidence reference. No real photograph, customer record, or
   external standard text is used.
3. **Follow a production escape.** Start from `APEX-NCR-001`: detected date,
   process, severity, lot, test evidence, containment owner/action/date,
   disposition, and target date. Follow its linked `APEX-CAPA-001` to the five
   why answers, action owners/due dates, and controlled-document response.
   Compare with `APEX-NCR-002` / `APEX-CAPA-002`, where fishbone hypotheses,
   Is/Is Not dimensions, evidence basis, confirmed cause rationale, and an
   in-progress action make the investigation state explicit.
4. **Show closure and prevention.** `APEX-CAPA-003` links an ESD risk to an
   owned corrective action, completion/verification evidence, effectiveness
   note, and closed workflow. The screen sequence makes clear which fields are
   analysis, action ownership, implementation evidence, and effectiveness
   review—not a single free-text status change.
5. **Explain measurement confidence.** In Equipment & Calibration, compare
   current, due-soon, overdue, quarantined, and out-for-calibration examples.
   Open the failed analyzer event to see provider, measurement lines, result,
   affected lot, impact assessment, and containment/NCR connection. Accepted
   calibration and equipment states are produced through the documented
   workflow.
6. **Trace external quality.** Follow the fictional Nova Aero complaint to
   its containment, NCR, alert, 8D, response due date, cost event, and customer
   scorecard. Then compare Orion Metals and Beacon Components: receiving issue,
   supplier corrective request, supplier response/status, evaluation criteria,
   and 90-day delivery/quality scorecard.
7. **Review people and competence.** Open the course and training event, then
   compare each persona's completion result, due date, qualification type,
   issue/expiry dates, assessment, and required-document acknowledgment. A gap
   or due item is a follow-up signal, not evidence that a real person was
   trained.
8. **Connect outcomes to leadership.** Performance shows eight objectives/KPIs
   with four synthetic time-series points each. Action Center rows link back
   to source records across documents, risks, CAPA, audits, training,
   qualifications, equipment, customer/supplier quality, and Management Review.
   The review snapshot has eight categorized inputs, a decision, and an owned
   action with a due date. Cost of Quality retains exactly six canonical lines:
   four on `APEX-CQ-001` and two on `APEX-CQ-002`, with both events confirmed.

At each stop, explain the record's source, owner, process/site, state, due date,
evidence, and linked follow-up. The full menu/submenu, model, access scope,
example, state, relationship, and validator mapping is in the
[`Demo2 coverage matrix`](../deployment/demo/DEMO_COVERAGE_MATRIX.md).

## Key Product Philosophy

For a menu-by-menu guide with records, states, relationships, role scopes, and
validation evidence, see
[`deployment/demo/DEMO_COVERAGE_MATRIX.md`](../deployment/demo/DEMO_COVERAGE_MATRIX.md).

Perfect Match QMS helps an organization implement, operate, demonstrate,
assess readiness, identify gaps, prioritize next actions, and improve.

This demonstration does not promise compliance or certification and is not a
substitute for professional assessment.
