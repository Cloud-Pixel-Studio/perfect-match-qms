# M31.1 Customer Browser UAT Baseline

## Scope

This is a discovery baseline for the customer-facing browser experience. It
does not change product behavior and does not claim WCAG compliance. The test
ran against a disposable fictional customer instance created from
`b7a6951cb8e3cb91e542dac739c2c52743b2eda6`. Demo, production, cleanvm-test-02,
and real customer environments were not used.

The browser harness is the Playwright package in
`tools/tests/UAT/`. Its generated JSON, traces, screenshots, and runtime
credentials remain local evidence and are excluded from Git.

## Environment and personas

- Instance: disposable `m31-uat-test`, destroyed after evidence capture.
- Browser: Chrome 151.0.7922.174 through Playwright.
- Viewports: 1440x900 and 1366x768.
- Personas: first Quality Manager, restricted QMS Viewer, and Technical
  Administrator.
- Customer readiness and the ephemeral test license were PASS/valid.
- The Quality Manager was not a system administrator.

## Automated result

The harness executed 4 Playwright tests with 4 passed and 0 failed:

1. Quality Manager shell, full menu inventory, guided implementation, tabs,
   and two idempotent Sync Framework runs.
2. Representative domain routes, Action Center, Company Profile, Processes,
   Sites, Commercial License, ISO Overview, notifications, and user menu.
3. Axe baseline on login, dashboard, implementation, Action Center, and
   Company Profile, plus responsive overflow checks.
4. Viewer restrictions and Technical Administrator separation.

Telemetry across the tested customer and administrator pages was:

- uncaught page errors: 0
- console errors: 0
- console warnings: 0
- failed requests: 0
- unexpected HTTP 4xx: 0
- HTTP 5xx: 0
- RPC failures: 0

## Customer shell and navigation

The visible customer shell contained Perfect Match QMS, Dashboard, Action
Center, Implementation, Quality Operations, Assurance, Performance, Standards,
and Configuration. Apps, Settings, Tests, Project, and Discuss were not
exposed to the Quality Manager.

The menu inventory recorded 84 visible link entries, representing 69 unique
label/XML-ID destinations. Representative customer routes passed without a
client or server error:

- Action Center
- Risks & Opportunities
- Nonconformities
- CAPA
- Complaints
- Audits
- KPIs
- People
- Monitoring Resources
- Controlled Documents
- Company Profile
- Processes
- Sites
- Commercial License
- ISO 9001 Overview

The requested `Management Review` label was not exposed as a menu link. The
dashboard still displayed Management Review summary entries. This is recorded
as a navigation/content follow-up, not silently treated as a passed route.

## Guided implementation workflow

The browser-only New Implementation wizard created one fictional ISO 9001
Initial Implementation using the approved v1.0 pack. Read-only Odoo ORM
evidence for the generated record was:

- controls: 37
- operational processes in the customer organization: 20
- control instances: 37
- activities: 118
- generated tasks linked to the implementation: 111

The implementation form exposed Packs, Controls, Implementation Areas,
Activities, Evidence Summary, Readiness, Assessments, and History. The visible
stat strip and generated project code were present. Sync Framework was run
twice through the supported UI and showed zero growth on both runs:

`processes 0 / controls 0 / instances 0 / tasks 0`

The implementation list also exposed a generic `New` button. It opened the
direct implementation form at the implementation-project action without the
guided generator. This was not executed or saved. Because it can bypass the
core guided workflow, it is classified P1 for product-owner triage. The
observed action XML ID was
`pm_qms_implementation.menu_pm_qms_implementation_projects`; the numeric
runtime action ID is intentionally not used as a permanent identifier.

Search/filter, empty-result handling, view-switcher and pager controls were
recorded as baseline observations. No change was made when the list did not
render a separate view-switcher or pager control in the tested state.

## Persona and data boundaries

- Quality Manager: customer shell and guided implementation flow PASS.
- Viewer: Apps, Settings, Commercial License, and unexpected implementation
  creation were not available; restriction checks PASS.
- Technical Administrator: Apps and Settings remained available; separation
  check PASS.
- No cross-company access, framework leakage, or unauthorized product mutation
  was observed in the covered checks.
- One fictional implementation was created by the planned UAT flow. No Demo,
  production, real customer, or cleanvm-test-02 data was changed.

## Accessibility baseline

Axe was run on all five required screens. Findings are baseline evidence, not
an assertion of conformance:

| Screen | Violations | Critical | Serious | Moderate | Incomplete |
| --- | ---: | ---: | ---: | ---: | ---: |
| Login | 6 | 1 | 2 | 3 | 1 |
| Dashboard | 5 | 2 | 1 | 2 | 1 |
| Implementation | 13 | 5 | 4 | 3 | 2 |
| Action Center | 12 | 4 | 3 | 4 | 1 |
| Company Profile | 12 | 5 | 2 | 4 | 1 |

The recurring rule IDs included `aria-required-children`,
`aria-required-parent`, `html-has-lang`, `meta-viewport`, `region`, form
label/name findings, and image/role labeling findings. Keyboard and responsive
smoke checks completed without horizontal overflow; a full accessibility
certification was not attempted.

## Terminology and experience findings

| Finding | Surface | Classification | Severity |
| --- | --- | --- | --- |
| Generic `New` on Implementation list can bypass guided creation | Implementations | Product workflow defect | P1 |
| `Management Review` summary exists but requested navigation label is absent | Customer navigation | Product/navigation follow-up | P2 |
| Native `My Company` wording in the single-company header | Authenticated header | Native Odoo surface / terminology review | P3 |
| `Implementations` and `Activities` coexist with native task concepts | Implementation form | Customer terminology review | P3 |

No product correction is included in M31.1. The recommended order is to
review the guided-create boundary first, then reconcile Management Review
navigation, then decide whether terminology polish is worth changing.

## Classification

- P0: 0.
- P1: 1, generic direct implementation creation path.
- P2: 1, Management Review navigation/content mismatch; accessibility
  findings remain a baseline workstream and should be triaged by impact.
- P3: 2, native/company and activity terminology review.

These findings are observations for Product Owner triage. They are not hidden
behind cosmetic scores, and they are not fixes in this baseline branch.

## Reproduction and cleanup

Run from `tools/tests/UAT/` with password-file environment variables, for
example `npm ci` followed by `npm test`. Use only a disposable instance. The
fictional test release tag was local-only and was not pushed. The disposable
instance, its generated data, and local test tag were removed after evidence
capture. No release tag or GitHub release was created.
