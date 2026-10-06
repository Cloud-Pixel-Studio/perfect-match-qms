"""Install only the nine ISO 9001:2026 scenario templates in licensed Demo2.

This script never creates a 2015 source profile, generic framework pack,
assessment, or certification decision. Run through the guarded Demo launcher.
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
if not (
    len(packs) == 1
    and packs.code == "PM-QMS-ISO9001-2026"
    and packs.state == "demo_preview"
    and packs.company_id == company
    and len(profiles) == 1
    and profiles.code == ISO9001_2026_PACK_PROFILE_CODE
    and profiles.pack_id == packs
    and profiles.company_id == company
    and profiles.standard_name == "ISO 9001"
    and profiles.edition == "2026"
    and profiles.state == "draft"
    and len(profiles.mapping_ids) == 65
    and all(mapping.review_status == "draft" for mapping in profiles.mapping_ids)
):
    raise RuntimeError("Demo2026 must retain only its unapproved 2026 pack and profile")

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
        "profile_id": profiles.id,
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
