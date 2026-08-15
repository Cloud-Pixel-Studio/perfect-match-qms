# IP And Standards Policy

Do not copy, reconstruct, paraphrase at length, or seed copyrighted standard text from ISO, IATF, AS, SAE, CMMC, or any other external source unless a valid license explicitly permits it and the user authorizes it.

External mappings may contain standard name, edition/year if appropriate and authorized, clause or section identifier, mapping type, and Perfect Match-authored applicability notes. External mappings must not contain external standard requirement text.

Perfect Match controls may contain proprietary objective, activity, workflow, evidence expectations, deliverables, responsibilities, approvals, templates, and guidance.

Framework packs may contain Perfect Match-authored control groupings, ordering,
versioning, source-pack metadata, and implementation notes. They must not
contain copied external standard requirement text.

Quality packs may include Perfect Match-authored controls, implementation
activities, evidence expectations, domains, roles, and operational guidance.
They must not claim to reproduce, replace, or summarize an external
publication.

Mapping profiles and imports are allowed to store metadata such as standard
name, edition, publisher, reference identifier, mapping type, review status,
reviewer, review date, and Perfect Match-authored notes. A profile with zero
approved mappings is valid and preferred until a human reviewer supplies
authorized mapping metadata.

The example mapping CSV under `framework/mappings/` is header-only by design.
Real mapping files that contain customer or licensed-reference work should be
handled as controlled inputs and reviewed before import.

Run `deployment/scripts/qms-content-safety.py` before committing standard-pack
or mapping work. The script is a hygiene check for obvious mistakes, not a
legal opinion.
