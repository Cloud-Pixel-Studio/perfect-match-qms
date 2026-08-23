# Demo Security Guide

The public Demo is a dedicated fictional Apex Precision Systems environment.
Credentials are provisioned by the existing Demo secret mechanism and are not
stored in this document or in Git.

## Personas

| Persona | Role | Scope |
| --- | --- | --- |
| Olivia Parker | Quality Manager | Apex organization, all sites and processes |
| Daniel Brooks | Quality Supervisor | Manufacturing Plant and processes linked to it |
| Maria Lewis | Document Controller | Apex organization, all sites and processes for document work |
| James Carter | Internal Auditor | Apex organization, all sites and processes |
| Emma Reed | Process Owner | Production and Final Inspection processes |
| Michael Stone | Management User | Apex organization, read-oriented management visibility |

The seed is idempotent and is restricted to `pmqms_demo`. It must not be used
against `pmqms_oliva_pilot`.

## Validation scenarios

1. Sign in as Olivia and confirm the dashboard, Users & Access, all three Apex
   sites, and the major QMS menus are visible.
2. Sign in as Daniel and confirm Manufacturing Plant records are visible while
   an Inspection & Distribution record is outside the assigned site/process
   scope.
3. Sign in as Maria and verify document work is visible without granting a
   system administrator role.
4. Sign in as James and verify audit records and independence controls.
5. Sign in as Emma and verify only the selected process scope is visible.
6. Sign in as Michael or the QMS Viewer test user and verify read-only behavior
   for risk, NCR, CAPA, audit, equipment, complaint, supplier, and cost records.

After validation, rotate the Demo administrator secret again if it was exposed
to a browser or support session. Keep the replacement in the existing local
secret file with restrictive permissions.
