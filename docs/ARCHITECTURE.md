# Architecture

Odoo is the platform. Perfect Match Digital QMS is the product.

The system starts as a modular Odoo 19 application using a modular monolith architecture. Core business logic belongs in Odoo modules. External automation belongs in n8n. AI behavior must use controlled application functions and must not have unrestricted database access.

## Initial Addon Boundaries

- `pm_qms_core`: core entities, processes, controls, ownership, and state framework.
- `pm_qms_documents`: document control and controlled templates.
- `pm_qms_risk`: risk management.
- `pm_qms_ncr`: nonconformance workflows.
- `pm_qms_capa`: corrective and preventive action workflows.
- `pm_qms_audit`: internal audits.
- `pm_qms_kpi`: objectives and KPI tracking.
- `pm_qms_management_review`: management review packages.
- `pm_qms_portal`: customer portal experience.
- `pm_qms_ai`: controlled AI integration and audit logging.
