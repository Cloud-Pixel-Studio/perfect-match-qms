# Equipment, Monitoring Resources and Calibration

Mission 15 adds `pm_qms_calibration`, the native Perfect Match QMS capability
for monitoring and measuring resources, calibration, verification,
out-of-tolerance control, and impact assessment.

## Architecture

The module is QMS-native and intentionally independent from Odoo Maintenance,
MRP, Inventory, Odoo Quality, or a laboratory information system.

Core records:

- `pm.qms.equipment` stores the controlled equipment or monitoring resource.
- `pm.qms.equipment.type` stores configurable equipment categories.
- `pm.qms.calibration.provider` stores external calibration providers.
- `pm.qms.calibration.event` stores calibration or verification history.
- `pm.qms.calibration.measurement.line` stores optional measurement points.
- `pm.qms.calibration.impact.assessment` stores out-of-tolerance evaluation.
- `pm.qms.calibration.affected.reference` stores future-compatible affected
  record references.

The equipment record owns master data and schedule state. Calibration events
own historical results. Impact assessments own retrospective evaluation and
disposition. NCR, CAPA, Evidence, Dashboard, and Management Review records link
to these objects without taking ownership of calibration state.

## Equipment Master

Every equipment record has a customer-facing equipment or gage ID that is
unique within the QMS organization. The same ID may exist in another
organization only when company and record-rule boundaries permit it.

The equipment master supports:

- name and equipment/gage ID
- configurable type/category
- manufacturer, model, serial number
- organization, company, process, location
- responsible QMS person
- monitoring or measuring purpose
- calibration and verification requirements
- calibration method, internal or external strategy, and default provider
- interval and interval unit
- due-soon threshold
- lifecycle status
- calculated schedule status
- acceptance criteria and notes
- related documents, evidence, calibration events, and impact assessments

Lifecycle status is separate from schedule condition. For example, an item can
be `in_service` while its calculated schedule status is `due_soon`.

## Scheduling

Next due dates are deterministic:

1. The latest accepted pass or conditional calibration event is selected.
2. If the accepted event has an explicit `next_due_date`, that date is used.
3. Otherwise the equipment interval is applied to the accepted event date.
4. If no accepted event exists, the equipment is marked as having no history.

Interval units support days, months, and years. Due-soon evaluation uses the
equipment's configured threshold. The default is conservative, but customers can
set equipment-specific windows when the risk of late calibration warrants it.

Reminder creation uses Odoo activities and is idempotent. Running the scheduler
again does not create duplicate "Calibration due" activities for the same
equipment and responsible person.

## Calibration Events

Calibration and verification events preserve history. Accepted events are
protected from ordinary edits so certificate, result, and review history do not
drift after approval.

Events support:

- event number
- calibration or verification type
- sent, start, calibration, and completion dates
- internal technician or external provider
- method/procedure
- certificate number and attachment
- related evidence
- pass, conditional, fail, or out-of-tolerance result
- as-found and as-left condition
- optional measurement lines
- reviewer, review date, and notes

A passed or conditionally accepted event may return equipment to service and
updates the next due date. Conditional use requires explicit event review and
does not imply a broad metrology approval process.

## Out Of Tolerance

A failed or out-of-tolerance event does not behave like a simple failed task.
On acceptance it:

- keeps the exact event history
- quarantines the equipment
- prevents silent return to normal service
- creates or reuses a linked impact assessment

Repeated processing is idempotent and does not duplicate impact assessments.

## Impact Assessment

The impact assessment records the retrospective evaluation window:

```text
last known acceptable calibration -> failed/OOT calibration
```

The system derives the last known acceptable event when one exists. If history
is incomplete, the assessment remains explicit about the uncertainty instead of
fabricating dates.

Assessment fields include:

- assessment number
- exact equipment and calibration event
- assessor and assessment date
- last acceptable event/date
- exposure start and exposure end
- whether the equipment was used during the exposure period
- impact conclusion: no, potential, confirmed, or unknown
- records reviewed
- affected references
- containment, evaluation, disposition
- NCR required and linked NCR
- CAPA required and linked CAPA
- approval, closure date, and notes

Closure requires a known conclusion and disposition. If NCR or CAPA is marked
required, the corresponding linked record must exist before closure.

## Affected Records

Mission 15 does not introduce MRP, Inventory, Sales, or Quality dependencies.
Affected records are stored as references with a model name, record ID, display
name, external reference, description, and disposition. This gives the product a
safe bridge point for future integrations without forcing those applications on
customers that do not use them.

## NCR, CAPA and Evidence

Impact assessments can create an NCR when product or process impact requires
formal nonconformance control. The NCR links back to:

- equipment
- calibration event
- impact assessment
- supporting certificate/evidence where available

CAPA can be created or linked from the NCR when corrective action is justified.
CAPA is not automatically created for every calibration failure.

Evidence can reference calibration events, and calibration records can reference
supporting evidence or certificate attachments. The module does not duplicate
document binaries; it reuses Odoo attachments and the existing Perfect Match
Evidence layer.

## People, Audit and Management Review

Internal technicians and responsible owners can link to `pm.qms.person`.
Assigning a technician does not assert competence; competency remains governed
by the People, Training and Competency module.

Auditors can review equipment, events, certificates, impact assessments, NCR,
CAPA, and evidence through QMS-scoped records.

New Management Reviews can include calibration resource-status inputs. Existing
completed review snapshots are not rewritten.

Readiness scoring remains unchanged. Calibration records may provide evidence
or management-review context, but they do not directly modify readiness.

## Dashboard

The Perfect Match QMS dashboard includes calibration attention metrics:

- due-soon equipment
- overdue equipment
- quarantined equipment
- open calibration impact assessments

Counts use scoped Odoo ORM queries and respect company/organization security.

## Security

The module reuses existing groups:

- QMS User: read authorized equipment and calibration records.
- QMS Manager: manage equipment, events, assessments, NCR/CAPA links, and
  operational workflow.
- QMS Administrator: configure equipment types and providers with full
  administrative access.

Company record rules apply to the new models. Organization constraints prevent
cross-organization relationship mistakes inside a company.

## Demo Data

Demo data is fictional and loaded only when Odoo demo data is enabled. The
Historical production-style validation installed the module without demo data,
so no fictional calibration records were seeded into the retired pilot. Current
validation uses DEV and the fictional Demo only.
