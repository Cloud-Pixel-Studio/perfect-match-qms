# Plane Project Management Source

This directory stores the source artifacts for the Perfect Match Digital QMS Plane workspace.

Plane is the operational project-management interface. This Git repository is the source of truth for project-management configuration where practical.

## Target Workspace

- Name: PERFECT MATCH DIGITAL QMS
- Suggested workspace identifier: PMQMS

## Official Integration Path

Use official Plane mechanisms only:

1. Plane-supported configuration tooling, if available for the installed edition/version.
2. Official Plane REST API.
3. Official Plane MCP integration, if later enabled and appropriate.

The current self-hosted instance requires an API key for REST calls. Generate it in Plane under Profile Settings > Personal Access Tokens, then store it outside Git as a root-readable secret or environment variable such as `PLANE_API_KEY`.

`PLANE_API_TOKEN` is accepted only as a backward-compatible alias by existing tooling. Prefer `PLANE_API_KEY` for new automation.

Do not paste tokens into source files, Markdown documents, shell history, or Git commits.

## Duplicate Prevention

Before importing any artifact, the importer must list existing workspaces, projects, labels, modules, cycles, and work items and match by stable name/identifier. If an equivalent object exists, update it or skip it instead of creating duplicates.

## Contents

- `projects/`: workspace project definitions.
- `modules/`: module definitions by project.
- `workflows.md`: workflow/state model.
- `labels.md`: reusable labels.
- `roadmap.md`: phases and product roadmap.
- `milestones.md`: product milestones.
- `cycles/`: first three two-week development cycles.
- `work-items/`: initial engineering backlog.
