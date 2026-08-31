# Development Workflow

Active workflow:

1. GitHub Issue
2. READY
3. IN DEVELOPMENT
4. CODE REVIEW
5. TESTING
6. UAT
7. MERGED / DONE

Critical path: Architecture, Infrastructure, Odoo development environment, PM QMS Core, Controls, Evidence, Document Control, Risk/NCR/CAPA, Audits, KPI, Management Review, ISO 9001 Pack, Project Generator, standalone product foundation, and secure access.

AI, multi-standard, CMMC, and commercial licensing work come later. The Oliva
pilot is historical and retired.

## Local Odoo DEV Loop

Use the isolated DEV stack:

```bash
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh test-core
```

Before closing the related GitHub Issue or Pull Request:

- Make sure the related addon installs or updates cleanly.
- Run the relevant Odoo test command.
- Update docs when architecture, security, data model, or workflow behavior changes.
- Confirm no external standard text was copied into code, XML, tests, seed data, or documentation.

## Secrets

Runtime secrets belong outside Git. For the local DEV stack they are generated under:

`/opt/perfect-match/secrets/odoo-dev/`
