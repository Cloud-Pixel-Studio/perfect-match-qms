"""Install only the nine ISO 9001:2026 scenario templates in licensed Demo2.

This script never creates assessment records or a certification decision. It
allows the separately guarded fictional 2015 source fixture after that fixture
has been installed through the dedicated command.
"""

import os

from odoo.addons.pm_qms_iso9001.hooks import (
    ISO9001_2026_PACK_PROFILE_CODE,
    ISO9001_TRANSITION_SCENARIOS,
    ISO9001_TRANSITION_SCENARIO_SEQUENCES,
    _assert_definition,
)
from odoo.addons.pm_qms_iso9001.models.framework_pack import (
    is_authorized_demo_2026_preview,
)


if (
    os.getenv("PMQMS_DEMO_INSTANCE") != "demo2"
    or os.getenv("PMQMS_DEMO_DB") != "pmqms_demo2"
    or env.cr.dbname != "pmqms_demo2"
    or not is_authorized_demo_2026_preview(env)
):
    raise RuntimeError("Scenario installation requires the licensed isolated Demo2026 Preview")

company = env.ref("base.main_company")
packs = env["pm.qms.framework.pack"].sudo().search([])
profiles = env["pm.qms.mapping.profile"].sudo().search([])
target_packs = packs.filtered(lambda item: item.code == "PM-QMS-ISO9001-2026")
target_profiles = profiles.filtered(lambda item: item.code == ISO9001_2026_PACK_PROFILE_CODE)
source_fixture = profiles.filtered(
    lambda item: item.code == "PM-QMS-DEMO-SOURCE-ISO9001-2015"
)
generic_packs = packs.filtered(lambda item: item.code == "PM-QMS-QUALITY")
expected_pack_count = 2 if source_fixture else 1
expected_profile_count = 2 if source_fixture else 1
if not (
    len(packs) == expected_pack_count
    and len(target_packs) == 1
    and target_packs.state == "demo_preview"
    and packs.company_id == company
    and len(target_profiles) == 1
    and target_profiles.pack_id == target_packs
    and target_profiles.company_id == company
    and target_profiles.standard_name == "ISO 9001"
    and target_profiles.edition == "2026"
    and target_profiles.state == "draft"
    and len(target_profiles.mapping_ids) == 65
    and all(mapping.review_status == "draft" for mapping in target_profiles.mapping_ids)
    and len(profiles) == expected_profile_count
    and (
        not source_fixture
        or (
            len(source_fixture) == 1
            and source_fixture.edition == "2015"
            and source_fixture.state == "active"
            and source_fixture.name.startswith("DEMO FIXTURE ONLY")
            and not source_fixture.mapping_ids
            and len(generic_packs) == 1
            and generic_packs.state == "active"
            and source_fixture.pack_id == generic_packs
        )
    )
):
    raise RuntimeError("Demo2026 pack/profile inventory is outside the approved preview fixture")

scenario_definitions = {definition[0]: definition for definition in ISO9001_TRANSITION_SCENARIOS}
if len(scenario_definitions) != 9 or set(scenario_definitions) != set(ISO9001_TRANSITION_SCENARIO_SEQUENCES):
    raise RuntimeError("The nine authored scenario definitions are incomplete")

scenario_model = env["pm.qms.iso9001.transition.scenario"].sudo()
existing_scenarios = scenario_model.search([])
if any(
    scenario.company_id != company or scenario.code not in scenario_definitions
    for scenario in existing_scenarios
):
    raise RuntimeError("Unexpected scenario records already exist in Demo2026")

for (
    code,
    name,
    scenario_type,
    source_edition,
    target_edition,
    objective,
    entry_conditions,
    required_outputs,
    migration_policy,
) in ISO9001_TRANSITION_SCENARIOS:
    values = {
        "name": name,
        "code": code,
        "scenario_type": scenario_type,
        "source_edition": source_edition,
        "target_edition": target_edition,
        "sequence": ISO9001_TRANSITION_SCENARIO_SEQUENCES[code],
        "profile_id": target_profiles.id,
        "company_id": company.id,
        "objective": objective,
        "entry_conditions": entry_conditions,
        "required_outputs": required_outputs,
        "migration_policy": migration_policy,
        "state": "active",
        "active": True,
    }
    existing = existing_scenarios.filtered(lambda scenario: scenario.code == code)
    if len(existing) > 1:
        raise RuntimeError("Duplicate scenario code exists in Demo2026")
    if existing:
        _assert_definition(existing, values, "Demo2026 scenario")
    else:
        scenario_model.with_context(module=True).create(values)

installed = scenario_model.search([])
if len(installed) != 9 or set(installed.mapped("code")) != set(scenario_definitions):
    raise RuntimeError("The complete Demo2026 scenario catalog was not installed")

if os.getenv("PMQMS_SCENARIO_DRY_RUN") == "1":
    env.cr.rollback()
    print("DEMO2026_SCENARIO_DRY_RUN=PASS count=9")
else:
    env.cr.commit()
    print("DEMO2026_SCENARIOS=PASS count=9")
