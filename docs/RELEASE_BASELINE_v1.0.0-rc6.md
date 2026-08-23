# Perfect Match QMS v1.0.0-rc6 Release Baseline

## Scope

This baseline freezes the standalone product organization, Site, secure access,
Action Center, and Cost of Quality surface delivered through Missions 18 and
19.

## Active Lifecycle

| Environment | Role | Status |
| --- | --- | --- |
| DEV | Engineering, install, upgrade, and regression validation | Active |
| Demo | Fictional customer-facing validation | Active |
| Oliva Torras pilot | Historical customer-specific technical pilot | Retired in RC6 |

The Demo remains isolated in `pmqms_demo` and contains the fictional Apex
Precision Systems organization with exactly three canonical Sites. The former
Oliva database and runtime resources are absent after retirement.

## Security And IP

No secrets are stored in the repository or release assets. External standards
remain reference metadata only; copyrighted requirement text is not copied.
Commercial licensing and Mission 20 are explicitly outside this baseline.

## Verification Evidence

The final report records the validated local Oliva backup, exact resources
removed, DEV and Demo health, code quality gates, CI, Demo visual checks, tag,
GitHub release, and Plane work-item linkage.
