# Development Cycles

Use two-week development cycles. Only the first three cycles are planned in detail; later work remains in the backlog until dependencies are clearer.

## SPRINT 01 - Foundation

| ID | Title | Project | Module | Priority | Dependencies |
| --- | --- | --- | --- | --- | --- |
| PMQMS-001 | Finalize Product Architecture Baseline | PMQMS CORE | Perfect Match Controls | HIGH | None |
| PMQMS-002 | Approve IP And Standards Policy | PMQMS CORE | Perfect Match Controls | URGENT | None |
| PMQMS-003 | Define PM Control Naming Convention | PMQMS CORE | Perfect Match Controls | HIGH | PMQMS-002 |
| PMQMS-004 | Create DEV Environment Architecture | PMQMS INFRASTRUCTURE | DEV | HIGH | PMQMS-001 |
| PMQMS-005 | Create Backup Strategy For Plane And Future Odoo | PMQMS INFRASTRUCTURE | Backup | URGENT | None |
| PMQMS-006 | Define Git Branching And Release Workflow | PMQMS INFRASTRUCTURE | CI/CD | HIGH | PMQMS-001 |
| PMQMS-007 | Design Odoo Addon Scaffold | PMQMS PLATFORM | Odoo Architecture | HIGH | PMQMS-001 |
| PMQMS-008 | Define Security Roles Baseline | PMQMS PLATFORM | Security and Permissions | HIGH | PMQMS-001 |
| PMQMS-009 | Design Auditability Requirements | PMQMS CORE | Perfect Match Controls | HIGH | PMQMS-001 |
| PMQMS-010 | Create Initial Test Strategy | PMQMS PLATFORM | Odoo Architecture | HIGH | PMQMS-007 |
| PMQMS-011 | Create Plane API Integration Plan | PMQMS INFRASTRUCTURE | CI/CD | HIGH | None |
| PMQMS-012 | Validate Plane Backup Gap | PMQMS INFRASTRUCTURE | Backup | URGENT | PMQMS-005 |

## SPRINT 02 - QMS Core

| ID | Title | Project | Module | Priority | Dependencies |
| --- | --- | --- | --- | --- | --- |
| PMQMS-013 | Scaffold pm_qms_core Addon | PMQMS CORE | Organization and Processes | HIGH | PMQMS-007, PMQMS-010 |
| PMQMS-014 | Create Organization Model Design | PMQMS CORE | Organization and Processes | HIGH | PMQMS-013 |
| PMQMS-015 | Implement Organization And Process Models | PMQMS CORE | Organization and Processes | HIGH | PMQMS-014 |
| PMQMS-016 | Design PM Control Data Model | PMQMS CORE | Perfect Match Controls | HIGH | PMQMS-003, PMQMS-015 |
| PMQMS-017 | Implement PM Control Odoo Model | PMQMS CORE | Perfect Match Controls | HIGH | PMQMS-016 |
| PMQMS-018 | Design Evidence Model | PMQMS CORE | Evidence Management | HIGH | PMQMS-016 |
| PMQMS-019 | Implement Evidence Models | PMQMS CORE | Evidence Management | HIGH | PMQMS-018 |
| PMQMS-020 | Define Document Control Model | PMQMS CORE | Document Control | HIGH | PMQMS-015 |

## SPRINT 03 - Controls and Evidence

| ID | Title | Project | Module | Priority | Dependencies |
| --- | --- | --- | --- | --- | --- |
| PMQMS-021 | Implement Document Control Foundation | PMQMS CORE | Document Control | HIGH | PMQMS-020 |
| PMQMS-022 | Create PM ISO 9001 Pack Architecture | PMQMS ISO 9001 | Standard Pack Architecture | HIGH | PMQMS-002, PMQMS-016 |
| PMQMS-023 | Design Risk Model | PMQMS CORE | Risk Management | HIGH | PMQMS-015 |
| PMQMS-024 | Implement Risk Management Foundation | PMQMS CORE | Risk Management | HIGH | PMQMS-023 |
| PMQMS-025 | Design NCR Model | PMQMS CORE | NCR | HIGH | PMQMS-015 |
| PMQMS-026 | Implement NCR Foundation | PMQMS CORE | NCR | HIGH | PMQMS-025 |
| PMQMS-027 | Design CAPA Model | PMQMS CORE | CAPA | HIGH | PMQMS-025 |

## Backlog

PMQMS-028 through PMQMS-052 remain in backlog until the first three cycles produce validated architecture and implementation evidence.
