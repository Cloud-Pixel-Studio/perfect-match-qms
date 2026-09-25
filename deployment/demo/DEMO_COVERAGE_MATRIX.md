# Demo2 guided manufacturing scenario — coverage matrix

**Status:** source-controlled scenario contract; PASS is granted only by the seeded database and `validate-demo` on the PR HEAD. All organizations, people, suppliers, lots, certificates, measurements, and costs below are synthetic.

The inventory was extracted from all `pm_qms_*` add-on XML window actions. The seven excluded actions are listed at the end with reasons. The remaining 74 menu-action entries map to 62 models. The test `GuidedCoverageContractTests` parses the same XML on every run and fails if a functional action lacks a fixture anchor or a matrix row. Runtime validation requires at least one record for every mapped model.

Roles in the table means the roles granted access by the installed menu groups, model ACLs, and record rules; it is not a blanket grant. The final column records the role-level paths asserted by the validator. Site visibility is additionally checked against each user's computed effective site IDs. Management User remains read-only; its server-side negative tests live in the Management User/CAPA QMS test suites and no destructive write is performed by `validate-demo`.

| Menu / sub-menu action | Model | Demonstration record / state | Relationships | Authorized role scope | Validation |
|---|---|---|---|---|---|
| `menu_pm_qms_dashboard` — Dashboard | `pm.qms.dashboard` | computed dashboard over APEX records (transient, no stored row) | KPI, risks, CAPA, audits, sites | roles with dashboard ACL | source records + Action Center validation |
| `menu_pm_qms_sites` — Sites | `pm.qms.site` | APEX-HQ / APEX-MFG / APEX-INS | APEX organization; named process/person/equipment assignments | Quality Manager; operational roles read per ACL | seed + site-scope check |
| `menu_pm_qms_audit_programs` — Audit Programs | `pm.qms.audit.program` | APEX-AUD-PROG-2026; current-year plan | audit APEX-AUD-001 | Internal Auditor / Quality Manager per ACL | count + role visibility |
| `menu_pm_qms_audits` — Audits | `pm.qms.audit` | APEX-AUD-001; planned/current follow-up | program, scope, plan, criteria, findings, evidence | Internal Auditor / Quality Manager per ACL | count + role visibility |
| `menu_pm_qms_audit_findings` — Findings | `pm.qms.audit.finding` | findings linked to APEX-AUD-001 | audit, process, evidence, corrective follow-up | Internal Auditor / Quality Manager per ACL | count + role visibility |
| `menu_pm_qms_audit_evidence` — Audit Evidence | `pm.qms.audit.evidence` | synthetic reflow sample linked to audit criterion | audit, criterion, controlled document, control instance | Internal Auditor / Quality Manager per ACL | count + role visibility |
| `menu_pm_qms_calibration_equipment` — Monitoring Resources | `pm.qms.equipment` | EQ-0001…EQ-0005; analyzer, multimeter, ESD meter, torque driver, oscilloscope | type, provider, site, process, person, events, impact; overdue/quarantined/out/due-soon/current states | Quality Manager / Supervisor / Process Owner by site scope | status + role/site checks |
| `menu_pm_qms_calibration_due_soon` — Due Soon | `pm.qms.equipment` | EQ-0002, accepted event due in 18 days | calibration event and provider | operational roles per ACL/site scope | equipment-state check |
| `menu_pm_qms_calibration_overdue` — Overdue | `pm.qms.equipment` | EQ-0001 history/overdue scenario | failed event and OOT impact assessment | operational roles per ACL/site scope | equipment-state check |
| `menu_pm_qms_calibration_out` — Out for Calibration | `pm.qms.equipment` | event transitions instrument out, then quarantine | equipment event history | operational roles per ACL/site scope | workflow seed + count |
| `menu_pm_qms_calibration_quarantine` — Quarantined | `pm.qms.equipment` | EQ-0001 quarantined by failed accepted event | APEX-CAL-EVT-001 and APEX-OOT-001 | operational roles per ACL/site scope | equipment-state check |
| `menu_pm_qms_calibration_events` — Calibration Events | `pm.qms.calibration.event` | APEX-CAL-EVT-001…005; failed, overdue, due-soon, current, in-progress service | equipment, provider, three measurement lines, event log | Quality Manager / Supervisor per ACL | count + state check |
| `menu_pm_qms_calibration_impact` — OOT Impact Assessments | `pm.qms.calibration.impact.assessment` | APEX-OOT-001, review open | failed event, affected inspection lot, equipment, NCR follow-up | Quality Manager / Supervisor per ACL | count + link check |
| `menu_pm_qms_calibration_types` — Resource Types | `pm.qms.equipment.type` | APEX-EQTYPE-001 | equipment records | Quality Manager / calibration managers per ACL | count |
| `menu_pm_qms_calibration_providers` — Providers | `pm.qms.calibration.provider` | APEX-CAL-PROV-001 | fictional supplier and accepted/failed events | Quality Manager / calibration managers per ACL | count |
| `menu_pm_qms_capa` — CAPA | `pm.qms.capa` | APEX-CAPA-001 draft; APEX-CAPA-002 implementation; APEX-CAPA-003 closed | NCR/risk, cause analysis, actions, documents, people | Quality Manager / Supervisor; Management User and Viewer read-only | exact state set + access tests |
| `menu_pm_qms_capa_actions` — CAPA Actions | `pm.qms.capa.action` | open, in-progress, completed, and verified actions | parent CAPA, owner, dates, event history | Quality Manager / Supervisor; Management User and Viewer read-only | status counts + ACL tests |
| `menu_pm_qms_control_instances` — Control Instances | `pm.qms.control.instance` | APEX-CI-001…006 | control, process, site, owner, evidence | Quality Manager / Process Owner by scope | model count + role visibility |
| `menu_pm_qms_controls` — Controls | `pm.qms.control` | APEX-CTRL-001…006; activated | process, implementation project, evidence requirements | Quality Manager / Process Owner per ACL | model count |
| `menu_pm_qms_activities` — Activities | `pm.qms.activity` | APEX-ACT-001…006; overdue/today/upcoming | control, process, owner; feeds Action Center | Quality Manager / Process Owner by scope | count + Action Center |
| `menu_pm_qms_evidence_requirements` — Evidence Requirements | `pm.qms.evidence.requirement` | APEX-REQ-001…013 | control instance and document evidence | Quality Manager / Process Owner per ACL | model count |
| `menu_pm_qms_organizations` — Organizations | `pm.qms.organization` | APEX — Apex Precision Electronics, Inc. | company, three sites, processes, people | Quality Manager; configuration access per ACL | exact organization/site validation |
| `menu_pm_qms_processes` — Processes | `pm.qms.process` | APEX-ESD, SMT, ASM, ETEST, CAL, NC, CAPA, TRACE, RECV, DISP and supporting processes | sites, controls, documents, risks, equipment | Quality Manager / Supervisor / Process Owner per scope | canonical process validation |
| `menu_pm_qms_sites` — Sites | `pm.qms.site` | APEX-HQ / APEX-MFG / APEX-INS | plant, electrical laboratory, receiving warehouse | Quality Manager; operational roles read per ACL | three-site exact validation |
| `menu_pm_qms_external_mappings` — External Mappings | `pm.qms.external.mapping` | CUST-DWG-EL-014 mapped to an internal control | control and fictional customer requirement reference | Quality Manager / implementation roles per ACL | model count |
| `menu_pm_qms_operational_events` — Operational Events | `pm.qms.event` | workflow history from audited QMS transitions | documents, audits, CAPA, calibration, supplier workflows | roles with event-history read ACL | model count |
| `menu_pm_qms_cost_events` — Cost Events | `pm.qms.cost.event` | APEX-CQ-001 and APEX-CQ-002, confirmed | complaint/SCAR sources, cost types and exact 4/2 line split | Quality Manager; Management User read-only analytics | 2 confirmed; 6 canonical lines |
| `menu_pm_qms_cost_analytics` — Cost Analytics | `pm.qms.cost.event` | APEX-CQ-001 and APEX-CQ-002 | prevention/appraisal/internal/external failure costs | Management User / Quality Manager per ACL | 4/2 line assertion |
| `menu_pm_qms_cost_types` — Cost Types | `pm.qms.cost.type` | APEX-CQT-PREV / APP / INT / EXT | linked to canonical cost event lines | Quality Manager per ACL | model count |
| `menu_pm_qms_customer_complaints` — Complaints | `pm.qms.customer.complaint` | APEX-CC-001; response due/containment | customer, NCR, quality alert, 8D, cost event | Quality Manager / Supervisor per ACL | model count + role visibility |
| `menu_pm_qms_quality_alerts` — Quality Alerts | `pm.qms.quality.alert` | APEX-QA-001 | complaint, electrical test process, records to preserve | Quality Manager / Supervisor per ACL | model count |
| `menu_pm_qms_root_cause` — Root Cause | `pm.qms.root.cause.analysis` | APEX-RCA-001; five linked questions | solder NCR, controlled work instruction, evidence | Quality Manager / Supervisor per ACL | five-line validation |
| `menu_pm_qms_eight_d` — 8D Cases | `pm.qms.eight.d` | APEX-8D-001 | customer complaint, containment, root cause, corrective action | Quality Manager / Supervisor per ACL | model count |
| `menu_pm_qms_supplier_issues` — Supplier Issues | `pm.qms.supplier.issue` | APEX-SI-001 / SI-002 | Orion/Beacon suppliers, receiving process, SCAR | Quality Manager / Supervisor per ACL | model count |
| `menu_pm_qms_scar` — SCAR | `pm.qms.scar` | APEX-SCAR-001 / SCAR-002; response pending/completed | supplier issue, supplier response, corrective follow-up | Quality Manager / Supervisor per ACL | model count |
| `menu_pm_qms_supplier_quality_root_cause` — Root Cause | `pm.qms.root.cause.analysis` | APEX-RCA-001 | NCR-002 and supplier/material evidence | Quality Manager / Supervisor per ACL | model count |
| `menu_pm_qms_supplier_quality_eight_d` — 8D Cases | `pm.qms.eight.d` | APEX-8D-001 | customer report, containment, corrective action | Quality Manager / Supervisor per ACL | model count |
| `menu_pm_qms_controlled_documents` — Controlled Documents | `pm.qms.document` | APEX-DOC-001…013; active and under review | process, revisions, evidence, acknowledgments | Document Controller / Quality Manager / read roles per ACL | count + role visibility |
| `menu_pm_qms_document_revisions` — Revisions | `pm.qms.document.revision` | controlled revisions with submit/approve/activate workflow | document, reviewer, change summary and effective status | Document Controller / Quality Manager per ACL | workflow seed + count |
| `menu_pm_qms_evidence_records` — Evidence Records | `pm.qms.evidence` | synthetic inspection/certificate/test references for each document | document, process, control and audit/CAPA references | Document Controller / Internal Auditor per ACL | linked evidence count |
| `menu_pm_qms_framework_packs` — Framework Packs | `pm.qms.framework.pack` | PM-QMS-QUALITY | generates implementation controls and evidence requirements | Quality Manager / implementation roles per ACL | required pack + sync assertion |
| `menu_pm_qms_implementation_projects` — Implementation Projects | `pm.qms.implementation.project` | Apex Precision Electronics QMS Guided Implementation | pack, synchronized controls/tasks, readiness assessment | Quality Manager / implementation roles per ACL | required project + controls |
| `menu_pm_qms_implementation_controls` — Implementation Controls | `pm.qms.implementation.control` | synchronized controls from PM-QMS-QUALITY | project, pack clauses, evidence and task relations | Quality Manager / implementation roles per ACL | nonzero synced controls |
| `menu_pm_qms_implementation_tasks` — Activities | `project.task` | tasks synchronized to guided project | implementation control, assignee and due date | Quality Manager / implementation roles per ACL | model count |
| `menu_pm_qms_readiness_assessments` — Readiness Assessments | `pm.qms.readiness.assessment` | Apex guided implementation readiness snapshot; completed | project, assessor, controls, evidence and activities | Quality Manager / implementation roles per ACL | workflow completion required |
| `menu_pm_qms_iso9001_overview` — Overview | `pm.qms.mapping.profile` | active PM-QMS mapping profile | original PMQMS framework content; no copied external standard text | QMS users/viewers granted menu access | model count |
| `menu_pm_qms_iso9001_transition_scenarios` — Implementation and Transition Scenarios | `pm.qms.iso9001.transition.scenario` | ISO9001-2026-TRANSITION-2015 and seven additional ISO 9001:2026 implementation and transition scenarios | profile, source/target edition, entry conditions, outputs and migration policy | QMS users/viewers read; administrator configuration | exactly 8 active scenarios |
| `menu_pm_qms_objectives` — Objectives | `pm.qms.objective` | APEX-OBJ-001 | first-pass/dimensional quality KPI and owner | Quality Manager / Management User read | model count |
| `menu_pm_qms_kpis` — KPIs | `pm.qms.kpi` | eight yield/supplier/NCR/CAPA/calibration/traceability/customer indicators | four periods of measurements; Management Review | Quality Manager / Management User / Viewer per ACL | >=8 KPIs |
| `menu_pm_qms_kpi_measurements` — KPI Measurements | `pm.qms.kpi.measurement` | 32 synthetic historical/current measurements | KPI, reporting period and values | Quality Manager / Management User / Viewer per ACL | >=32 measurements |
| `menu_pm_qms_customer_performance` — Customer Performance | `pm.qms.customer.performance` | fictional Nova Aero 90-day scorecard | survey, complaint, returns/rejections and delivery | Quality Manager / Management User per ACL | required scorecard |
| `menu_pm_qms_customer_satisfaction` — Customer Satisfaction | `pm.qms.customer.satisfaction` | fictional Nova Aero survey aggregate | complaint response and customer-performance KPI | Quality Manager / Management User per ACL | required survey |
| `menu_pm_qms_supplier_performance` — Supplier Performance | `pm.qms.supplier.performance` | 90-day Orion and Beacon scorecards | receiving, supplier issues, SCAR and evaluation | Quality Manager / Management User per ACL | >=2 scorecards |
| `menu_pm_qms_supplier_evaluations` — Supplier Evaluations | `pm.qms.supplier.evaluation` | completed Orion and monitored Beacon evaluations | supplier issues, scorecard and follow-up | Quality Manager / Management User per ACL | completed records required |
| `menu_pm_qms_management_review` — Management Review | `pm.qms.management.review` | APEX review snapshot | KPI, audit, risks, CAPA, suppliers, satisfaction, cost | Management User / Quality Manager / Viewer per ACL | >=8 cross-functional inputs |
| `menu_pm_qms_management_reviews` — Reviews | `pm.qms.management.review` | APEX review | inputs, decisions and actions | Management User / Quality Manager / Viewer per ACL | required snapshot |
| `menu_pm_qms_management_review_actions` — Actions | `pm.qms.management.review.action` | APEX-MRA-001 | review owner and target date; Action Center source | Management User read; Quality Manager manages | model count |
| `menu_pm_qms_management_review_decisions` — Decisions | `pm.qms.management.review.decision` | Alternate supplier qualification decision | supplier performance and review | Management User read; Quality Manager manages | model count |
| `menu_pm_qms_management_review_inputs` — Review Inputs | `pm.qms.management.review.input` | eight cross-functional snapshot inputs | KPI, audit, risk, CAPA, supplier, customer, calibration, previous actions | Management User / Quality Manager / Viewer per ACL | >=8 inputs |
| `menu_pm_qms_nonconformities` — Nonconformities | `pm.qms.nonconformity` | APEX-NCR-001 / NCR-002; containment and disposition | process, customer/supplier issue, CAPA, audit | Quality Manager / Supervisor / Process Owner per ACL | >=2 linked NCRs |
| `menu_pm_qms_quality_pack_profile` — Mapping Profiles | `pm.qms.mapping.profile` | active profile | framework overview and internal mappings | QMS users/viewers granted menu access | model count |
| `menu_pm_qms_quality_external_mappings` — External Mapping Matrix | `pm.qms.external.mapping` | CUST-DWG-EL-014 | customer requirement to internal control | Quality Manager / implementation roles per ACL | model count |
| `menu_pm_qms_people_people` — People | `pm.qms.person` | seven official Demo personas | site, role, training, competency, qualification | Quality Manager / Supervisor per ACL | seven personas present |
| `menu_pm_qms_people_roles` — Roles | `pm.qms.role` | QMS role definitions | access scope and competency/training requirements | Quality Manager / People managers per ACL | model count |
| `menu_pm_qms_people_competencies` — Competencies | `pm.qms.competency` | APEX electrical inspection competency | role requirements, assessments and course | Quality Manager / People managers per ACL | model count |
| `menu_pm_qms_people_matrix` — Competency Matrix | `pm.qms.competency.matrix.line` | role-linked competency requirements | role, competency, validity and notes | Quality Manager / People managers per ACL | nonzero matrix lines |
| `menu_pm_qms_people_assessments` — Assessments | `pm.qms.competency.assessment` | assessments for all seven personas | person, role, competency and evidence | Quality Manager / People managers per ACL | seven records / role visibility |
| `menu_pm_qms_training_courses` — Definitions | `pm.qms.training.course` | APEX-TRN-001 | competency, training event and person records | Quality Manager / People managers per ACL | model count |
| `menu_pm_qms_training_events` — Events | `pm.qms.training.event` | APEX electrical test and ESD refresher session | course, attendee/completion records | Quality Manager / People managers per ACL | event required |
| `menu_pm_qms_training_records` — Records | `pm.qms.training.record` | one record per persona; completed, pending and due dates | course, event, person, role requirement | Quality Manager / Supervisor per ACL; person access where allowed | seven records |
| `menu_pm_qms_qualification_records` — Records | `pm.qms.qualification.record` | one qualification per persona; current/soon/expired dates | qualification type, person and evidence | Quality Manager / People managers per ACL | seven records |
| `menu_pm_qms_qualification_types` — Types | `pm.qms.qualification.type` | APEX-QUAL-001 | electrical inspection qualification records | Quality Manager / People managers per ACL | model count |
| `menu_pm_qms_my_acknowledgments` — My Required Acknowledgments | `pm.qms.document.acknowledgment` | required acknowledgment for assigned operator | controlled document and active revision | individual assigned user / Document Controller per ACL | record required |
| `menu_pm_qms_all_acknowledgments` — All Acknowledgments | `pm.qms.document.acknowledgment` | required acknowledgment and due date | document, revision, person and organization | manager / Document Controller per ACL | record required |
| `menu_pm_qms_risks` — Risks & Opportunities | `pm.qms.risk` | APEX-RISK-001…008; open/monitored | process, owner, mitigation, NCR/CAPA, KPI and review | Quality Manager / Supervisor / Process Owner; Management User and Viewer read | >=8 + role visibility |

## Role walk-through coverage

| Role | Demonstration paths asserted read-only | Scope / write contract |
|---|---|---|
| Quality Manager | documents, risks, CAPA, audits, KPI, Management Review; overall organization | full authorized QMS scope; workflows through official actions |
| Quality Supervisor | processes, risks, CAPA, NCR, equipment | constrained by configured effective sites/processes; cannot see out-of-scope equipment |
| Document Controller | documents, revisions, evidence, acknowledgments | document lifecycle and revision evidence |
| Internal Auditor | audits, findings, audit evidence, documents, risks | audit sample and evidence chain |
| Process Owner | assigned processes, activities, NCR, CAPA, equipment | assigned site/process scope |
| Management User | dashboard, KPI, Management Review, risks, CAPA | read-only; create/write/unlink/action_start/action_complete denied by server-side checks and regression tests |
| QMS Viewer | dashboard, documents, risks, CAPA, audits | read-only role; no writes are attempted by validation |

## Workflow states and evidence relationships

- Documents: submitted/approved/active revisions; assigned acknowledgments and linked synthetic evidence.
- NCR/CAPA: two NCR sources; CAPA-001 draft, CAPA-002 implementation, CAPA-003 closed only via `action_start_analysis`, `action_plan_actions`, `action_start_implementation`, action start/complete/verify, effectiveness, and close workflows.
- Audit: program → audit scope/plan/criterion → finding/evidence, linked to process/document/control.
- Calibration: accepted fail creates quarantine and OOT impact; accepted past-due, due-soon, and current events create three other statuses; the fifth event remains in progress with equipment out for calibration. All five equipment states are asserted.
- Supplier/customer: complaint → alert/8D/NCR and costs; supplier issue → SCAR → evaluation and scorecard.
- Management: 8 inputs and snapshot with linked KPI/audit/risk/CAPA/supplier/customer/calibration/previous action, plus a decision and owned follow-up action.
- Cost of Quality: preserve exactly APEX-CQ-001 = 4 lines and APEX-CQ-002 = 2 lines; both confirmed, exactly six canonical lines.
- Action Center: source records are refreshed by Quality Manager; validator requires at least 8 values across at least 6 source models.
- License: existing Demo2 license remains 1 company / 3 sites / 7 named users; this change neither issues nor modifies it.

## Explicit exclusions

These actions are not instructional business-record screens and are intentionally excluded: `menu_pm_qms_users_access` (system user administration), `menu_pm_qms_license` and `menu_pm_qms_activation_requests` (license administration), `menu_pm_qms_project_generator` (manager-only generator wizard), `menu_pm_qms_document_import` and `menu_pm_qms_evidence_import` (bulk import operations), and `menu_pm_qms_quality_mapping_import` (administrator-only bulk import). Database manager and destructive reset actions are not part of the QMS functional menu inventory.

The data is a walkthrough fixture, not a claim of certification. Intercompany isolation remains untested in the single-company Demo; email/SMTP, external workflow delivery, and full visual certification remain outside this scenario.
