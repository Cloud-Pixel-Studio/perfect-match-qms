# AGENTS.md

Instructions for Perfect Match standard packs under `standard_packs/`.

## IP Boundary

Standard packs contain Perfect Match proprietary implementation controls, activities, templates, guidance, evidence expectations, and mappings.

Never copy, paraphrase, reconstruct, or embed copyrighted ISO, IATF, SAE, AS, CMMC, or other external standard text.

External references must be limited to:

- standard/framework name;
- clause/control/reference identifier;
- version/year where legally appropriate;
- Perfect Match internal mapping rationale written in original words.

## Architecture

Keep standard-pack content separate from core QMS models. Shared behavior belongs in Odoo addons under `addons/`; reusable proprietary methodology content belongs in `framework/`; pack-specific mapping and packaging rules belong here.

Avoid duplicating equivalent controls across packs. Prefer shared controls plus additional/framework-specific controls when the architecture supports it.

## Validation

Before committing a standard pack:

- scan for copied external standard language;
- verify mappings are reference-only;
- document assumptions and unresolved licensing questions;
- add tests or validation scripts where generated seed/demo data is involved.
