"""Read-only acceptance checks for the isolated ISO 9001:2026 Demo Preview."""

import os

from odoo.addons.pm_qms_iso9001.hooks import ISO9001_TRANSITION_SCENARIOS
from odoo.addons.pm_qms_iso9001.models.framework_pack import is_authorized_demo_2026_preview


SOURCE_FIXTURE_CODE = "PM-QMS-DEMO-SOURCE-ISO9001-2015"
GENERIC_PACK_CODE = "PM-QMS-QUALITY"


if (
    os.getenv("PMQMS_DEMO_INSTANCE") != "demo2"
    or os.getenv("PMQMS_DEMO_DB") != "pmqms_demo2"
    or env.cr.dbname != "pmqms_demo2"
    or not is_authorized_demo_2026_preview(env)
):
    raise RuntimeError("Demo2026 preview validation requires the exact licensed Demo2 environment")

pack_model = env["pm.qms.framework.pack"].sudo()
packs = pack_model.search([])
target_pack = packs.filtered(lambda item: item.code == "PM-QMS-ISO9001-2026")
generic_pack = packs.filtered(lambda item: item.code == GENERIC_PACK_CODE)
if not (
    len(packs) == 2
    and len(target_pack) == 1
    and target_pack.state == "demo_preview"
    and len(generic_pack) == 1
    and generic_pack.state == "active"
):
    raise RuntimeError("Expected the 2026 Preview pack and the active generic source-fixture pack")

profile_model = env["pm.qms.mapping.profile"].sudo()
profiles = profile_model.search([])
target_profile = profiles.filtered(lambda item: item.edition == "2026")
source_profile = profiles.filtered(lambda item: item.code == SOURCE_FIXTURE_CODE)
if not (
    len(profiles) == 2
    and len(target_profile) == 1
    and target_profile.pack_id == target_pack
    and target_profile.state == "draft"
    and len(target_profile.mapping_ids) == 65
    and all(mapping.review_status == "draft" for mapping in target_profile.mapping_ids)
    and len(target_profile.mapping_ids.filtered("demo_preview_usable")) == 65
    and len(source_profile) == 1
    and source_profile.pack_id == generic_pack
    and source_profile.standard_name == "ISO 9001"
    and source_profile.edition == "2015"
    and source_profile.state == "active"
    and source_profile.name.startswith("DEMO FIXTURE ONLY")
    and "Fictional source-edition profile" in source_profile.notes
    and not source_profile.mapping_ids
):
    raise RuntimeError("The 2026 Preview profile or fictional active 2015 source fixture is invalid")

scenarios = env["pm.qms.iso9001.transition.scenario"].sudo().search([])
expected_scenarios = {definition[0]: definition for definition in ISO9001_TRANSITION_SCENARIOS}
assessments = env["pm.qms.iso9001.gap.assessment"].sudo().search([])
if not (
    len(expected_scenarios) == 9
    and len(scenarios) == 9
    and set(scenarios.mapped("code")) == set(expected_scenarios)
    and all(
        scenario.profile_id == target_profile
        and scenario.target_edition == "2026"
        and scenario.state == "active"
        and scenario.active
        and scenario.source_edition == expected_scenarios[scenario.code][3]
        for scenario in scenarios
    )
    and all(
        assessment.company_id == env.ref("base.main_company")
        and assessment.scenario_id in scenarios
        and assessment.state in ("draft", "in_progress", "completed", "cancelled")
        for assessment in assessments
    )
):
    raise RuntimeError("The nine 2026 templates, assessments, or Demo2026 isolation are invalid")

organization = env["pm.qms.organization"].sudo().search(
    [("code", "=", "APEX"), ("organization_kind", "=", "operational")], limit=1
)
if not organization:
    raise RuntimeError("Fictional Apex operational organization is missing")

usage = env["pm.qms.entitlement.service"].usage(organization.company_id)
if (
    usage["status"] not in ("valid", "expiring")
    or usage["company"]["used"] != 1
    or usage["site"]["used"] != 3
    or usage["named_user"]["used"] != 7
    or (usage["company"]["limit"], usage["site"]["limit"], usage["named_user"]["limit"])
    != (1, 3, 7)
):
    raise RuntimeError("Demo2026 operational use does not match the signed 1/3/7 limits")

projects = env["pm.qms.implementation.project"].sudo().search(
    [("organization_id", "=", organization.id)]
).filtered(lambda project: target_pack in project.pack_ids)
seeded_projects = projects.filtered(
    lambda project: project.name == "Apex Precision Electronics QMS Guided Implementation"
)
if len(seeded_projects) != 1 or len(seeded_projects.implementation_control_ids) < 38:
    raise RuntimeError("The seeded 2026 Demo Preview implementation project is incomplete")

required_examples = {
    "pm.qms.process": 10,
    "pm.qms.document": 10,
    "pm.qms.risk": 5,
    "pm.qms.nonconformity": 2,
    "pm.qms.capa": 3,
    "pm.qms.audit": 1,
    "pm.qms.equipment": 5,
    "pm.qms.customer.complaint": 1,
    "pm.qms.supplier.issue": 2,
    "pm.qms.cost.event": 2,
    "pm.qms.management.review": 1,
    "pm.qms.person": 7,
}
for model_name, minimum in required_examples.items():
    if model_name not in env:
        raise RuntimeError(f"Missing installed QMS model: {model_name}")
    model = env[model_name].sudo()
    if "organization_id" in model._fields:
        domain = [("organization_id", "=", organization.id)]
    elif "company_id" in model._fields:
        domain = [("company_id", "=", organization.company_id.id)]
    else:
        raise RuntimeError(f"Cannot scope Demo2026 validation model: {model_name}")
    if model.search_count(domain) < minimum:
        raise RuntimeError(f"Insufficient fictional Demo2026 records: {model_name}")

print("DEMO2026_PREVIEW_VALIDATION=PASS")
print("license=valid-v3-demo-qa limits=1/3/7")
print("pack=demo_preview profile=draft mappings=demo-only-usable/unreviewed approved-coverage=0")
print("scenario_templates=9 source_profile_2015=active-fictional-fixture mappings=0")
print(f"gap_assessments={len(assessments)}")
print(f"operational_examples_checked={len(required_examples)}")
