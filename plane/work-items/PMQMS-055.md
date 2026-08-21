# PMQMS-055 - Harden QMS Activity UX And Project Abstraction

Priority: HIGH
Project: PMQMS PLATFORM
Module: UI/UX
Cycle: Backlog
Labels: odoo, frontend, testing, pilot, architecture
Dependencies: PMQMS-046, PMQMS-047

## Objective

Keep Perfect Match QMS implementation work in a product-specific activity experience while preserving Odoo Project as the underlying execution engine.

## Description

Deliver the Mission 12.1 UX hardening layer for implementation activities. Generated implementation tasks must remain `project.task` records, but users should reach them through Perfect Match QMS menus, actions, labels, guidance fields, and smart buttons instead of the generic Project task surface.

The change must not introduce a duplicate QMS task model and must not hide or break native Odoo Project for roles that still need the execution engine.

## Acceptance Criteria

- A Perfect Match QMS `Activities` action exists for generated implementation `project.task` records.
- Implementation smart buttons and readiness navigation open the QMS activity action instead of the native Project task action.
- Activity kanban, list, search, and form views show implementation, area, control, readiness, and evidence context.
- Native Odoo Project remains available and functional for authorized users.
- Automated tests cover the QMS activity action, smart-button routing, readiness routing, and native Project preservation.
- The Oliva Torras pilot can be updated after backup and still shows QMS implementation activities correctly.
- Documentation and an ADR explain the product abstraction and why `project.task` remains the underlying model.
- Verification evidence is recorded before the item is closed.
