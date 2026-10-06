"""Create an explicitly fictional ISO 9001:2015 source profile for Demo2026.

This fixture exists only to exercise source-edition transition workflows. It
does not import customer certification, historical records, or ISO mappings.
"""

import os

from odoo.addons.pm_qms_pack_quality.hooks import QUALITY_CONTROLS
from odoo.addons.pm_qms_iso9001.hooks import (
    ISO9001_2026_PACK_CODE,
    ISO9001_2026_PACK_PROFILE_CODE,
    ISO9001_TRANSITION_SCENARIOS,
)
from odoo.addons.pm_qms_iso9001.models.framework_pack import (
    is_authorized_demo_2026_preview,
)


FIXTURE_PROFILE_CODE = "PM-QMS-DEMO-SOURCE-ISO9001-2015"
FIXTURE_PROFILE_NAME = "DEMO FIXTURE ONLY — ISO 9001:2015 source profile"
FIXTURE_PROFILE_NOTES = (
    "Fictional source-edition profile for Demo2026 workflow testing only. "
    "It is not evidence of a real certificate or customer history and contains "
    "no approved external mappings or imported historical records."
)
GENERIC_PACK_CODE = "PM-QMS-QUALITY"


if (
    os.getenv("PMQMS_DEMO_INSTANCE") != "demo2"
    or os.getenv("PMQMS_DEMO_DB") != "pmqms_demo2"
    or env.cr.dbname != "pmqms_demo2"
    or os.getenv("PMQMS_DEMO_PACK_MODE")
    or not is_authorized_demo_2026_preview(env)
):
    raise RuntimeError("The source fixture requires the licensed isolated Demo2026 Preview")

company = env.ref("base.main_company")
pack_model = env["pm.qms.framework.pack"].sudo()
profile_model = env["pm.qms.mapping.profile"].sudo()
packs = pack_model.search([])
target_pack = packs.filtered(lambda item: item.code == ISO9001_2026_PACK_CODE)
if not (
    len(packs) in (1, 2)
    and len(target_pack) == 1
    and target_pack.company_id == company
    and target_pack.state == "demo_preview"
):
    raise RuntimeError("Demo2026 must contain its isolated 2026 Preview pack")

target_profiles = profile_model.search(
    [("code", "=", ISO9001_2026_PACK_PROFILE_CODE), ("company_id", "=", company.id)]
)
if not (
    len(target_profiles) == 1
    and target_profiles.pack_id == target_pack
    and target_profiles.edition == "2026"
    and target_profiles.state == "draft"
    and len(target_profiles.mapping_ids) == 65
    and all(mapping.review_status == "draft" for mapping in target_profiles.mapping_ids)
):
    raise RuntimeError("The unapproved 2026 profile must remain unchanged in Demo Preview")

scenarios = env["pm.qms.iso9001.transition.scenario"].sudo().search([])
expected_scenario_codes = {definition[0] for definition in ISO9001_TRANSITION_SCENARIOS}
if len(scenarios) != 9 or set(scenarios.mapped("code")) != expected_scenario_codes:
    raise RuntimeError("The complete 2026 scenario catalog is required before adding the fixture")

generic_packs = packs.filtered(
    lambda item: item.code == GENERIC_PACK_CODE and item.company_id == company
)
if len(generic_packs) > 1:
    raise RuntimeError("Duplicate generic QMS packs exist in Demo2026")

admin_group = env.ref("pm_qms_core.group_pm_qms_administrator")
admin = env["res.users"].sudo().search(
    [("group_ids", "in", admin_group.id), ("active", "=", True)], limit=1
)
if not admin:
    raise RuntimeError("An active QMS Administrator is required to create the source fixture")
if generic_packs:
    generic_pack = generic_packs
    if generic_pack.state != "active":
        raise RuntimeError("The existing generic QMS pack is not active; refusing to alter it")
else:
    generic_pack = env["pm.qms.framework.pack"].with_user(admin).create(
        {
            "name": "Perfect Match Quality Management Pack",
            "code": GENERIC_PACK_CODE,
            "version": "1.0",
            "company_id": company.id,
            "description": "Standard-neutral Perfect Match QMS control library; source profile fixture only.",
            "pack_type": "standard",
        }
    )

    expected_control_codes = {item["code"] for item in QUALITY_CONTROLS}
    controls = env["pm.qms.control"].sudo().search(
        [("company_id", "=", company.id), ("code", "in", sorted(expected_control_codes))]
    )
    if set(controls.mapped("code")) != expected_control_codes:
        raise RuntimeError("The shared QMS controls needed by the generic pack are incomplete")
    pack_control_model = env["pm.qms.framework.pack.control"].with_user(admin)
    for sequence, control in enumerate(controls.sorted("code"), start=1):
        pack_control_model.create(
            {
                "pack_id": generic_pack.id,
                "control_id": control.id,
                "sequence": sequence * 10,
                "required": True,
            }
        )
    generic_pack.action_activate()

if generic_pack.company_id != company or generic_pack.state != "active":
    raise RuntimeError("The generic source-profile pack is not active for Demo2026")

fixture_profiles = profile_model.search(
    [("company_id", "=", company.id), ("standard_name", "=", "ISO 9001"), ("edition", "=", "2015")]
)
fixture = fixture_profiles.filtered(lambda item: item.code == FIXTURE_PROFILE_CODE)
if len(fixture_profiles) > 1 or len(fixture) > 1:
    raise RuntimeError("Unexpected ISO 9001:2015 profiles exist; refusing to choose a source")

if fixture:
    if not (
        fixture.name == FIXTURE_PROFILE_NAME
        and fixture.notes == FIXTURE_PROFILE_NOTES
        and fixture.pack_id == generic_pack
        and not fixture.mapping_ids
        and fixture.state == "active"
    ):
        raise RuntimeError("The existing Demo2026 2015 fixture differs from its safe definition")
else:
    fixture = env["pm.qms.mapping.profile"].with_user(admin).create(
        {
            "name": FIXTURE_PROFILE_NAME,
            "code": FIXTURE_PROFILE_CODE,
            "company_id": company.id,
            "pack_id": generic_pack.id,
            "standard_name": "ISO 9001",
            "edition": "2015",
            "publisher": "ISO",
            "notes": FIXTURE_PROFILE_NOTES,
        }
    )
    fixture.action_activate()

if not (
    fixture.state == "active"
    and fixture.pack_id == generic_pack
    and not fixture.mapping_ids
    and len(pack_model.search([])) == 2
    and len(profile_model.search([])) == 2
):
    raise RuntimeError("Demo2026 source fixture postconditions failed")

if os.getenv("PMQMS_2015_FIXTURE_DRY_RUN") == "1":
    env.cr.rollback()
    print("DEMO2026_2015_SOURCE_FIXTURE_DRY_RUN=PASS profile=active fictional=1 mappings=0")
else:
    env.cr.commit()
    print("DEMO2026_2015_SOURCE_FIXTURE=PASS profile=active fictional=1 mappings=0")
