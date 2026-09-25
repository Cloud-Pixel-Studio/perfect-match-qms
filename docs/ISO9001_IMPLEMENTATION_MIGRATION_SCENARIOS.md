# ISO 9001 implementation and migration scenarios

This catalog defines how PMQMS chooses the initial project plan. It does not
make certification decisions and does not replace a customer assessment.

| Code | Scenario | Initial action |
| --- | --- | --- |
| NEW_IMPLEMENTATION_2026 | No formal QMS | Create a 2026 implementation project |
| TRANSITION_2015_TO_2026 | Existing ISO 9001:2015 system | Preserve history and create gap/transition workspace |
| LEGACY_STANDARD_TRANSITION | Older ISO 9001 edition | Inventory first, then staged transition |
| IMPLEMENTED_NOT_CERTIFIED | QMS exists without certificate | Baseline evidence and readiness assessment |
| MIGRATION_FROM_OTHER_SYSTEM | Another QMS or spreadsheets | Controlled inventory, mapping, import and reconciliation |
| RECERTIFICATION | Certified organization | Prioritize audit findings, changes, and transition evidence |
| SCOPE_EXPANSION | New scope, product, process or site | Impact assessment and controlled extension |
| MULTI_SITE_ROLLOUT | Several sites | Pilot one site, then replicate with site-specific evidence |
| INTEGRATED_MANAGEMENT_SYSTEM | Multiple management frameworks | Reuse common controls while preserving framework references |
| PARTIAL_IMPLEMENTATION | Selected capabilities only | Activate contracted modules and declare exclusions |

## Required intake questions

The onboarding wizard should ask:

1. Does the organization have an existing QMS?
2. Which standard edition and certification status apply?
3. Is a certification, surveillance, or transition audit scheduled?
4. What data sources must be migrated?
5. What is the intended certification scope?
6. Which companies, sites, products, and processes are included?
7. Which other frameworks must be integrated?
8. Which records must remain historical and read-only?
9. What evidence is already approved?
10. Who approves the transition plan?

## Output

The wizard produces:

- selected scenario;
- implementation baseline;
- target profile;
- scope and exclusions;
- migration inventory;
- gap-assessment plan;
- responsible roles;
- due dates;
- evidence plan;
- approval gates;
- risks and assumptions.

## Classification

The system must distinguish:

- `NOT_STARTED`;
- `IN_PROGRESS`;
- `IMPLEMENTED`;
- `READY_FOR_INTERNAL_REVIEW`;
- `READY_FOR_CERTIFICATION_REVIEW`;
- `CERTIFIED` — entered only as an external customer-confirmed status;
- `NOT_APPLICABLE`;
- `BLOCKED`.

PMQMS may report implementation readiness. It must not automatically claim that
a customer is certified.
