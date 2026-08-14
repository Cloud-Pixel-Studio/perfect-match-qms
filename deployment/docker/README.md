# Docker

Docker artifacts live under `deployment/docker/`.

The Odoo development stack for Mission 02 is in:

`deployment/docker/dev/`

It uses Odoo 19, PostgreSQL 15, a dedicated Docker network, and dedicated named volumes. It does not reuse Plane containers, networks, volumes, databases, or credentials.

Runtime secrets are generated outside Git under:

`/opt/perfect-match/secrets/odoo-dev/`

See `deployment/docker/dev/README.md` for commands.
