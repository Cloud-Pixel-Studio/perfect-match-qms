# GitHub Governance

GitHub is the sole active engineering and project-management Source of Truth
for Perfect Match QMS. Plane is retired; its repository artifacts are
reference-only history.

## Authority

- Source of truth: `Cloud-Pixel-Studio/perfect-match-qms`
- Work item: GitHub Issue
- Implementation unit: focused Git branch
- Review unit: Pull Request
- Automated gate: QMS CI
- Authoritative integration branch: `main`
- Demo: canonical validation environment, not source-code authority
- Release: immutable Git tag and approved release artifact
- Historical Plane data: reference-only

## Engineering Flow

1. Define the issue or mission in GitHub.
2. Branch from the latest `main`.
3. Implement a narrow, reviewable scope.
4. Run targeted validation and document the result.
5. Commit and push the focused branch.
6. Open a Pull Request to `main`.
7. Wait for QMS CI to pass and complete review.
8. Obtain Product Owner authorization when the change requires it.
9. Merge through the protected repository workflow when applicable.
10. Run the post-merge Demo/deployment gate when the change affects it.
11. Create an immutable release tag only after release authorization.

There is no direct-to-`main` development workflow. Plane updates, Plane API
calls, Plane work items, cycles, statuses, and checkpoints are not part of the
current Definition of Done.

## Definition of Done

A change is complete when applicable scope, focused tests, regression gates,
security checks, documentation, Pull Request review, required authorization,
and merge to `main` are complete. Demo validation and release artifact checks
are added when the change affects those boundaries.

## Historical Boundary

The `plane/` directory is a read-only historical archive. Do not import its
contents, synchronize it, or create bulk GitHub Issues from it. If historical
work is resumed, create a current GitHub Issue and reference the old identifier
only for traceability.

## Recommended Main Policy

The next settings-activation mission should evaluate Pull Request enforcement,
the exact `QMS CI / qms-quality-gate` status check, blocked force pushes and
branch deletion, and an auditable emergency bypass. A small team should use a
review requirement that does not deadlock Product Owner merges; the recommended
starting point is a required Pull Request plus CI, with zero mandatory
third-party approvals until reviewer capacity supports one approval.

Repository settings are intentionally not changed by this documentation PR.
