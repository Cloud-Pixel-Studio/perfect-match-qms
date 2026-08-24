# Deployment Scripts

`customer-instance.sh` is the operator-controlled Mission 21 foundation for
isolated customer and ephemeral test instances. It consumes
`deployment/customer/modules.txt` and approved release bundles. It never
targets the canonical DEV or Demo databases and never stores runtime state in
the repository.

The existing `odoo-dev.sh` and `odoo-demo.sh` scripts remain environment-
specific. Do not use Demo seed, Demo license, Demo credentials, or Demo
database volumes for customer provisioning.
