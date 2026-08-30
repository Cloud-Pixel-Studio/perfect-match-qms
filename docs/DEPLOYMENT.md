# Deployment

Odoo currently has two active VM-local Docker Compose environments:

- DEV under `deployment/docker/dev/`
- Demo under `deployment/docker/demo/`

Neither Odoo environment is exposed directly to the Internet by default.

## DEV

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-dev.sh config
./deployment/scripts/odoo-dev.sh up
./deployment/scripts/odoo-dev.sh health
```

DEV uses:

- Database: `pmqms_dev`
- HTTP: `127.0.0.1:8069`
- Network: `pmqms_dev_network`

## Demo

The public Demo uses the dedicated `pmqms_demo` database and the
`demo.invperfectmatch.com` HTTPS route. It is fictional product data only and
must remain isolated from DEV and unrelated infrastructure. See `docs/DEMO_ENVIRONMENT.md` for
operational commands and secret locations.

The Oliva Torras pilot was retired in RC6. Its database, containers, volumes,
network, secrets, and localhost ports were removed after a validated local
backup. Historical Oliva runbooks remain reference material and are not active
deployment instructions.

## Future Production

Future production deployment should use Docker Compose or an approved
orchestrator, PostgreSQL with managed backups, Nginx reverse proxy, TLS
certificates, environment-variable based configuration, monitored backup
retention, and separate engineering, Demo, and customer production
environments.
