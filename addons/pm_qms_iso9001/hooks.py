import json
from pathlib import Path

from odoo import Command
from odoo.exceptions import UserError


PROFILE_CODE = "PM-QMS-QUALITY-ISO9001"
PROFILE_EDITION = "2015"
PROFILE_NAME = "ISO 9001:2015 + Amendment 1:2024 Mapping"
PROFILE_NOTES = (
    "This profile targets ISO 9001:2015 together with Amendment 1:2024. "
    "External standard references are provided for implementation traceability. "
    "This software does not include or replace the official publication. "
    "Organizations remain responsible for authorized copies of applicable standards."
)


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
    matching_profiles = profiles.filtered(lambda item: item.edition == PROFILE_EDITION)
    if len(matching_profiles) > 1:
        raise UserError("Duplicate ISO 9001 mapping profiles exist for the published edition.")
    profile = matching_profiles[:1]
    if not profile:
        if profiles:
            raise UserError(
                "An ISO 9001 mapping profile already uses this code with another edition; "
                "refusing to overwrite or invent a replacement."
            )
        profile = env["pm.qms.mapping.profile"].with_context(module=True).create(
            {
                "name": PROFILE_NAME,
                "code": PROFILE_CODE,
                "company_id": company.id,
                "pack_id": pack.id,
                "standard_name": "ISO 9001",
                "edition": PROFILE_EDITION,
                "publisher": "ISO",
                "notes": PROFILE_NOTES,
            }
        )
    else:
        profile.with_context(module=True).write({"name": PROFILE_NAME, "notes": PROFILE_NOTES})
    if profile.state == "draft":
        profile.with_context(module=True).action_activate()
    seed_iso9001_initial_implementation(env)


INITIAL_PACK_CODE = "PM-QMS-ISO9001-INITIAL"
INITIAL_PACK_VERSION = "1.0"
AMENDMENT_PACK_VERSION = "1.1"
AMENDMENT_REVISED_LOGICAL_IDS = ("A001", "A002", "A008", "A010", "A011", "A023", "A037")
AMENDMENT_REVISED_KEYS = frozenset(
    f"ISO9001-INITIAL-V11-{logical_id}" for logical_id in AMENDMENT_REVISED_LOGICAL_IDS
)
AMENDMENT_SHARED_KEYS = frozenset(
    f"ISO9001-INITIAL-{i:03d}"
    for i in range(1, 38)
    if f"A{i:03d}" not in AMENDMENT_REVISED_LOGICAL_IDS
)

INITIAL_AUTHORED_CONTENT_FILES = (
    (
        "initial_implementation_p01_p06_v1.json",
        "m25.4-authored-content-v1",
        "M25.4",
        frozenset(f"ISO9001-INITIAL-A{i:03d}" for i in range(1, 11)),
    ),
    (
        "initial_implementation_p07_p08_v1.json",
        "m25.5-authored-content-v1",
        "M25.5",
        frozenset(f"ISO9001-INITIAL-A{i:03d}" for i in range(11, 16)),
    ),
    (
        "initial_implementation_p09_p10_v1.json",
        "m25.6-authored-content-v1",
        "M25.6",
        frozenset(f"ISO9001-INITIAL-A{i:03d}" for i in range(16, 28)),
    ),
    (
        "initial_implementation_p11_p13_v1.json",
        "m25.7-authored-content-v1",
        "M25.7",
        frozenset(f"ISO9001-INITIAL-A{i:03d}" for i in range(28, 38)),
    ),
)


def _initial_blueprint():
    path = Path(__file__).parent / "content" / "initial_implementation_v1.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise UserError("ISO 9001 initial implementation blueprint is invalid.") from exc


def _amendment_blueprint():
    path = Path(__file__).parent / "content" / "initial_implementation_v1_1.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise UserError("ISO 9001 Amendment 1 implementation blueprint is invalid.") from exc


def _amendment_content():
    path = Path(__file__).parent / "content" / "initial_implementation_amendment1_v1_1.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise UserError("ISO 9001 Amendment 1 authored content is invalid.") from exc


def _amendment_evidence_profile():
    path = Path(__file__).parent / "content" / "initial_implementation_evidence_profile_v1_1.json"
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise UserError("ISO 9001 Amendment 1 evidence crosswalk is invalid.") from exc


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


def _validate_authored_content_block(
    data, filename, expected_schema_version, expected_checkpoint, expected_keys
):
    metadata_keys = {"schema_version", "content_checkpoint", "pack_code", "pack_version", "activities"}
    record_keys = {
        "activity_key",
        "content_checkpoint",
        "title",
        "description",
        "objective",
        "why_it_matters",
        "implementation_steps",
        "expected_output",
        "evidence_expectations",
        "success_criteria",
        "responsible_role",
        "activity_kind",
        "readiness_required",
    }
    if expected_checkpoint == "M25.7":
        record_keys.add("applicable_pack_ids")
    records = data.get("activities") if isinstance(data, dict) else None
    actual_keys = [record.get("activity_key") for record in records] if isinstance(records, list) else []
    if (
        not isinstance(data, dict)
        or set(data) != metadata_keys
        or not isinstance(records, list)
        or any(not isinstance(record, dict) or set(record) != record_keys for record in records)
        or data.get("schema_version") != expected_schema_version
        or data.get("content_checkpoint") != expected_checkpoint
        or data.get("pack_code") != INITIAL_PACK_CODE
        or data.get("pack_version") != INITIAL_PACK_VERSION
        or len(records) != len(expected_keys)
        or len(actual_keys) != len(set(actual_keys))
        or set(actual_keys) != set(expected_keys)
    ):
        raise UserError(f"ISO 9001 authored content block {filename} is invalid.")
    required = (
        "title",
        "description",
        "objective",
        "why_it_matters",
        "implementation_steps",
        "expected_output",
        "evidence_expectations",
        "success_criteria",
        "responsible_role",
        "activity_kind",
        "readiness_required",
    )
    for record in records:
        if (
            record.get("content_checkpoint") != expected_checkpoint
            or any(not record.get(field_name) for field_name in required)
            or any(
                not isinstance(record[field_name], str)
                for field_name in required
                if field_name != "readiness_required"
            )
        ):
            raise UserError(
                f"ISO 9001 {expected_checkpoint} content is incomplete for "
                f"{record.get('activity_key')}."
            )
        if record["activity_kind"] != "qms_implementation" or record["readiness_required"] is not True:
            raise UserError(
                f"ISO 9001 {expected_checkpoint} content has invalid activity "
                f"semantics for {record['activity_key']}."
            )
        if expected_checkpoint == "M25.7" and record["applicable_pack_ids"] != [INITIAL_PACK_CODE]:
            raise UserError(
                f"ISO 9001 {expected_checkpoint} content has invalid pack scope for "
                f"{record['activity_key']}."
            )
    return {record["activity_key"]: record for record in records}


def _combine_authored_content_blocks(blocks):
    combined = {}
    for filename, content in blocks:
        duplicates = set(combined).intersection(content)
        if duplicates:
            raise UserError(
                "Duplicate authored activity keys across content blocks: "
                + ", ".join(sorted(duplicates))
            )
        combined.update(content)
    return combined


def _initial_authored_content():
    blocks = []
    content_root = Path(__file__).parent / "content"
    for filename, schema_version, checkpoint, expected_keys in INITIAL_AUTHORED_CONTENT_FILES:
        path = content_root / filename
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise UserError(f"ISO 9001 authored content block {filename} is invalid.") from exc
        blocks.append(
            (
                filename,
                _validate_authored_content_block(
                    data, filename, schema_version, checkpoint, expected_keys
                ),
            )
        )
    return _combine_authored_content_blocks(blocks)


def _validate_authored_blueprint_alignment(authored, blueprint_by_key):
    for key, content in authored.items():
        blueprint = blueprint_by_key.get(key)
        if not blueprint:
            raise UserError(f"Authored activity key {key} is not in the approved blueprint.")
        if blueprint.get("content_checkpoint") != content.get("content_checkpoint"):
            raise UserError(
                f"Authored activity {key} has a checkpoint different from the blueprint."
            )
    return blueprint_by_key


def _seed_initial_authored_activities(seed_env, pack, company, blueprint_activities):
    authored = _initial_authored_content()
    blueprint_by_key = {item["activity_key"]: item for item in blueprint_activities}
    _validate_authored_blueprint_alignment(authored, blueprint_by_key)
    Activity = seed_env["pm.qms.activity"]
    Line = seed_env["pm.qms.framework.pack.control"]
    for key in sorted(authored):
        content = authored[key]
        blueprint = blueprint_by_key.get(key)
        if not blueprint:
            raise UserError(f"Authored content key {key} is not aligned with the blueprint.")
        control = seed_env["pm.qms.control"].search(
            [("code", "=", blueprint["control_code"]), ("company_id", "=", company.id)]
        )
        if len(control) != 1:
            raise UserError(f"Generic control {blueprint['control_code']} is missing or duplicated.")
        line = Line.search(
            [("pack_id", "=", pack.id), ("control_id", "=", control.id)], limit=1
        )
        if not line or line.area_id.code != blueprint["phase_key"]:
            raise UserError(
                f"Authored activity {key} is not aligned with its active pack phase."
            )
        existing = Activity.search(
            [("definition_key", "=", key), ("company_id", "=", company.id)]
        )
        if len(existing) > 1:
            raise UserError(f"Duplicate seeded activity definition {key} exists.")
        values = {
            "definition_key": key,
            "name": content["title"],
            "control_id": control.id,
            "description": content["description"],
            "objective": content["objective"],
            "why_it_matters": content["why_it_matters"],
            "implementation_steps": content["implementation_steps"],
            "expected_output": content["expected_output"],
            "evidence_expectations": content["evidence_expectations"],
            "success_criteria": content["success_criteria"],
            "responsible_role": content["responsible_role"],
            "activity_kind": content["activity_kind"],
            "readiness_required": content["readiness_required"],
            "active": True,
        }
        if existing:
            _assert_definition(existing, values, f"ISO 9001 authored activity {key}")
            if set(existing.applicable_pack_ids.ids) != {pack.id}:
                raise UserError(f"Existing ISO 9001 activity {key} has incompatible pack scope.")
        else:
            Activity.with_context(module=True).create(
                {**values, "applicable_pack_ids": [Command.set([pack.id])]}
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
    _seed_initial_authored_activities(seed_env, pack, company, activities)
    return pack


def _validate_pack_blueprint(blueprint, expected_version, label):
    pack_data = blueprint.get("pack") if isinstance(blueprint, dict) else None
    phases = blueprint.get("phases") if isinstance(blueprint, dict) else None
    activities = blueprint.get("activities") if isinstance(blueprint, dict) else None
    if (
        not isinstance(pack_data, dict)
        or pack_data.get("code") != INITIAL_PACK_CODE
        or pack_data.get("version") != expected_version
        or not isinstance(phases, list)
        or len(phases) != 13
        or not isinstance(activities, list)
        or len(activities) != 37
    ):
        raise UserError(f"{label} blueprint metadata is invalid.")
    phase_codes = [phase.get("code") for phase in phases]
    if phase_codes != [f"P{i:02d}" for i in range(1, 14)]:
        raise UserError(f"{label} phases must be P01-P13.")
    activity_keys = [activity.get("activity_key") for activity in activities]
    control_codes = [activity.get("control_code") for activity in activities]
    if (
        len(activity_keys) != len(set(activity_keys))
        or len(control_codes) != len(set(control_codes))
        or any(activity.get("phase_key") not in set(phase_codes) for activity in activities)
    ):
        raise UserError(f"{label} activity/control keys are invalid.")
    return pack_data, phases, activities


def _ensure_pack_structure(seed_env, company, blueprint, expected_version, label, description):
    pack_data, phases, activities = _validate_pack_blueprint(blueprint, expected_version, label)
    Pack = seed_env["pm.qms.framework.pack"]
    packs = Pack.search(
        [
            ("code", "=", INITIAL_PACK_CODE),
            ("version", "=", expected_version),
            ("company_id", "=", company.id),
        ]
    )
    if len(packs) > 1:
        raise UserError(f"Duplicate {label} packs exist.")
    pack_values = {
        "name": pack_data["name"],
        "code": INITIAL_PACK_CODE,
        "version": expected_version,
        "company_id": company.id,
        "pack_type": "standard",
    }
    pack = packs[:1]
    if pack:
        _assert_definition(pack, pack_values, label)
    else:
        pack = Pack.with_context(pm_qms_pack_workflow=True).create(
            {**pack_values, "description": description}
        )

    Area = seed_env["pm.qms.framework.area"]
    Line = seed_env["pm.qms.framework.pack.control"]
    phase_codes = [phase["code"] for phase in phases]
    areas = Area.search([("pack_id", "=", pack.id)])
    if pack.state != "draft" and (
        len(areas) != len(phases) or set(areas.mapped("code")) != set(phase_codes)
    ):
        raise UserError(f"Active {label} pack has incompatible phases.")
    areas_by_code = {}
    for phase in phases:
        existing = areas.filtered(lambda area: area.code == phase["code"])
        if len(existing) > 1:
            raise UserError(f"Duplicate {label} phase {phase['code']} exists.")
        values = {
            "name": phase["name"],
            "code": phase["code"],
            "pack_id": pack.id,
            "sequence": phase["sequence"],
            "description": phase["description"],
            "active": True,
        }
        if existing:
            _assert_definition(existing, values, f"{label} phase {phase['code']}")
            area = existing
        elif pack.state == "draft":
            area = Area.with_context(module=True).create(values)
        else:
            raise UserError(f"Active {label} pack is missing phase {phase['code']}.")
        areas_by_code[phase["code"]] = area

    Control = seed_env["pm.qms.control"]
    expected_codes = {activity["control_code"] for activity in activities}
    existing_lines = Line.search([("pack_id", "=", pack.id)])
    if pack.state != "draft" and set(existing_lines.mapped("control_id.code")) != expected_codes:
        raise UserError(f"Active {label} pack has incompatible controls.")
    for sequence, activity in enumerate(activities, 1):
        control = Control.search(
            [("code", "=", activity["control_code"]), ("company_id", "=", company.id)]
        )
        if len(control) != 1:
            raise UserError(f"Generic control {activity['control_code']} is missing or duplicated.")
        existing = existing_lines.filtered(lambda line: line.control_id == control)
        if len(existing) > 1:
            raise UserError(f"Duplicate {label} control line exists for {activity['control_code']}.")
        values = {
            "pack_id": pack.id,
            "control_id": control.id,
            "area_id": areas_by_code[activity["phase_key"]].id,
            "sequence": sequence * 10,
            "required": True,
            "active": True,
        }
        if existing:
            _assert_definition(existing, values, f"{label} control {activity['control_code']}")
        elif pack.state == "draft":
            Line.with_context(module=True).create(values)
        else:
            raise UserError(f"Active {label} pack is missing control {activity['control_code']}.")

    if pack.state == "draft":
        pack.with_context(pm_qms_pack_workflow=True).action_activate()
    return pack, phases, activities


def _activity_values(content, definition_key, control_id):
    return {
        "definition_key": definition_key,
        "name": content["title"],
        "control_id": control_id,
        "description": content["description"],
        "objective": content["objective"],
        "why_it_matters": content["why_it_matters"],
        "implementation_steps": content["implementation_steps"],
        "expected_output": content["expected_output"],
        "evidence_expectations": content["evidence_expectations"],
        "success_criteria": content["success_criteria"],
        "responsible_role": content["responsible_role"],
        "activity_kind": content["activity_kind"],
        "readiness_required": content["readiness_required"],
        "active": True,
    }


def _ensure_activity(seed_env, pack, company, blueprint, content, label):
    control = seed_env["pm.qms.control"].search(
        [("code", "=", blueprint["control_code"]), ("company_id", "=", company.id)]
    )
    if len(control) != 1:
        raise UserError(f"Generic control {blueprint['control_code']} is missing or duplicated.")
    line = seed_env["pm.qms.framework.pack.control"].search(
        [("pack_id", "=", pack.id), ("control_id", "=", control.id)], limit=1
    )
    if not line or line.area_id.code != blueprint["phase_key"]:
        raise UserError(f"{label} is not aligned with its active pack phase.")
    definition_key = blueprint["definition_key"]
    Activity = seed_env["pm.qms.activity"]
    existing = Activity.search(
        [("definition_key", "=", definition_key), ("company_id", "=", company.id)]
    )
    if len(existing) > 1:
        raise UserError(f"Duplicate seeded activity definition {definition_key} exists.")
    values = _activity_values(content, definition_key, control.id)
    if existing:
        _assert_definition(existing, values, label)
        activity = existing
    else:
        activity = Activity.with_context(module=True).create(values)
    return activity


def _set_activity_scope(activity, pack_ids, label):
    expected = set(pack_ids)
    if set(activity.applicable_pack_ids.ids) != expected:
        activity.with_context(module=True).write({"applicable_pack_ids": [Command.set(sorted(expected))]})
    if set(activity.applicable_pack_ids.ids) != expected:
        raise UserError(f"{label} has incompatible pack scope.")


def _seed_initial_authored_activities_v11(seed_env, pack, company, blueprint_activities, shared_pack=None):
    authored = _initial_authored_content()
    blueprint_by_key = {item["activity_key"]: item for item in blueprint_activities}
    _validate_authored_blueprint_alignment(authored, blueprint_by_key)
    records = {}
    for key in sorted(authored):
        blueprint = {**blueprint_by_key[key], "definition_key": key}
        activity = _ensure_activity(
            seed_env,
            pack,
            company,
            blueprint,
            authored[key],
            f"ISO 9001 authored activity {key}",
        )
        _set_activity_scope(activity, [pack.id], f"ISO 9001 authored activity {key}")
        records[key] = activity
    if shared_pack:
        for key in sorted(AMENDMENT_SHARED_KEYS):
            _set_activity_scope(records[key], [pack.id, shared_pack.id], f"ISO 9001 shared activity {key}")
    return records


def _validate_amendment_blueprint(blueprint, initial_blueprint):
    pack_data = blueprint.get("pack") if isinstance(blueprint, dict) else None
    phases = blueprint.get("phases") if isinstance(blueprint, dict) else None
    activities = blueprint.get("activities") if isinstance(blueprint, dict) else None
    if (
        not isinstance(pack_data, dict)
        or pack_data.get("code") != INITIAL_PACK_CODE
        or pack_data.get("version") != AMENDMENT_PACK_VERSION
        or phases != initial_blueprint.get("phases")
        or not isinstance(activities, list)
        or len(activities) != 37
    ):
        raise UserError("ISO 9001 Amendment 1 blueprint structure is invalid.")
    logical_ids = [item.get("logical_id") for item in activities]
    if logical_ids != [f"A{i:03d}" for i in range(1, 38)]:
        raise UserError("ISO 9001 Amendment 1 logical activity positions are invalid.")
    for item in activities:
        expected_source = f"ISO9001-INITIAL-{item['logical_id']}"
        if item.get("source_activity_key") != expected_source:
            raise UserError(f"ISO 9001 Amendment 1 source activity is invalid for {item['logical_id']}.")
        expected_key = (
            f"ISO9001-INITIAL-V11-{item['logical_id']}"
            if item["logical_id"] in AMENDMENT_REVISED_LOGICAL_IDS
            else expected_source
        )
        if item.get("definition_key") != expected_key:
            raise UserError(f"ISO 9001 Amendment 1 definition key is invalid for {item['logical_id']}.")
    return pack_data, phases, activities


def _validate_amendment_content(data):
    metadata_keys = {
        "schema_version",
        "mission",
        "pack_code",
        "pack_version",
        "revised_activity_count",
        "activities",
    }
    record_keys = {
        "logical_id",
        "activity_key",
        "content_checkpoint",
        "title",
        "description",
        "objective",
        "why_it_matters",
        "implementation_steps",
        "expected_output",
        "evidence_expectations",
        "success_criteria",
        "responsible_role",
        "activity_kind",
        "readiness_required",
    }
    records = data.get("activities") if isinstance(data, dict) else None
    if (
        not isinstance(data, dict)
        or set(data) != metadata_keys
        or not isinstance(records, list)
        or len(records) != 7
        or any(not isinstance(record, dict) or set(record) != record_keys for record in records)
        or data.get("schema_version") != "m25.11-amendment1-v1.1"
        or data.get("mission") != "M25.11"
        or data.get("pack_code") != INITIAL_PACK_CODE
        or data.get("pack_version") != AMENDMENT_PACK_VERSION
        or data.get("revised_activity_count") != 7
    ):
        raise UserError("ISO 9001 Amendment 1 authored content metadata is invalid.")
    expected_keys = {f"ISO9001-INITIAL-V11-{item}" for item in AMENDMENT_REVISED_LOGICAL_IDS}
    if {record.get("activity_key") for record in records} != expected_keys:
        raise UserError("ISO 9001 Amendment 1 authored content keys are invalid.")
    required = (
        "title",
        "description",
        "objective",
        "why_it_matters",
        "implementation_steps",
        "expected_output",
        "evidence_expectations",
        "success_criteria",
        "responsible_role",
        "activity_kind",
        "readiness_required",
    )
    for record in records:
        if (
            record.get("logical_id") not in AMENDMENT_REVISED_LOGICAL_IDS
            or record.get("activity_key") != f"ISO9001-INITIAL-V11-{record.get('logical_id')}"
            or record.get("content_checkpoint") != "M25.11"
            or any(not record.get(field_name) for field_name in required)
            or any(
                not isinstance(record[field_name], str)
                for field_name in required
                if field_name != "readiness_required"
            )
            or record.get("activity_kind") != "qms_implementation"
            or record.get("readiness_required") is not True
        ):
            raise UserError(
                f"ISO 9001 Amendment 1 content is incomplete for {record.get('activity_key')}."
            )
    return {record["activity_key"]: record for record in records}


def _validate_amendment_evidence_profile(data):
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "standard_name", "edition", "mappings"}
        or data.get("schema_version") != "m25.11-evidence-crosswalk-v1.1"
        or data.get("standard_name") != "ISO 9001"
        or data.get("edition") != PROFILE_EDITION
        or not isinstance(data.get("mappings"), list)
        or len(data["mappings"]) != 37
    ):
        raise UserError("ISO 9001 Amendment 1 evidence crosswalk metadata is invalid.")
    keys = {item.get("activity_key") for item in data["mappings"]}
    expected = {
        f"ISO9001-INITIAL-V11-{logical_id}" if logical_id in AMENDMENT_REVISED_LOGICAL_IDS else f"ISO9001-INITIAL-{logical_id}"
        for logical_id in [f"A{i:03d}" for i in range(1, 38)]
    }
    if keys != expected or any(
        set(item) != {"activity_key", "control_code", "evidence_definition_key", "evidence_policy"}
        for item in data["mappings"]
    ):
        raise UserError("ISO 9001 Amendment 1 evidence crosswalk keys are invalid.")
    return data


def seed_iso9001_initial_implementation(env):
    initial_blueprint = _initial_blueprint()
    amendment_blueprint = _amendment_blueprint()
    initial_authored = _initial_authored_content()
    amendment_content = _validate_amendment_content(_amendment_content())
    _validate_amendment_evidence_profile(_amendment_evidence_profile())
    _validate_amendment_blueprint(amendment_blueprint, initial_blueprint)
    company = env.ref("base.main_company")
    seed_env = env(context=dict(env.context, module="pm_qms_iso9001"))
    initial_pack, _phases, initial_activities = _ensure_pack_structure(
        seed_env,
        company,
        initial_blueprint,
        INITIAL_PACK_VERSION,
        "ISO 9001 initial implementation",
        "Versioned Perfect Match blueprint structure for ISO 9001 initial implementation.",
    )
    initial_records = _seed_initial_authored_activities_v11(
        seed_env, initial_pack, company, initial_activities
    )
    amendment_pack, _amendment_phases, amendment_activities = _ensure_pack_structure(
        seed_env,
        company,
        amendment_blueprint,
        AMENDMENT_PACK_VERSION,
        "ISO 9001 Amendment 1 initial implementation",
        "Versioned Perfect Match implementation pack aligned to Amendment 1:2024 concepts.",
    )
    for blueprint in amendment_activities:
        source_key = blueprint["source_activity_key"]
        if blueprint["definition_key"] == source_key:
            content = initial_authored[source_key]
        else:
            content = amendment_content[blueprint["definition_key"]]
        activity = _ensure_activity(
            seed_env,
            amendment_pack,
            company,
            blueprint,
            content,
            f"ISO 9001 Amendment 1 activity {blueprint['logical_id']}",
        )
        _set_activity_scope(
            activity,
            [amendment_pack.id],
            f"ISO 9001 Amendment 1 activity {blueprint['logical_id']}",
        )
        if blueprint["definition_key"] == source_key:
            _set_activity_scope(
                initial_records[source_key],
                [initial_pack.id, amendment_pack.id],
                f"ISO 9001 shared activity {source_key}",
            )
    for logical_id in AMENDMENT_REVISED_LOGICAL_IDS:
        _set_activity_scope(
            initial_records[f"ISO9001-INITIAL-{logical_id}"],
            [initial_pack.id],
            f"ISO 9001 v1.0 revised activity {logical_id}",
        )
    return initial_pack
