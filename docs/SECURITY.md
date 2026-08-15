# Security

- Least privilege by default.
- No secrets in Git.
- No direct public exposure of Odoo, PostgreSQL, Redis, RabbitMQ, or internal services.
- Use TLS for public endpoints.
- Audit critical QMS events.
- Keep client data separated by design.
- Keep audit completion separate from corrective-action closure so open
  findings, NCRs, and CAPAs remain visible after an audit report is completed.
- Keep objective targets, KPI results, customer performance, and supplier
  performance isolated by company and organization relationships.
- Do not allow arbitrary SQL, Python, or executable formulas for performance
  measurement calculations.

The AI copilot must use controlled application functions and must not have unrestricted SQL or filesystem access.

The standard development platform must not store CUI.

See `docs/SECURITY_ARCHITECTURE.md` for the QMS role model, company isolation,
document/evidence/audit/performance access rules, and future portal principles.
