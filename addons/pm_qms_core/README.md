# pm_qms_core

`pm_qms_core` is the first Odoo addon for Perfect Match Digital QMS.

## Scope

This scaffold introduces the reusable core entities needed before standard packs, client pilots, automation, or AI features:

- QMS processes.
- Perfect Match proprietary controls.
- Implementation activities.
- Evidence requirements.
- External mappings stored separately from proprietary controls.

## IP Boundary

External mappings store only framework names and reference identifiers. Do not copy ISO, IATF, AS, SAE, CMMC, or other copyrighted standard text into this addon.

## Development

Use the DEV stack from the repository root:

```bash
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh test-core
```
