# Framework Architecture

The QMS framework is a reusable Perfect Match methodology, not a copy of an
external standard. `pm_qms_core` owns controls, activities, evidence
requirements, and generic external reference records. `pm_qms_implementation`
owns framework pack versions, pack lines, areas, project generation, and
readiness. `pm_qms_pack_quality` owns the proprietary PM-QMS-QUALITY catalog
and its guided seed.

The generic engines accept any active pack and do not branch on ISO 9001 or
another standard. Standard profile metadata and future reviewed reference
identifiers live in a standard add-on. The base framework therefore operates
with zero standards installed.

Framework definitions are master data. **Configuration > Framework
Administration** is restricted to `QMS Administrator`; ordinary QMS users
work with generated implementation controls, activities, evidence, and
readiness records.
