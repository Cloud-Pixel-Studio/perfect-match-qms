# Demo2 clean ISO 9001:2026-only installation

`PMQMS_DEMO_INSTANCE=demo2 ./deployment/scripts/odoo-demo.sh install-demo2-2026-only`
is a first-install-only path for a new, isolated Demo2 database. It accepts only
the canonical Demo2 database, Compose project, volumes, network, and ports; it
checks host capacity and refuses any existing Demo2 container, volume, network,
or database. It also requires the pinned runtime images to be available.

During module installation, `PMQMS_DEMO_PACK_MODE=2026-only` is passed only to
the one-shot Odoo process. The mode is additionally restricted inside addon
hooks to `PMQMS_DEMO_INSTANCE=demo2` and database `pmqms_demo2`. The quality-pack
hook creates its shared proprietary process/control/activity/evidence catalog
but skips creation and activation of the generic `PM-QMS-QUALITY` pack and its
guided-readiness records. The ISO hook creates only the ISO 9001:2026 draft pack,
its draft mapping profile, and unreviewed mappings; it skips the ISO initial
implementation packs, the 2015 profile, and transition-scenario records. The
normal installation path is unchanged when the mode variable is absent.

The command initializes the canonical addon set with Odoo demo data disabled,
does not update an existing database, and does not provision a license, create
demo user accounts, or invoke the general Demo seed. It intentionally stops
after verifying one 2026 draft pack, one 2026 draft profile, no transition
scenarios, and no non-draft mappings. Separate authorized steps are required
before serving the application or loading any fictional operational scenario.

The integration regression `deployment/scripts/tests/test_demo_2026_only_install.sh`
runs only on an isolated GitHub Actions runner. It refuses pre-existing
Demo2-named Docker resources, installs into a clean disposable database using
the repository runtime lock, verifies pack/profile selection and review state,
then removes only the test-owned Compose project and volumes.

This path does not activate the pack, alter review decisions, create an
implementation project, or claim that a customer QMS is compliant or certified.

## Licensed operational demonstration

After importing an independently issued, valid Demo/QA v3 license bound to
Demo2 with limits 1 company / 3 sites / 7 named users, and after deploying the
reviewed Demo Preview code, an operator may run
`PMQMS_DEMO_INSTANCE=demo2 ./deployment/scripts/odoo-demo.sh seed-demo2-2026-only`
following a verified database-and-filestore backup. This command refuses any
other instance, a missing or mismatched license, extra packs or profiles, an
already customer-active pack, transition scenarios, or a missing technical admin account. It
does not read or replace the existing admin password. It creates the fictional
Apex operational company, three sites, seven QMS personas, and cross-module
operational records without loading a generic or ISO 9001:2015 pack or a
transition assessment. It calls the guarded pack workflow to enter the
isolated Demo Preview state and generates a fictional implementation project
from that pack.

After seeding, run
`PMQMS_DEMO_INSTANCE=demo2 ./deployment/scripts/odoo-demo.sh validate-demo2-2026-preview`.
This read-only check requires the signed 1/3/7 entitlement, exactly one
Preview pack, an unapproved 2026 mapping profile, the seeded implementation
project (while permitting separate user-created projects), nine scenario
templates, and operational examples across the installed
QMS modules.

The scenario catalog is installed separately with
`PMQMS_DEMO_INSTANCE=demo2 ./deployment/scripts/odoo-demo.sh seed-demo2-2026-scenarios`
after a verified backup. Set `PMQMS_SCENARIO_DRY_RUN=1` for a rollback-only
rehearsal. This command requires the exact licensed Demo2 Preview and the
single draft 2026 profile. It is idempotent, rejects unexpected definitions,
and never loads the general ISO hook, a generic pack, a 2015 profile, or
transition assessments. The nine active *templates* are new implementation,
2015-to-2026 transition, legacy migration, recertification from 2015,
same-edition 2026 recertification, scope expansion, multi-site rollout,
integrated system, and partial implementation.

An active template is only selectable catalog metadata, not an approved ISO
mapping or a completed transition. The 2015-to-2026 and 2015 recertification
workflows require a real active 2015 source profile and historical records;
their Start Gap Assessment action remains blocked in this 2026-only demo.
Do not fabricate a 2015 source profile or claim that a transition took place.

The ISO 9001:2026 pack is in `demo_preview`, not customer-active. Its mapping
profile and individual mappings remain draft and unapproved. The preview is
valid only for the exact Demo2 database and signed v3 Demo/QA license; a clone
or another environment cannot generate or synchronize projects from it. Normal
activation and customer release remain blocked pending independent practitioner
review and approved publication. The UI labels the preview as not approved.
