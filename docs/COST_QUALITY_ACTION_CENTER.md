# Cost of Quality and Unified Action Center

Mission 17 adds two product layers to Perfect Match QMS:

- Unified Action Center: answers what needs attention without becoming a new workflow engine.
- Cost of Quality: answers what quality is costing without creating accounting, invoice, payroll, sales, purchase, inventory, manufacturing, or Odoo Quality dependencies.

## Modules

- `pm_qms_action_center` provides the action aggregation service, transient presentation records, views, filters, source navigation, dashboard metrics, and demo data for development only.
- `pm_qms_cost_quality` provides cost types, cost events, cost lines, analytics views, dashboard metrics, management review snapshots, and demo data for development only.

Both modules sit above the RC4 QMS capabilities. Existing source modules remain authoritative.

## Unified Action Center Architecture

The Action Center uses `pm.qms.action.center.line`, a transient model rebuilt for the current user. It is a presentation layer, not a durable action store. Refreshing the Action Center deletes only the current user's transient projection and recreates it from readable source records. The stable normalized identity is:

```text
source_model + source_id + action_kind
```

This identity allows one source record to produce multiple obligations when they represent different work, such as a CAPA implementation deadline and a CAPA effectiveness review.

Provider queries run as the current user. The providers do not use `sudo()` to collect source records. The only `sudo()` in the Action Center is for reading the configurable due-soon threshold from `ir.config_parameter`; it does not expose source records.

Opening a source record is allowlisted server-side. The client cannot send arbitrary model/res_id pairs and use the Action Center as a generic opener. Before opening a record, the server verifies the provider tuple, the installed model, record existence, and read access.

## Source Matrix

| Source | Action kind | Owner mapping | Due mapping | Status mapping | Open criteria | Close criteria |
| --- | --- | --- | --- | --- | --- | --- |
| `pm.qms.nonconformity` | `ncr_closure` | `owner_id` | `target_date` | `state` | state not closed/cancelled | NCR closed or cancelled |
| `pm.qms.risk` | `risk_response` | `owner_id` | `target_date` | `state` | state not closed | risk closed |
| `pm.qms.audit.finding` | `finding_follow_up` | `owner_id` | `due_date` | `state` | state not closed/cancelled | finding closed or cancelled |
| `pm.qms.capa` | `capa_due` | `action_owner_id` | `target_date` | `state` | state not effective/closed/cancelled | CAPA effective, closed, or cancelled |
| `pm.qms.capa` | `effectiveness_review` | `owner_id` | `effectiveness_review_date` | `state` | effectiveness required and state not effective/closed/cancelled | CAPA effective, closed, or cancelled |
| `pm.qms.capa.action` | `capa_action` | `owner_id` | `target_date` | `status` | status not completed/verified/cancelled | action completed, verified, or cancelled |
| `pm.qms.management.review.action` | `management_review_action` | `owner_id` | `target_date` | `status` | status not completed/verified/cancelled | action completed, verified, or cancelled |
| `pm.qms.training.record` | `training_completion` | `person_id.user_id` | `due_date` | `state` | state planned or overdue | training completed or otherwise closed by source workflow |
| `pm.qms.qualification.record` | `qualification_expiration` | `person_id.user_id` | `expiration_date` | `status` | status expiring or expired | qualification no longer expiring/expired |
| `pm.qms.document.acknowledgment` | `document_acknowledgment` | `person_id.user_id` | `due_date` | `state` | state pending | acknowledgment completed |
| `pm.qms.equipment` | `calibration_due` | `responsible_person_id.user_id` | `next_due_date` | `calibration_status` | calibration required, not retired, status due/due soon/overdue | calibration no longer due/due soon/overdue or equipment retired |
| `pm.qms.calibration.impact.assessment` | `oot_impact_assessment` | `assessor_person_id.user_id` | none | `state` | state not closed/cancelled | assessment closed or cancelled |
| `pm.qms.customer.complaint` | `customer_response` | `response_owner_id` | `response_due_date` | `state` | state not closed/cancelled | complaint closed or cancelled |
| `pm.qms.customer.complaint` | `containment` | `containment_owner_id` | `containment_due_date` | `state` | containment required, not complete/not required, state not closed/cancelled | containment complete/not required or complaint closed/cancelled |
| `pm.qms.quality.alert` | `quality_alert_review` | `owner_id` | `review_date` | `state` | state draft or published | source no longer draft/published |
| `pm.qms.eight.d` | `eight_d_due` | `owner_id` | `due_date` | `state` | state not closed/cancelled | 8D closed or cancelled |
| `pm.qms.supplier.issue` | `supplier_issue` | `owner_id` | `containment_due_date` | `state` | state not closed/cancelled | issue closed or cancelled |
| `pm.qms.scar` | `scar_response` | `owner_id` | `response_due_date` | `state` | state not closed/cancelled | SCAR closed or cancelled |

## Due Buckets and Priority

Due buckets are normalized as Overdue, Due Today, Due Soon, and Open / No Due Date. The due-soon threshold defaults to seven days and is read from `pm_qms.action_center.due_soon_days`.

Priority normalization maps urgent/critical to Urgent, high/major to High, low/minor to Low, and overdue records to High when no explicit priority exists.

## Person to User Resolution

Some QMS obligations are assigned to `pm.qms.person` instead of directly to `res.users`. When a provider has a person field and the person has `user_id`, the Action Center shows that user as the owner. If no mapped user exists, the line remains unassigned but visible to users who can read the source record.

## Action Center UX

The UI provides My Actions, overdue, due-today, due-soon, category, owner, organization, and source filters. The dashboard adds action counts and a direct Action Center link. Opening a line navigates to the original source form, preserving the source as the editable system of record.

## Cost of Quality Methodology

Cost of Quality uses four categories:

- Prevention
- Appraisal
- Internal Failure
- External Failure

COPQ is defined only as Internal Failure plus External Failure. Prevention and Appraisal are quality costs, but not Cost of Poor Quality.

## Cost Architecture

`pm.qms.cost.type` defines reusable cost classifications per company. `pm.qms.cost.event` captures a dated quality cost event for an organization, optional process, optional allowlisted QMS source, and one or more cost lines. `pm.qms.cost.line` stores the category through its cost type, the cost amount, recovery amount, net amount, estimated flag, and notes.

The Cost of Quality addon is not an accounting system. It does not post journal entries, create invoices, calculate payroll, or infer revenue. Costs are entered explicitly by users.

## Formulas

```text
Prevention Total = sum(line.amount where category = prevention)
Appraisal Total = sum(line.amount where category = appraisal)
Internal Failure Total = sum(line.amount where category = internal_failure)
External Failure Total = sum(line.amount where category = external_failure)
Gross Quality Cost = Prevention + Appraisal + Internal Failure + External Failure
COPQ = Internal Failure + External Failure
Recoveries = sum(line.recovery_amount)
Net Quality Cost = Gross Quality Cost - Recoveries
```

Recovery amounts must be zero or positive. Negative recovery hacks are rejected.

## Lifecycle and Immutability

Cost events start in Draft. QMS Managers can confirm or cancel them. Confirmed events become protected against silent edits to organization, process, date, source, and lines. Corrections are handled by creating a new Draft correction event linked to the confirmed event.

Draft and cancelled events are excluded from official analytics and management review snapshots.

## Source Traceability

Cost events may link only to an allowlisted QMS source model: NCR, CAPA, CAPA Action, Audit Finding, Calibration Impact Assessment, Customer Complaint, 8D, Supplier Issue, or SCAR. Company and organization alignment are enforced. Source identifier and title snapshots are preserved so historical cost context remains readable even if the source name changes later.

Multiple cost events may link to the same source when separate quality costs are identified. No costs are automatically fabricated from source records.

## Analytics and Dashboard

Cost Events provide list, form, pivot, and graph views. The official Cost Analytics action filters to confirmed events. Dashboard metrics include confirmed event count, total quality cost, COPQ, and recoveries for the selected organization.

The existing KPI engine remains authoritative. Mission 17 does not replace KPI measurement or target logic.

## Management Review Integration

Management Review snapshots include Cost of Quality summary inputs and per-event inputs for confirmed events in the review period and organization. Historical reviews remain unchanged because snapshots are created at review generation time.

## Demo and Pilot Policy

Development demo XML may create illustrative cost data. Pilot updates use `--without-demo=all`; therefore Mission 17 must not seed fictional Cost Events into pilot. A newly upgraded pilot is expected to have zero Cost Events unless legitimate pilot users create them. The Action Center may show real existing pilot obligations because it is a live aggregate view.
