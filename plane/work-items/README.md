# Work Items

These files are Plane source artifacts for the initial Perfect Match Digital QMS engineering backlog. They are intended to be imported through an official Plane mechanism after an API token is configured securely.

| ID | Title | Project | Module | Priority | Cycle | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| PMQMS-001 | Finalize Product Architecture Baseline | PMQMS CORE | Perfect Match Controls | HIGH | SPRINT 01 - Foundation | None |
| PMQMS-002 | Approve IP And Standards Policy | PMQMS CORE | Perfect Match Controls | URGENT | SPRINT 01 - Foundation | None |
| PMQMS-003 | Define PM Control Naming Convention | PMQMS CORE | Perfect Match Controls | HIGH | SPRINT 01 - Foundation | PMQMS-002 |
| PMQMS-004 | Create DEV Environment Architecture | PMQMS INFRASTRUCTURE | DEV | HIGH | SPRINT 01 - Foundation | PMQMS-001 |
| PMQMS-005 | Create Backup Strategy For Plane And Future Odoo | PMQMS INFRASTRUCTURE | Backup | URGENT | SPRINT 01 - Foundation | None |
| PMQMS-006 | Define Git Branching And Release Workflow | PMQMS INFRASTRUCTURE | CI/CD | HIGH | SPRINT 01 - Foundation | PMQMS-001 |
| PMQMS-007 | Design Odoo Addon Scaffold | PMQMS PLATFORM | Odoo Architecture | HIGH | SPRINT 01 - Foundation | PMQMS-001 |
| PMQMS-008 | Define Security Roles Baseline | PMQMS PLATFORM | Security and Permissions | HIGH | SPRINT 01 - Foundation | PMQMS-001 |
| PMQMS-009 | Design Auditability Requirements | PMQMS CORE | Perfect Match Controls | HIGH | SPRINT 01 - Foundation | PMQMS-001 |
| PMQMS-010 | Create Initial Test Strategy | PMQMS PLATFORM | Odoo Architecture | HIGH | SPRINT 01 - Foundation | PMQMS-007 |
| PMQMS-011 | Create Plane API Integration Plan | PMQMS INFRASTRUCTURE | CI/CD | HIGH | SPRINT 01 - Foundation | None |
| PMQMS-012 | Validate Plane Backup Gap | PMQMS INFRASTRUCTURE | Backup | URGENT | SPRINT 01 - Foundation | PMQMS-005 |
| PMQMS-013 | Scaffold pm_qms_core Addon | PMQMS CORE | Organization and Processes | HIGH | SPRINT 02 - QMS Core | PMQMS-007, PMQMS-010 |
| PMQMS-014 | Create Organization Model Design | PMQMS CORE | Organization and Processes | HIGH | SPRINT 02 - QMS Core | PMQMS-013 |
| PMQMS-015 | Implement Organization And Process Models | PMQMS CORE | Organization and Processes | HIGH | SPRINT 02 - QMS Core | PMQMS-014 |
| PMQMS-016 | Design PM Control Data Model | PMQMS CORE | Perfect Match Controls | HIGH | SPRINT 02 - QMS Core | PMQMS-003, PMQMS-015 |
| PMQMS-017 | Implement PM Control Odoo Model | PMQMS CORE | Perfect Match Controls | HIGH | SPRINT 02 - QMS Core | PMQMS-016 |
| PMQMS-018 | Design Evidence Model | PMQMS CORE | Evidence Management | HIGH | SPRINT 02 - QMS Core | PMQMS-016 |
| PMQMS-019 | Implement Evidence Models | PMQMS CORE | Evidence Management | HIGH | SPRINT 02 - QMS Core | PMQMS-018 |
| PMQMS-020 | Define Document Control Model | PMQMS CORE | Document Control | HIGH | SPRINT 02 - QMS Core | PMQMS-015 |
| PMQMS-021 | Implement Document Control Foundation | PMQMS CORE | Document Control | HIGH | SPRINT 03 - Controls and Evidence | PMQMS-020 |
| PMQMS-022 | Create PM ISO 9001 Pack Architecture | PMQMS ISO 9001 | Standard Pack Architecture | HIGH | SPRINT 03 - Controls and Evidence | PMQMS-002, PMQMS-016 |
| PMQMS-023 | Design Risk Model | PMQMS CORE | Risk Management | HIGH | SPRINT 03 - Controls and Evidence | PMQMS-015 |
| PMQMS-024 | Implement Risk Management Foundation | PMQMS CORE | Risk Management | HIGH | SPRINT 03 - Controls and Evidence | PMQMS-023 |
| PMQMS-025 | Design NCR Model | PMQMS CORE | NCR | HIGH | SPRINT 03 - Controls and Evidence | PMQMS-015 |
| PMQMS-026 | Implement NCR Foundation | PMQMS CORE | NCR | HIGH | SPRINT 03 - Controls and Evidence | PMQMS-025 |
| PMQMS-027 | Design CAPA Model | PMQMS CORE | CAPA | HIGH | SPRINT 03 - Controls and Evidence | PMQMS-025 |
| PMQMS-028 | Implement CAPA Foundation | PMQMS CORE | CAPA | HIGH | Backlog | PMQMS-027 |
| PMQMS-029 | Design Internal Audit Model | PMQMS CORE | Internal Audit | MEDIUM | Backlog | PMQMS-016 |
| PMQMS-030 | Implement Internal Audit Foundation | PMQMS CORE | Internal Audit | MEDIUM | Backlog | PMQMS-029 |
| PMQMS-031 | Design KPI And Objectives Model | PMQMS CORE | KPI and Objectives | MEDIUM | Backlog | PMQMS-015 |
| PMQMS-032 | Implement KPI Foundation | PMQMS CORE | KPI and Objectives | MEDIUM | Backlog | PMQMS-031 |
| PMQMS-033 | Design Management Review Model | PMQMS CORE | Management Review | MEDIUM | Backlog | PMQMS-031 |
| PMQMS-034 | Implement Management Review Foundation | PMQMS CORE | Management Review | MEDIUM | Backlog | PMQMS-033 |
| PMQMS-035 | Design Customer Portal Architecture | PMQMS PLATFORM | Portal | MEDIUM | Backlog | PMQMS-008 |
| PMQMS-036 | Implement Portal Foundation | PMQMS PLATFORM | Portal | MEDIUM | Backlog | PMQMS-035 |
| PMQMS-037 | Design API Architecture | PMQMS PLATFORM | API Layer | MEDIUM | Backlog | PMQMS-008, PMQMS-016 |
| PMQMS-038 | Design n8n Integration Layer | PMQMS AUTOMATION | n8n Workflows | MEDIUM | Backlog | PMQMS-037 |
| PMQMS-039 | Create Odoo Docker Dev Compose | PMQMS INFRASTRUCTURE | Docker | HIGH | Backlog | PMQMS-004 |
| PMQMS-040 | Create Odoo Addon Test Harness | PMQMS PLATFORM | Odoo Architecture | HIGH | Backlog | PMQMS-010, PMQMS-013 |
| PMQMS-041 | Design CI/CD Pipeline | PMQMS INFRASTRUCTURE | CI/CD | MEDIUM | Backlog | PMQMS-006, PMQMS-040 |
| PMQMS-042 | Design Monitoring Strategy | PMQMS INFRASTRUCTURE | Monitoring | MEDIUM | Backlog | PMQMS-004 |
| PMQMS-043 | Implement Plane Backup Automation | PMQMS INFRASTRUCTURE | Backup | URGENT | Backlog | PMQMS-005, PMQMS-012 |
| PMQMS-044 | Create Odoo Deployment Architecture | PMQMS INFRASTRUCTURE | PRODUCTION | MEDIUM | Backlog | PMQMS-039, PMQMS-041 |
| PMQMS-045 | Design Project Generator | PMQMS PLATFORM | Odoo Architecture | MEDIUM | Backlog | PMQMS-016, PMQMS-022 |
| PMQMS-046 | Implement Project Generator Foundation | PMQMS PLATFORM | Odoo Architecture | MEDIUM | Backlog | PMQMS-045 |
| PMQMS-047 | Create Oliva Torras Pilot Plan | PMQMS OLIVA TORRAS PILOT | Pilot Planning | MEDIUM | Backlog | PMQMS-022, PMQMS-045 |
| PMQMS-048 | Design AI Copilot Architecture | PMQMS AI COPILOT | AI Architecture | LOW | Backlog | PMQMS-037 |
| PMQMS-049 | Design AI Audit Logging | PMQMS AI COPILOT | AI Audit Logging | LOW | Backlog | PMQMS-048 |
| PMQMS-050 | Design Multi-Standard Control Engine | PMQMS MULTI-STANDARD | Mapping Engine | LOW | Backlog | PMQMS-016, PMQMS-022 |
| PMQMS-051 | Design CMMC Boundary | PMQMS DEFENSE | CUI Boundary | LOW | Backlog | PMQMS-008 |
| PMQMS-052 | Create Documentation Quality Gate | PMQMS PLATFORM | Odoo Architecture | MEDIUM | Backlog | PMQMS-006 |
