# Docker

Docker artifacts live under `deployment/docker/`.

The Odoo development stack for Mission 02 is in:

`deployment/docker/dev/`

It uses Odoo 19, PostgreSQL 15, a dedicated Docker network, and dedicated named volumes. It does not reuse Plane containers, networks, volumes, databases, or credentials.

Runtime secrets are generated outside Git under:

`/opt/perfect-match/secrets/odoo-dev/`

See `deployment/docker/dev/README.md` for commands.

Odoo and PostgreSQL persistent services use the immutable references from
`deployment/runtime/runtime-lock.json` through the environment wrappers.
Normal startup uses `pull_policy: never`; use the explicit `runtime-fetch`
command when an operator intentionally prepares a locked image.
