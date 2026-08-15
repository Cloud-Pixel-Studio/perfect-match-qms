# Deployment

Plane is available at `https://plane.cloudpixelstudio.agency`.

Odoo currently has two VM-local Docker Compose environments:

- DEV under `deployment/docker/dev/`
- Oliva technical pilot under `deployment/docker/pilot/`

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

## Oliva Pilot

```bash
cd /opt/perfect-match/perfect-match-qms
./deployment/scripts/odoo-pilot.sh config
./deployment/scripts/odoo-pilot.sh up
./deployment/scripts/odoo-pilot.sh health
```

The Oliva pilot uses:

- Database: `pmqms_oliva_pilot`
- HTTP: `127.0.0.1:8169`
- Network: `pmqms_oliva_pilot_network`

Public DNS and TLS routing for the pilot require a separate controlled reverse
proxy change. Do not route pilot traffic through Plane's database, network, or
volumes.

## Future Production

Future production deployment should use Docker Compose or an approved
orchestrator, PostgreSQL with managed backups, Nginx reverse proxy, TLS
certificates, environment-variable based configuration, monitored backup
retention, and separate DEV, STAGING, PILOT, and PRODUCTION environments.
