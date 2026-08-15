# ADR-047: Guided Implementation and Readiness Center

## Status
Accepted

## Context
Perfect Match QMS needs implementation guidance and certification-readiness navigation without turning external standards into owned application logic or duplicating readiness formulas.

## Decision
Implementation areas belong to framework pack control membership, not to reusable controls. The same reusable control can therefore appear in different areas in different packs. Reusable Perfect Match guidance lives on `pm.qms.control`; client-specific notes and implementation decisions stay on control instances and implementation controls.

The Readiness Center is a guided operational view over existing implementation projects, controls, evidence, and tasks. It uses the stored readiness semantics from implementation controls and project metrics. It does not create a second readiness formula. Recommended next actions are deterministic and come from real gap reasons, missing evidence, and open activities.

External alignment remains metadata only. The guided UI only summarizes approved mapping records when the mapping workflow is installed and approved records exist.

## Consequences
Framework authors can structure packs around implementation journeys while preserving reusable controls. Historical readiness assessments remain immutable snapshots, while the Readiness Center stays live. Quality Pack guidance is seeded with original Perfect Match wording and still requires deeper methodology review before a complete commercial playbook is declared finished.
