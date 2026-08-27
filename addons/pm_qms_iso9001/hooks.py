import json
from pathlib import Path

from odoo.exceptions import UserError


PROFILE_CODE = "PM-QMS-QUALITY-ISO9001"
PROFILE_EDITION = "2015"


def post_init_hook(env):
    company = env.ref("base.main_company")
    pack = env["pm.qms.framework.pack"].search(
        [
            ("code", "=", "PM-QMS-QUALITY"),
            ("version", "=", "1.0"),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    if not pack:
        raise UserError("The PM-QMS-QUALITY framework pack is required before ISO 9001 can be installed.")

    profiles = env["pm.qms.mapping.profile"].search(
        [("code", "=", PROFILE_CODE), ("company_id", "=", company.id)]
    )
    profile = profiles.filtered(lambda item: item.edition == PROFILE_EDITION)[:1]
    if not profile:
        if profiles:
            raise UserError(
                "An ISO 9001 mapping profile already uses this code with another edition; "
                "refusing to overwrite or invent a replacement."
            )
        profile = env["pm.qms.mapping.profile"].with_context(module=True).create(
            {
                "name": "ISO 9001 Current Published Edition Mapping",
                "code": PROFILE_CODE,
                "company_id": company.id,
                "pack_id": pack.id,
                "standard_name": "ISO 9001",
                "edition": PROFILE_EDITION,
                "publisher": "ISO",
                "notes": (
                    "External standard references are provided for implementation traceability. "
                    "This software does not include or replace the official publication. "
                    "Organizations remain responsible for authorized copies of applicable standards."
                ),
            }
        )
    if profile.state == "draft":
        profile.with_context(module=True).action_activate()
    seed_iso9001_initial_implementation(env)


INITIAL_PACK_CODE = "PM-QMS-ISO9001-INITIAL"
INITIAL_PACK_VERSION = "1.0"


def _initial_blueprint():
    path = Path(__file__).parent / "content" / "initial_implementation_v1.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise UserError("ISO 9001 initial implementation blueprint is invalid.") from exc


def _assert_definition(record, values, label):
    for field_name, expected in values.items():
        actual = record[field_name]
        if hasattr(actual, "id") and isinstance(expected, int):
            actual = actual.id
        if actual != expected:
            raise UserError(
                f"Existing {label} is incompatible with the ISO 9001 initial "
                f"implementation definition: {field_name}."
            )


def seed_iso9001_initial_implementation(env):
    blueprint = _initial_blueprint()
    pack_data = blueprint.get("pack") or {}
    phases = blueprint.get("phases") or []
    activities = blueprint.get("activities") or []
    if (
        pack_data.get("code") != INITIAL_PACK_CODE
        or pack_data.get("version") != INITIAL_PACK_VERSION
        or len(phases) != 13
    ):
        raise UserError("ISO 9001 initial implementation blueprint metadata is invalid.")
    phase_codes = [phase.get("code") for phase in phases]
    if phase_codes != [f"P{i:02d}" for i in range(1, 14)]:
        raise UserError("ISO 9001 initial implementation phases must be P01-P13.")
    activity_keys = [activity.get("activity_key") for activity in activities]
    control_codes = [activity.get("control_code") for activity in activities]
    if len(activity_keys) != len(set(activity_keys)) or len(control_codes) != len(set(control_codes)):
        raise UserError("ISO 9001 initial implementation blueprint keys must be unique.")
    areas_by_code = {phase["code"]: phase for phase in phases}
    if any(activity.get("phase_key") not in areas_by_code for activity in activities):
        raise UserError("ISO 9001 initial implementation blueprint has an unknown phase.")

    company = env.ref("base.main_company")
    seed_env = env(context=dict(env.context, module="pm_qms_iso9001"))
    Pack = seed_env["pm.qms.framework.pack"]
    packs = Pack.search(
        [
            ("code", "=", INITIAL_PACK_CODE),
            ("version", "=", INITIAL_PACK_VERSION),
            ("company_id", "=", company.id),
        ]
    )
    if len(packs) > 1:
        raise UserError("Duplicate ISO 9001 initial implementation packs exist.")
    pack = packs[:1]
    pack_values = {
        "name": pack_data["name"],
        "code": INITIAL_PACK_CODE,
        "version": INITIAL_PACK_VERSION,
        "company_id": company.id,
        "pack_type": "standard",
    }
    if pack:
        _assert_definition(pack, pack_values, "ISO 9001 initial implementation pack")
    else:
        pack = Pack.with_context(pm_qms_pack_workflow=True).create(
            {**pack_values, "description": "Versioned Perfect Match blueprint structure for ISO 9001 initial implementation; guided content continues through later authoring checkpoints."}
        )

    Area = seed_env["pm.qms.framework.area"]
    areas = Area.search([("pack_id", "=", pack.id)])
    if len(areas) != len(phases) or set(areas.mapped("code")) != set(phase_codes):
        if pack.state != "draft":
            raise UserError("Active ISO 9001 initial implementation pack has incompatible phases.")
    areas_by_code_record = {}
    for phase in phases:
        existing = areas.filtered(lambda area: area.code == phase["code"])
        if len(existing) > 1:
            raise UserError(f"Duplicate ISO 9001 phase {phase['code']} exists.")
        values = {
            "name": phase["name"],
            "code": phase["code"],
            "pack_id": pack.id,
            "sequence": phase["sequence"],
            "description": phase["description"],
            "active": True,
        }
        if existing:
            _assert_definition(existing, values, f"ISO 9001 phase {phase['code']}")
            area = existing
        elif pack.state == "draft":
            area = Area.with_context(module=True).create(values)
        else:
            raise UserError(f"Active ISO 9001 initial implementation pack is missing phase {phase['code']}.")
        areas_by_code_record[phase["code"]] = area

    Control = seed_env["pm.qms.control"]
    Line = seed_env["pm.qms.framework.pack.control"]
    expected_codes = set(control_codes)
    existing_lines = Line.search([("pack_id", "=", pack.id)])
    if pack.state != "draft" and set(existing_lines.mapped("control_id.code")) != expected_codes:
        raise UserError("Active ISO 9001 initial implementation pack has incompatible controls.")
    for sequence, activity in enumerate(activities, 1):
        control = Control.search(
            [("code", "=", activity["control_code"]), ("company_id", "=", company.id)]
        )
        if len(control) != 1:
            raise UserError(f"Generic control {activity['control_code']} is missing or duplicated.")
        existing = existing_lines.filtered(lambda line: line.control_id == control)
        if len(existing) > 1:
            raise UserError(f"Duplicate ISO 9001 control line exists for {activity['control_code']}.")
        values = {
            "pack_id": pack.id,
            "control_id": control.id,
            "area_id": areas_by_code_record[activity["phase_key"]].id,
            "sequence": sequence * 10,
            "required": True,
            "active": True,
        }
        if existing:
            _assert_definition(existing, values, f"ISO 9001 control {activity['control_code']}")
        elif pack.state == "draft":
            Line.with_context(module=True).create(values)
        else:
            raise UserError(f"Active ISO 9001 initial implementation pack is missing control {activity['control_code']}.")

    if pack.state == "draft":
        pack.with_context(pm_qms_pack_workflow=True).action_activate()
    return pack
