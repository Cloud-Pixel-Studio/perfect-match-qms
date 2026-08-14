# Security

- Least privilege by default.
- No secrets in Git.
- No direct public exposure of Odoo, PostgreSQL, Redis, RabbitMQ, or internal services.
- Use TLS for public endpoints.
- Audit critical QMS events.
- Keep client data separated by design.

The AI copilot must use controlled application functions and must not have unrestricted SQL or filesystem access.

The standard development platform must not store CUI.
