# Perfect Match QMS Product Visual Surface

Mission 13 turns the existing Perfect Match QMS backend into a customer-facing product surface. The rule is simple: if a capability exists in the product backend, it must be reachable from the Perfect Match QMS application unless security or administration boundaries require contextual access.

## Visual Architecture

Perfect Match QMS remains an Odoo-native application shell. The product uses Odoo forms, lists, kanban views, stat buttons, search views, filters, grouped lists, notebooks, statusbars, and list decorations before custom frontend code.

The visual surface is organized around these product routes:

- Dashboard
- Implementations
- Controls
- Activities
- Evidence
- Readiness
- Documents
- Risk & Improvement
- Audit
- Performance
- Management Review
- Framework
- Configuration

Odoo remains visible as the platform only where it is useful. Customer-facing labels use Perfect Match language such as Implementation, Activity, Evidence, Readiness, Gap, Framework, Quality Objective, KPI, and Management Review.

## UX Principles

- The Perfect Match QMS app shell is the primary entry point.
- Dashboard metrics use real product data only.
- Readiness remains calculated by the existing readiness engine.
- Activities remain `project.task` records filtered into the Perfect Match QMS context.
- Framework methodology remains manager/admin-facing.
- External mappings remain metadata only and do not contain external standard requirement text.
- Empty states explain the purpose of the screen and the next useful action.
- Lists use Odoo-native visual semantics: success for ready/accepted/closed, warning for partial/in progress/review, danger for gaps/overdue/rejected, muted for cancelled/obsolete/not applicable.

## Capability-To-UI Matrix

| Capability | Model | Menu/Route | List/Kanban | Form | Search/Filters | Dashboard/Stat | Notes |
|---|---|---:|---:|---:|---:|---:|---|
| Executive Dashboard | `pm.qms.dashboard` | Yes | N/A | Yes | N/A | Yes | Transient dashboard with real counts and quick routes. |
| Organizations | `pm.qms.organization` | Yes | Yes | Yes | Yes | Contextual | Configuration route, manager-facing. |
| Processes | `pm.qms.process` | Yes | Yes | Yes | Yes | Contextual | Configuration/framework support. |
| Framework Packs | `pm.qms.framework.pack` | Yes | Yes | Yes | Yes | Yes | Manager/admin framework route. |
| Framework Controls | `pm.qms.control` | Yes | Yes | Yes | Yes | Contextual | Proprietary guidance only. |
| External Mapping Metadata | `pm.qms.external.mapping` | Yes | Yes | Yes | Yes | No | Metadata only. No external standard text. |
| Implementation Projects | `pm.qms.implementation.project` | Yes | Yes | Yes | Yes | Yes | Stat buttons for controls, activities, evidence, gaps, readiness. |
| Implementation Areas | `pm.qms.framework.area` via readiness lines | Contextual | Yes | Contextual | Contextual | Yes | Areas are pack areas surfaced through readiness center and implementation tabs. |
| Implementation Controls | `pm.qms.implementation.control` | Yes | Yes | Yes | Yes | Yes | Guided control UX with evidence/activity actions. |
| Activities | `project.task` | Yes | Kanban/List | Yes | Yes | Yes | QMS-filtered project tasks. No duplicate task model. |
| Evidence Requirements | `pm.qms.evidence.requirement` | Yes | Yes | Yes | Yes | Contextual | Framework/admin evidence definitions. |
| Evidence Records | `pm.qms.evidence` | Yes | Yes | Yes | Yes | Yes | State decorations and review filters. |
| Readiness Center | `pm.qms.readiness.center` | Contextual | Yes | Yes | N/A | Yes | Opened from dashboard/implementation. |
| Historical Readiness | `pm.qms.readiness.assessment` | Yes | Yes | Yes | Yes | Yes | Immutable snapshots remain authoritative history. |
| Documents | `pm.qms.document` | Yes | Yes | Yes | Yes | Contextual | Controlled document workflow. |
| Document Revisions | `pm.qms.document.revision` | Yes | Yes | Yes | Yes | Contextual | Revision status decorations. |
| Risks & Opportunities | `pm.qms.risk` | Yes | Yes | Yes | Yes | Yes | Dashboard route to open risks. |
| NCR | `pm.qms.nonconformity` | Yes | Yes | Yes | Yes | Yes | Dashboard route to open NCRs. |
| CAPA | `pm.qms.capa` | Yes | Yes | Yes | Yes | Yes | Dashboard route to open CAPA. |
| CAPA Actions | `pm.qms.capa.action` | Yes | Yes | Yes | Yes | Contextual | Operational action tracking. |
| Audit Programs | `pm.qms.audit.program` | Yes | Yes | Yes | Yes | Contextual | Internal audit planning. |
| Internal Audits | `pm.qms.audit` | Yes | Yes | Yes | Yes | Contextual | Audit lifecycle route. |
| Audit Evidence | `pm.qms.audit.evidence` | Yes | Yes | Yes | Yes | Contextual | Audit evidence route. |
| Audit Findings | `pm.qms.audit.finding` | Yes | Yes | Yes | Yes | Yes | Dashboard route to open findings. |
| Quality Objectives | `pm.qms.objective` | Yes | Yes | Yes | Yes | Yes | Dashboard performance route. |
| KPI Definitions | `pm.qms.kpi` | Yes | Yes | Yes | Yes | Yes | Dashboard performance route. |
| KPI Measurements | `pm.qms.kpi.measurement` | Yes | Yes | Yes | Yes | Contextual | Measurement history. |
| Customer Performance | `pm.qms.customer.performance` | Yes | Yes | Yes | Yes | Yes | Performance route. |
| Customer Satisfaction | `pm.qms.customer.satisfaction` | Yes | Yes | Yes | Yes | Contextual | Performance route. |
| Supplier Performance | `pm.qms.supplier.performance` | Yes | Yes | Yes | Yes | Yes | Performance route. |
| Supplier Evaluations | `pm.qms.supplier.evaluation` | Yes | Yes | Yes | Yes | Contextual | Supplier performance route. |
| Management Review | `pm.qms.management.review` | Yes | Yes | Yes | Yes | Yes | Dashboard route. |
| Management Review Inputs | `pm.qms.management.review.input` | Yes | Yes | Yes | Yes | Contextual | Snapshot input route. |
| Decisions | `pm.qms.management.review.decision` | Yes | Yes | Yes | Yes | Contextual | Review decision route. |
| Review Actions | `pm.qms.management.review.action` | Yes | Yes | Yes | Yes | Yes | Action tracking route. |
| Migration Tooling | Import wizards | Admin only | N/A | Wizard | N/A | No | Admin/migration route only. |

## Dashboard

The dashboard identifies organization and active implementation, then shows readiness, implementation counts, evidence status, operational health, performance status, management review state, attention-required metrics, and recommended next actions. Navigation goes directly to gaps, evidence requiring attention, risks, NCRs, CAPA, audit findings, objectives, KPIs, and management reviews.

## Implementation Workspace

Implementation records expose stat buttons for controls, activities, evidence, gaps, readiness, and accepted evidence. The workspace keeps the underlying Odoo project available as an execution detail while preserving Perfect Match terminology for the customer-facing route.

## Controls, Activities, Evidence, Readiness

Controls are presented as guided implementation records with purpose, why it matters, implementation guidance, recommended steps, tools, evidence guidance, activity counts, evidence counts, and direct routes to activities and evidence.

Activities remain Odoo `project.task` records but are surfaced through Perfect Match QMS kanban/list/form views. Evidence has review-state filters, state decorations, and an empty state explaining why records matter.

Readiness uses the existing readiness center and historical assessment models. Area progress and recommended next actions have visual priority/state decorations.

## Operational QMS Routes

Documents, revisions, risks, NCR, CAPA, audits, findings, objectives, KPIs, performance records, and management reviews all have customer-facing list/form routes with Odoo-native state decorations. Where useful, actions include search views and concise empty states.

## Framework/Admin Routes

Framework controls, framework packs, processes, organizations, evidence requirements, and external mapping metadata remain authorized framework/admin surfaces. Normal QMS users do not receive framework methodology menus.

## Demo Dataset

Mission 13 does not introduce a new `pm_qms_demo` addon. Existing module demo files remain for module-level development, but no fictional demo dataset is installed into the Oliva pilot and no production module depends on demo data. A future disposable demo database can be created as a separate mission if needed.

## Visual QA Checklist

- Dashboard loads from the Perfect Match QMS app shell.
- Implementation opens with product stat buttons.
- Controls show readable guidance and state.
- Activities open in QMS-filtered kanban/list/form views.
- Evidence shows review state and filters.
- Readiness Center shows area progress and next actions.
- Documents and revisions show lifecycle state.
- Risks, NCR, CAPA, audit, KPI, performance, and management review routes load.
- Framework routes are visible only to authorized manager/admin users.
- External mappings remain metadata only.
- No customer-specific product code is present.
