"""Read-only acceptance checks for the isolated ISO 9001:2026 Demo Preview."""

import os

from odoo.addons.pm_qms_iso9001.hooks import ISO9001_TRANSITION_SCENARIOS
from odoo.addons.pm_qms_iso9001.models.framework_pack import is_authorized_demo_2026_preview


if (
    os.getenv("PMQMS_DEMO_INSTANCE") != "demo2"
    or os.getenv("PMQMS_DEMO_DB") != "pmqms_demo2"
    or env.cr.dbname != "pmqms_demo2"
    or not is_authorized_demo_2026_preview(env)
):
    raise RuntimeError("Demo2026 preview validation requires the exact licensed Demo2 environment")

pack_model = env["pm.qms.framework.pack"].sudo()
packs = pack_model.search([])
if len(packs) != 1 or packs.code != "PM-QMS-ISO9001-2026" or packs.state != "demo_preview":
    raise RuntimeError("Expected only the ISO 9001:2026 pack in Demo Preview")

profiles = env["pm.qms.mapping.profile"].sudo().search([])
if not (
    len(profiles) == 1
    and profiles.pack_id == packs
    and profiles.edition == "2026"
    and profiles.state == "draft"
    and all(mapping.review_status == "draft" for mapping in profiles.mapping_ids)
):
    raise RuntimeError("The 2026 mapping profile or transition isolation is invalid")

scenarios = env["pm.qms.iso9001.transition.scenario"].sudo().search([])
expected_scenarios = {definition[0]: definition for definition in ISO9001_TRANSITION_SCENARIOS}
if not (
    len(expected_scenarios) == 9
    and len(scenarios) == 9
    and set(scenarios.mapped("code")) == set(expected_scenarios)
    and all(
        scenario.profile_id == profiles
        and scenario.target_edition == "2026"
        and scenario.state == "active"
        and scenario.active
        and scenario.source_edition == expected_scenarios[scenario.code][3]
        for scenario in scenarios
    )
    and not env["pm.qms.iso9001.gap.assessment"].sudo().search_count([])
):
    raise RuntimeError("The nine 2026 scenario templates or Demo2026 isolation are invalid")

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
).filtered(lambda project: packs in project.pack_ids)
if len(projects) != 1 or len(projects.implementation_control_ids) < 38:
    raise RuntimeError("The 2026 Demo Preview implementation project is incomplete")

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
print("pack=demo_preview profile=draft mappings=unreviewed")
print("scenario_templates=9 source_profile_2015=absent")
print(f"operational_examples_checked={len(required_examples)}")
