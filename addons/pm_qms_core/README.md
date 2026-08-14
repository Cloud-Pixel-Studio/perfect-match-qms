# pm_qms_core

`pm_qms_core` is the first Odoo addon for Perfect Match Digital QMS.

## Scope

This scaffold introduces the reusable core entities needed before standard packs, client pilots, automation, or AI features:

- QMS organizations.
- QMS processes.
- Perfect Match proprietary controls.
- Implementation activities.
- Evidence requirements.
- External mappings stored separately from proprietary controls.

## IP Boundary

External mappings store only framework names, editions, reference identifiers, and Perfect Match internal notes. Do not copy ISO, IATF, AS, SAE, CMMC, or other copyrighted standard text into this addon.

The central object is `pm.qms.control`. It is a proprietary Perfect Match implementation object, not an ISO clause or an external standard requirement.

## Models

- `pm.qms.organization`: optional company-bound container for processes.
- `pm.qms.process`: QMS process definitions with owners, hierarchy, inputs, and outputs.
- `pm.qms.control`: proprietary Perfect Match Controls with sequence/manual identifiers.
- `pm.qms.activity`: reusable implementation activities tied to controls.
- `pm.qms.evidence.requirement`: expected evidence definitions tied to controls.
- `pm.qms.external.mapping`: reference-only external standard mappings tied to controls.

## Development

Use the DEV stack from the repository root:

```bash
./deployment/scripts/odoo-dev.sh install-core
./deployment/scripts/odoo-dev.sh update-core
./deployment/scripts/odoo-dev.sh test-core
```
