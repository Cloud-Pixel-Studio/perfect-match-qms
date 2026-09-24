import base64
import os
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import Command, fields
from odoo.addons.pm_qms_app.hooks import restrict_optional_platform_menus

DEMO_INSTANCE = os.getenv("PMQMS_DEMO_INSTANCE", "demo")
APPROVED_DEMO_DATABASES = {"demo": "pmqms_demo", "demo2": "pmqms_demo2"}
EXPECTED_DB = os.getenv("PMQMS_DEMO_DB", APPROVED_DEMO_DATABASES.get(DEMO_INSTANCE, ""))
COMPANY_NAME = os.getenv("PMQMS_DEMO_COMPANY_NAME", "Apex Precision Electronics, Inc.")
ADMIN_LOGIN = os.getenv("PMQMS_DEMO_ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.getenv("PMQMS_DEMO_ADMIN_PASSWORD")
QUALITY_MANAGER_LOGIN = os.getenv("PMQMS_DEMO_QUALITY_MANAGER_LOGIN", "olivia.parker.demo@perfectmatch.local")
PERSONA_PASSWORD_DIR = Path(os.getenv("PMQMS_DEMO_PERSONA_PASSWORD_DIR", "/run/pmqms-demo-persona-passwords"))
ORG_CODE = "APEX"

def validate_seed_database(instance_name, configured_db, actual_db):
    """Allow only the explicitly approved Demo instance/database pairs."""
    expected_db = APPROVED_DEMO_DATABASES.get(instance_name)
    if not expected_db or configured_db != expected_db or actual_db != expected_db:
        raise RuntimeError(
            f"Demo seed refused for instance {instance_name!r} and database {actual_db!r}; "
            "only approved Demo instance/database pairs are allowed."
        )
    return expected_db


def ensure_guided_implementation_project(project_model, manager_user, existing_project, values):
    """Keep the seed idempotent and run generation as its authorized QMS manager."""
    if existing_project:
        return existing_project
    return project_model.with_user(manager_user).generate_from_wizard(values)


validate_seed_database(DEMO_INSTANCE, EXPECTED_DB, env.cr.dbname)

restrict_optional_platform_menus(env)

now = fields.Datetime.now()
today = fields.Date.context_today(env["res.company"])
# Frozen reporting window keeps four synthetic KPI periods stable across reruns.
scenario_as_of = fields.Date.to_date("2026-09-23")
overdue = today - relativedelta(days=14)
due_today = today
due_soon = today + relativedelta(days=7)
next_month = today + relativedelta(months=1)

warnings = []
created = {}

def model_exists(model_name):
    return model_name in env

def ref(xmlid):
    try:
        return env.ref(xmlid)
    except Exception:
        return env["ir.model.data"].browse()

def field_selection(model, field):
    selection = model._fields[field].selection
    if isinstance(selection, str):
        selection = getattr(model, selection)()
    elif callable(selection):
        selection = selection(model)
    return selection or []

def best_selection(model, field, preferred=()):
    if field not in model._fields:
        return False
    keys = [key for key, _label in field_selection(model, field)]
    for key in preferred:
        if key in keys:
            return key
    return keys[0] if keys else False

def filtered(model_name, vals):
    if not model_exists(model_name):
        return {}
    model = env[model_name]
    clean = {k: v for k, v in vals.items() if k in model._fields}
    for name, field in model._fields.items():
        if name in clean or not field.required or field.compute or field.related or field.type in ("one2many", "many2many"):
            continue
        if name in ("state", "status") or name.endswith("_status"):
            continue
        if name == "company_id":
            clean[name] = company.id
        elif name == "organization_id":
            clean[name] = organization.id
        elif name == "process_id" and processes:
            clean[name] = processes[0].id
        elif name.endswith("owner_id") or name in ("owner_id", "detected_by_id", "project_manager_id", "reviewer_id", "assessor_id"):
            clean[name] = demo_user.id
        elif name.endswith("person_id") and persons:
            clean[name] = persons[0].id
        elif name == "partner_id":
            clean[name] = customer.id
        elif name in ("customer_id", "supplier_id"):
            clean[name] = (customer if name == "customer_id" else supplier).id
        elif name == "currency_id":
            clean[name] = company.currency_id.id
        elif field.type in ("char", "html", "text"):
            clean[name] = clean.get("name") or "Perfect Match fictional demo value"
        elif field.type in ("date",):
            clean[name] = today
        elif field.type in ("datetime",):
            clean[name] = now
        elif field.type in ("integer",):
            clean[name] = 1
        elif field.type in ("float", "monetary"):
            clean[name] = 1.0
        elif field.type == "boolean":
            clean[name] = False
        elif field.type == "selection":
            choice = best_selection(model, name)
            if choice:
                clean[name] = choice
    return clean

def domain_for(model_name, code=None, name=None, extra=None):
    model = env[model_name]
    domain = list(extra or [])
    if code and "code" in model._fields:
        domain.append(("code", "=", code))
    elif name and "name" in model._fields:
        domain.append(("name", "=", name))
    elif name and "title" in model._fields:
        domain.append(("title", "=", name))
    return domain


def scoped_person_record_identity(
    person_id, related_field, related_id, organization_id, company_id
):
    """Return the stable identity used by the canonical Demo fixture."""
    return [
        ("person_id", "=", person_id),
        (related_field, "=", related_id),
        ("organization_id", "=", organization_id),
        ("company_id", "=", company_id),
    ]


def training_identity_domain(person_id, course_id, organization_id, company_id):
    return scoped_person_record_identity(
        person_id, "course_id", course_id, organization_id, company_id
    )


def qualification_identity_domain(
    person_id, qualification_type_id, organization_id, company_id
):
    return scoped_person_record_identity(
        person_id,
        "qualification_type_id",
        qualification_type_id,
        organization_id,
        company_id,
    )


def upsert(model_name, code=None, name=None, vals=None, extra_domain=None, required=True):
    vals = dict(vals or {})
    if not model_exists(model_name):
        if required:
            warnings.append(f"missing_model:{model_name}")
        return env["ir.model"].browse()
    model = env[model_name]
    domain = domain_for(model_name, code=code, name=name, extra=extra_domain)
    record = model.search(domain, limit=1) if domain else model.browse()
    payload = filtered(model_name, vals)
    if code and "code" in model._fields:
        payload["code"] = code
    if name:
        if "name" in model._fields:
            payload["name"] = name
        elif "title" in model._fields:
            payload["title"] = name
    try:
        with env.cr.savepoint():
            if record:
                writable = {
                    k: v
                    for k, v in payload.items()
                    if k not in ("code",)
                    and not model._fields[k].readonly
                    and not field_value_equal(record[k], model._fields[k], v)
                }
                if writable:
                    record.write(writable)
            else:
                record = model.create(payload)
        return record
    except Exception as exc:
        warnings.append(f"{model_name}:{code or name}:{exc.__class__.__name__}:{exc}")
        return model.browse()


def upsert_by_identity(model_name, identity, vals, required=False):
    """Idempotently reconcile a scenario row using an explicit stable domain."""
    if not model_exists(model_name):
        if required:
            raise RuntimeError(f"Required Demo scenario model is missing: {model_name}")
        return env["ir.model"].browse()
    model = env[model_name]
    payload = filtered(model_name, vals)
    record = model.search(identity, limit=1)
    try:
        with env.cr.savepoint():
            if record:
                writable = {
                    key: value
                    for key, value in payload.items()
                    if not model._fields[key].readonly
                    and not field_value_equal(record[key], model._fields[key], value)
                }
                if writable:
                    record.write(writable)
            else:
                record = model.create(payload)
        return record
    except Exception as exc:
        message = f"{model_name}:{identity}:{exc.__class__.__name__}:{exc}"
        warnings.append(message)
        if required:
            raise RuntimeError(f"Required Demo scenario row failed: {model_name}") from exc
        return model.browse()


def field_value_equal(current, field, incoming):
    if field.type == "many2one":
        incoming_id = incoming.id if hasattr(incoming, "id") else incoming
        return current.id == incoming_id
    if field.type == "many2many":
        original = set(current.ids)
        desired = set(original)
        for command in incoming or []:
            if not isinstance(command, (list, tuple)) or len(command) < 1:
                return False
            operation = command[0]
            if operation == 0 or operation == 1:
                return False
            if operation == 2:
                if len(command) < 2:
                    return False
                if command[1] in desired:
                    return False
            elif operation == 3:
                if len(command) < 2:
                    return False
                desired.discard(command[1])
            elif operation == 4:
                if len(command) < 2:
                    return False
                desired.add(command[1])
            elif operation == 5:
                desired.clear()
            elif operation == 6:
                if len(command) < 3 or not isinstance(command[2], (list, tuple, set)):
                    return False
                desired = set(command[2])
            else:
                return False
        return original == desired
    return current == incoming


def upsert_capa_why(capa, sequence, answer):
    """Seed one fixed CAPA Why slot without using generic payload filling."""
    model = env["pm.qms.capa.why"]
    record = model.search(
        [("capa_id", "=", capa.id), ("sequence", "=", sequence)],
        limit=1,
    )
    try:
        with env.cr.savepoint():
            if record:
                if record.answer != answer:
                    record.write({"answer": answer})
                return record
            return model.with_context(pm_qms_capa_initialize=True).create(
                {"capa_id": capa.id, "sequence": sequence, "answer": answer}
            )
    except Exception as exc:
        warnings.append(f"pm.qms.capa.why:{capa.id}:{sequence}:{exc.__class__.__name__}:{exc}")
        return model.browse()

def call(record, *names):
    if not record:
        return False
    for name in names:
        if hasattr(record, name):
            try:
                getattr(record, name)()
                return True
            except Exception as exc:
                warnings.append(f"workflow:{record._name}:{name}:{exc.__class__.__name__}:{exc}")
    return False

company = env.company
usd = env.ref("base.USD", raise_if_not_found=False)
company_vals = {"name": COMPANY_NAME}
logo_path = "/mnt/extra-addons/pm_qms_app/static/description/perfect_match_logo_master.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as logo_file:
        company_vals["logo"] = base64.b64encode(logo_file.read()).decode("ascii")
if usd:
    company_vals["currency_id"] = usd.id
company.write(company_vals)

qms_manager = ref("pm_qms_core.group_pm_qms_manager")
qms_admin = ref("pm_qms_core.group_pm_qms_administrator")
system_admin = ref("base.group_system")
base_user = ref("base.group_user")
role_group_xmlids = {
    "Quality Manager": "pm_qms_core.group_qms_quality_manager",
    "Quality Supervisor": "pm_qms_core.group_qms_quality_supervisor",
    "Document Controller": "pm_qms_core.group_qms_document_controller",
    "Internal Auditor": "pm_qms_core.group_qms_internal_auditor",
    "Process Owner": "pm_qms_core.group_qms_process_owner",
    "Management User": "pm_qms_core.group_qms_management_user",
    "QMS Viewer": "pm_qms_core.group_qms_viewer",
}
role_groups = {role: ref(xmlid) for role, xmlid in role_group_xmlids.items() if ref(xmlid)}

if ADMIN_LOGIN == QUALITY_MANAGER_LOGIN:
    raise RuntimeError("Demo technical admin and Quality Manager logins must be different.")

# Keep the externally managed Demo admin as a technical account. The named
# Quality Manager is a separate fictional persona and is never a System Admin.
technical_admin = env["res.users"].with_context(no_reset_password=True).search(
    [("login", "=", ADMIN_LOGIN)], limit=1
)
technical_admin_values = {
    "name": "Perfect Match Technical Administrator",
    "email": ADMIN_LOGIN,
    "company_id": company.id,
    "pmqms_license_account_type": "technical",
    "pmqms_license_exempt": True,
    "pmqms_license_exemption_reason": "Technical Demo administration; does not consume a customer QMS seat.",
}
if base_user and system_admin and qms_admin:
    technical_admin_values["group_ids"] = [Command.set([base_user.id, system_admin.id, qms_admin.id])]
if technical_admin:
    technical_admin.write(technical_admin_values)
else:
    technical_admin_values["login"] = ADMIN_LOGIN
    if ADMIN_PASSWORD:
        technical_admin_values["password"] = ADMIN_PASSWORD
    technical_admin = env["res.users"].with_context(no_reset_password=True).create(technical_admin_values)

# The framework/library organization is internal product content, not a
# separately licensed customer company. Normalize the legacy demo row before
# touching the operational organization so the Mission 20 company entitlement
# remains idempotent across upgrades.
if model_exists("pm.qms.organization") and "organization_kind" in env["pm.qms.organization"]._fields:
    framework_organization = env["pm.qms.organization"].search(
        [("code", "=", "PM-QMS-FRAMEWORK")], limit=1
    )
    if framework_organization:
        framework_organization.write({"organization_kind": "framework"})

organization = upsert(
    "pm.qms.organization",
    code=ORG_CODE,
    name=COMPANY_NAME,
    vals={
        "name": COMPANY_NAME,
        "code": ORG_CODE,
        "company_id": company.id,
        "description": "Fictional precision manufacturing company used only for Perfect Match QMS product demonstrations.",
    },
)

site_specs = [
    (
        "APEX-HQ",
        "Manufacturing Plant",
        "manufacturing",
        True,
        "SMT, assembly, ESD controls, production supervision, and point-of-use quality activities.",
    ),
    (
        "APEX-MFG",
        "Electrical Test Laboratory",
        "laboratory",
        False,
        "Electrical verification, measurement equipment, calibration, and failure analysis.",
    ),
    (
        "APEX-INS",
        "Warehouse & Receiving",
        "warehouse",
        False,
        "Supplier receiving, incoming inspection, material traceability, storage, and dispatch.",
    ),
]
sites = []
if model_exists("pm.qms.site") and organization:
    for code, name, site_type, is_primary, description in site_specs:
        site = upsert(
            "pm.qms.site",
            code=code,
            name=name,
            vals={
                "name": name,
                "code": code,
                "organization_id": organization.id,
                "site_type": site_type,
                "is_primary": is_primary,
                "timezone": "America/New_York",
                "description": description,
            },
            required=False,
        )
        if site:
            sites.append(site)
site_by_code = {site.code: site for site in sites}

user_specs = [
    ("Olivia Parker", QUALITY_MANAGER_LOGIN, "Quality Manager"),
    ("Daniel Brooks", "daniel.brooks.demo@perfectmatch.local", "Quality Supervisor"),
    ("Maria Lewis", "maria.lewis.demo@perfectmatch.local", "Document Controller"),
    ("James Carter", "james.carter.demo@perfectmatch.local", "Internal Auditor"),
    ("Emma Reed", "emma.reed.demo@perfectmatch.local", "Process Owner"),
    ("Michael Stone", "michael.stone.demo@perfectmatch.local", "Management User"),
    ("Victor Lee", "qms.viewer.demo@perfectmatch.local", "QMS Viewer"),
]
users = {}
for full_name, login, role in user_specs:
    vals = {"name": full_name, "login": login, "email": login, "company_id": company.id, "company_ids": [Command.link(company.id)]}
    assigned_groups = [g.id for g in (base_user, role_groups.get(role)) if g]
    if assigned_groups:
        vals["group_ids"] = [Command.set(sorted(set(assigned_groups)))]
    persona_password_file = PERSONA_PASSWORD_DIR / role.lower().replace(" ", "-")
    persona_password = (
        persona_password_file.read_text(encoding="utf-8").strip()
        if persona_password_file.is_file()
        else None
    )
    user = env["res.users"].with_context(no_reset_password=True).search([("login", "=", login)], limit=1)
    if user:
        writable = {k: v for k, v in vals.items() if k != "login"}
        user.write(writable)
    else:
        if persona_password:
            vals["password"] = persona_password
        user = env["res.users"].with_context(no_reset_password=True).create(vals)
    users[role] = user

demo_user = users["Quality Manager"]
if organization and "quality_contact_id" in organization._fields:
    organization.write(
        {
            "quality_contact_id": demo_user.id,
            "qms_scope": "Fictional Apex precision manufacturing QMS covering leadership, production, inspection, customer quality, supplier quality, and support processes.",
        }
    )
customer = env["res.partner"].search([("name", "=", "Nova Aero Components LLC"), ("company_id", "in", [False, company.id])], limit=1)
if not customer:
    customer = env["res.partner"].create({"name": "Nova Aero Components LLC", "email": "quality@nova-aero.example", "company_id": company.id})
supplier = env["res.partner"].search([("name", "=", "Orion Metals LLC"), ("company_id", "in", [False, company.id])], limit=1)
if not supplier:
    supplier = env["res.partner"].create({"name": "Orion Metals LLC", "email": "scar@orion-metals.example", "company_id": company.id})
supplier_alt = env["res.partner"].search([("name", "=", "Beacon Components Supply LLC"), ("company_id", "in", [False, company.id])], limit=1)
if not supplier_alt:
    supplier_alt = env["res.partner"].create({"name": "Beacon Components Supply LLC", "email": "quality@beacon-components.example", "company_id": company.id})

process_specs = [
    ("APEX-LEAD", "Leadership", "management"),
    ("APEX-QMS", "Quality Management", "support"),
    ("APEX-CUST", "Customer Service", "core"),
    ("APEX-SUP", "Purchasing / Supplier Management", "support"),
    ("APEX-REC", "Receiving Inspection", "core"),
    ("APEX-PROD", "Electronics Production", "core"),
    ("APEX-FIN", "Final Electrical Inspection", "core"),
    ("APEX-SHIP", "Shipping", "core"),
    ("APEX-DOC", "Document Control", "support"),
    ("APEX-AUD", "Internal Audit", "support"),
    ("APEX-TRN", "Training & Competency", "support"),
    ("APEX-CAL", "Calibration", "support"),
    ("APEX-ESD", "Electrostatic Discharge Control", "core"),
    ("APEX-SMT", "Surface-Mount Technology Assembly", "core"),
    ("APEX-ASM", "Electrical Component Assembly", "core"),
    ("APEX-ETEST", "Electrical Product Testing", "core"),
    ("APEX-NC", "Nonconforming Product Control", "support"),
    ("APEX-CAPA", "Corrective and Preventive Action", "support"),
    ("APEX-TRACE", "Component and Lot Traceability", "core"),
    ("APEX-RECV", "Supplier Receiving and Incoming Inspection", "core"),
    ("APEX-DISP", "Warehouse Dispatch and Customer Release", "core"),
]
process_site_codes = {
    "APEX-LEAD": ["APEX-HQ"],
    "APEX-QMS": ["APEX-HQ"],
    "APEX-CUST": ["APEX-INS"],
    "APEX-SUP": ["APEX-INS"],
    "APEX-REC": ["APEX-INS"],
    "APEX-PROD": ["APEX-HQ"],
    "APEX-FIN": ["APEX-MFG"],
    "APEX-SHIP": ["APEX-INS"],
    "APEX-DOC": ["APEX-HQ"],
    "APEX-AUD": ["APEX-HQ"],
    "APEX-TRN": ["APEX-HQ"],
    "APEX-CAL": ["APEX-MFG"],
    "APEX-ESD": ["APEX-HQ"],
    "APEX-SMT": ["APEX-HQ"],
    "APEX-ASM": ["APEX-HQ"],
    "APEX-ETEST": ["APEX-MFG"],
    "APEX-NC": ["APEX-MFG", "APEX-INS"],
    "APEX-CAPA": ["APEX-HQ"],
    "APEX-TRACE": ["APEX-INS"],
    "APEX-RECV": ["APEX-INS"],
    "APEX-DISP": ["APEX-INS"],
}
processes = []
for code, name, kind in process_specs:
    proc_model = env["pm.qms.process"] if model_exists("pm.qms.process") else None
    vals = {"code": code, "name": name, "organization_id": organization.id, "company_id": company.id, "description": f"Fictional Apex demo process for {name}.", "process_type": kind}
    if proc_model and "process_type" in proc_model._fields:
        vals["process_type"] = best_selection(proc_model, "process_type", (kind, "core", "support", "management"))
    proc = upsert("pm.qms.process", code=code, name=name, vals=vals)
    if proc:
        if "site_ids" in proc._fields and site_by_code:
            proc.write(
                {
                    "site_ids": [
                        Command.set(
                            [site_by_code[site_code].id for site_code in process_site_codes.get(code, []) if site_code in site_by_code]
                        )
                    ]
                }
            )
        processes.append(proc)

# Mission 19 access is explicit and idempotent. Scope is applied after the
# process/site graph exists so selected-site and selected-process assignments
# can be checked by the same constraints used by the customer-facing UI.
process_by_code = {process.code: process for process in processes}
scope_by_role = {
    "Quality Manager": {"all_sites": True, "all_processes": True},
    "Quality Supervisor": {"site_codes": ["APEX-HQ"], "process_codes": [code for code, sites_for_process in process_site_codes.items() if "APEX-HQ" in sites_for_process]},
    "Document Controller": {"all_sites": True, "all_processes": True},
    "Internal Auditor": {"all_sites": True, "all_processes": True},
    "Process Owner": {"site_codes": ["APEX-HQ", "APEX-MFG"], "process_codes": ["APEX-PROD", "APEX-FIN", "APEX-SMT", "APEX-ASM", "APEX-ETEST"]},
    "Management User": {"all_sites": True, "all_processes": True},
    "QMS Viewer": {"all_sites": True, "all_processes": True},
}
for role, user in users.items():
    scope = scope_by_role[role]
    site_ids = [site_by_code[code].id for code in scope.get("site_codes", []) if code in site_by_code]
    process_ids = [process_by_code[code].id for code in scope.get("process_codes", []) if code in process_by_code]
    user.with_context(pm_qms_demo_seed=True).write(
        {
            "qms_organization_ids": [Command.set([organization.id])],
            "qms_all_sites": scope.get("all_sites", False),
            "qms_site_ids": [Command.set(site_ids)],
            "qms_all_processes": scope.get("all_processes", False),
            "qms_process_ids": [Command.set(process_ids)],
        }
    )

persons = []
role_records = []
person_site_codes = {
    "Quality Manager": "APEX-HQ",
    "Quality Supervisor": "APEX-HQ",
    "Document Controller": "APEX-HQ",
    "Internal Auditor": "APEX-HQ",
    "Process Owner": "APEX-HQ",
    "Management User": "APEX-HQ",
    "QMS Viewer": "APEX-HQ",
}
for full_name, login, role_name in user_specs:
    role = upsert("pm.qms.role", code=role_name.upper().replace(" ", "-")[:30], name=role_name, vals={"name": role_name, "company_id": company.id}, required=False)
    if role:
        role_records.append(role)
    person = upsert(
        "pm.qms.person",
        code=login,
        name=full_name,
        vals={
            "name": full_name,
            "email": login,
            "user_id": users[role_name].id,
            "organization_id": organization.id,
            "company_id": company.id,
            "active": True,
            "site_id": site_by_code.get(person_site_codes.get(role_name)).id
            if site_by_code.get(person_site_codes.get(role_name))
            else False,
        },
        extra_domain=[("email", "=", login)] if model_exists("pm.qms.person") and "email" in env["pm.qms.person"]._fields else None,
        required=False,
    )
    if person:
        persons.append(person)
        if role:
            upsert("pm.qms.person.role.assignment", vals={"person_id": person.id, "role_id": role.id, "organization_id": organization.id, "company_id": company.id, "effective_date": today, "start_date": today}, extra_domain=[("person_id", "=", person.id), ("role_id", "=", role.id), ("effective_date", "=", today)], required=False)

# Older Demo seeds used a temporary demo.qm identity without a primary site.
# Retire that identity and place its historical person record in the HQ scope so
# existing training/qualification records remain readable by the new admin.
legacy_user = env["res.users"].search([("login", "=", "demo.qm@perfectmatch.local")], limit=1)
if legacy_user and legacy_user.id != users["Quality Manager"].id:
    legacy_user.write({"active": False})
legacy_persons = env["pm.qms.person"].search(
    [("organization_id", "=", organization.id), ("site_id", "=", False)]
)
if legacy_persons and site_by_code.get("APEX-HQ"):
    legacy_persons.write({"site_id": site_by_code["APEX-HQ"].id, "active": False})

# Implementation project from the existing Perfect Match Quality Pack.
pack = env["pm.qms.framework.pack"].search([("code", "=", "PM-QMS-QUALITY"), ("state", "=", "active"), ("company_id", "=", company.id)], limit=1) if model_exists("pm.qms.framework.pack") else False
if not pack and model_exists("pm.qms.framework.pack"):
    pack = env["pm.qms.framework.pack"].search([("code", "=", "PM-QMS-QUALITY"), ("state", "=", "active")], limit=1)
project = env["pm.qms.implementation.project"].search([("name", "in", ["Apex Precision QMS Demo Implementation", "Apex Precision Electronics QMS Guided Implementation"]), ("organization_id", "=", organization.id)], limit=1) if model_exists("pm.qms.implementation.project") else False
if pack:
    try:
        # The Odoo shell's env.user is a technical execution identity, not the
        # authorized persona. Keep model ACLs and manager checks active by
        # running this bootstrap workflow as the seeded Quality Manager.
        project = ensure_guided_implementation_project(env["pm.qms.implementation.project"], demo_user, project, {
            "name": "Apex Precision Electronics QMS Guided Implementation",
            "company_id": company.id,
            "organization_id": organization.id,
            "project_manager_id": demo_user.id,
            "date_start": today - relativedelta(days=45),
            "target_date": today + relativedelta(days=75),
            "implementation_type": "migration",
            "pack_ids": pack.ids,
            "create_odoo_project": True,
            "notes": "Fictional guided implementation for Apex Precision Electronics using only original Perfect Match control content; no external copyrighted standard text is copied.",
        })
    except Exception as exc:
        raise RuntimeError("Guided implementation project generation failed") from exc
if not project:
    raise RuntimeError("Required guided implementation project or Quality Pack is missing")
if project:
    try:
        if project.name != "Apex Precision Electronics QMS Guided Implementation":
            project.write({"name": "Apex Precision Electronics QMS Guided Implementation"})
        project.with_user(demo_user).action_sync_framework()
    except Exception as exc:
        raise RuntimeError("Guided implementation framework synchronization failed") from exc
    if model_exists("pm.qms.implementation.control") and not env["pm.qms.implementation.control"].search_count([("implementation_project_id", "=", project.id)]):
        raise RuntimeError("Guided implementation project has no synchronized framework controls")
    readiness_center = env["pm.qms.readiness.center"].search([("implementation_project_id", "=", project.id)], limit=1) if model_exists("pm.qms.readiness.center") else False
    if readiness_center:
        readiness_center.action_refresh()
    elif model_exists("pm.qms.readiness.center"):
        readiness_center = env["pm.qms.readiness.center"].create({"implementation_project_id": project.id})
    assessment = env["pm.qms.readiness.assessment"].search([("implementation_project_id", "=", project.id), ("name", "=", "Apex guided implementation readiness snapshot")], limit=1) if model_exists("pm.qms.readiness.assessment") else False
    if not assessment and model_exists("pm.qms.readiness.assessment"):
        assessment = env["pm.qms.readiness.assessment"].create({"name": "Apex guided implementation readiness snapshot", "implementation_project_id": project.id, "assessment_date": today, "assessor_id": demo_user.id, "notes": "Fictional readiness snapshot for guided demonstration; incomplete items point to synthetic evidence and activities."})
    if assessment and assessment.state == "draft":
        try:
            assessment.with_user(demo_user).action_complete_assessment()
        except Exception as exc:
            raise RuntimeError("Guided implementation readiness assessment failed") from exc

controls = env["pm.qms.control"].search([("company_id", "=", company.id)], limit=6) if model_exists("pm.qms.control") else env["ir.model"].browse()
control_instances = []
for index, proc in enumerate(processes[:6], start=1):
    control = upsert("pm.qms.control", code=f"APEX-CTRL-{index:03d}", name=f"Apex demo control {index}: {proc.name}", vals={"organization_id": organization.id, "company_id": company.id, "process_id": proc.id, "objective": f"Demonstrate control ownership and evidence for {proc.name}."}, required=False)
    if control:
        call(control, "action_activate")
        ci = upsert("pm.qms.control.instance", code=f"APEX-CI-{index:03d}", name=f"{proc.name} control instance", vals={"control_id": control.id, "organization_id": organization.id, "company_id": company.id, "process_id": proc.id, "owner_id": demo_user.id}, required=False)
        if ci:
            control_instances.append(ci)
        upsert("pm.qms.activity", code=f"APEX-ACT-{index:03d}", name=f"Collect evidence for {proc.name}", vals={"organization_id": organization.id, "company_id": company.id, "control_id": control.id, "process_id": proc.id, "owner_id": demo_user.id, "target_date": [overdue, due_today, due_soon][index % 3], "description": "Source-driven fictional implementation activity for Action Center."}, required=False)

if controls and model_exists("pm.qms.external.mapping"):
    upsert_by_identity("pm.qms.external.mapping", [("control_id", "=", controls[0].id), ("standard_name", "=", "Customer drawing requirement"), ("edition", "=", "APEX-2026"), ("reference", "=", "CUST-DWG-EL-014")], {"control_id": controls[0].id, "standard_name": "Customer drawing requirement", "edition": "APEX-2026", "reference": "CUST-DWG-EL-014", "note": "Fictional customer requirement identifier mapped to the internal inspection control; no third-party text is included."})

# Documents, revisions, evidence, and acknowledgments.
document_specs = [
    ("APEX-DOC-001", "Quality Policy", "APEX-LEAD"),
    ("APEX-DOC-002", "Quality Manual / QMS Overview", "APEX-QMS"),
    ("APEX-DOC-003", "SOP - Control of Nonconforming Electrical Product", "APEX-NC"),
    ("APEX-DOC-004", "SOP - Document Control", "APEX-DOC"),
    ("APEX-DOC-005", "Work Instruction - Final Electrical Inspection", "APEX-FIN"),
    ("APEX-DOC-006", "Form - Test Equipment Verification", "APEX-CAL"),
    ("APEX-DOC-007", "Procedure - ESD Protected Area and Handling", "APEX-ESD"),
    ("APEX-DOC-008", "Procedure - Supplier Receiving and Inspection", "APEX-RECV"),
    ("APEX-DOC-009", "Work Instruction - SMT Solder Paste and Reflow", "APEX-SMT"),
    ("APEX-DOC-010", "Procedure - Electrical Functional Test", "APEX-ETEST"),
    ("APEX-DOC-011", "Procedure - Component and Lot Traceability", "APEX-TRACE"),
    ("APEX-DOC-012", "Procedure - Nonconforming Product and CAPA", "APEX-CAPA"),
    ("APEX-DOC-013", "Procedure - Internal Audit and Follow-up", "APEX-AUD"),
]
documents = []
revisions = []
for code, title, process_code in document_specs:
    proc = next((p for p in processes if p.code == process_code), processes[0] if processes else False)
    doc = upsert("pm.qms.document", code=code, name=title, vals={"organization_id": organization.id, "company_id": company.id, "process_id": proc.id if proc else False, "owner_id": demo_user.id, "document_type": best_selection(env["pm.qms.document"], "document_type", ("procedure", "policy", "form")) if model_exists("pm.qms.document") and "document_type" in env["pm.qms.document"]._fields else False, "description": f"Original fictional Apex document for demo: {title}."}, required=False)
    if doc:
        documents.append(doc)
        rev = upsert("pm.qms.document.revision", vals={"document_id": doc.id, "revision": "A", "version": "A", "title": title, "content": f"Fictional guided example for {title}: purpose, owner, required inputs, acceptance evidence, and escalation path. No copyrighted standards text is included.", "effective_date": today - relativedelta(days=20), "review_date": [next_month, next_month, due_soon, today + relativedelta(days=45)][len(documents) % 4], "change_summary": "Initial controlled Demo revision with synthetic process-specific instructions.", "owner_id": demo_user.id}, extra_domain=[("document_id", "=", doc.id), ("revision", "=", "A")], required=False)
        if rev:
            revisions.append(rev)
        ci = control_instances[(len(documents) - 1) % len(control_instances)] if control_instances else False
        req = upsert("pm.qms.evidence.requirement", code=f"APEX-REQ-{code[-3:]}", name=f"Required evidence - {title}", vals={"organization_id": organization.id, "company_id": company.id, "process_id": proc.id if proc else False, "control_id": ci.control_id.id if ci else (controls[:1].id if controls else False), "control_instance_id": ci.id if ci else False, "description": f"Required evidence demo item for {title}."}, required=False)
        upsert("pm.qms.evidence", code=f"APEX-EV-{code[-3:]}", name=f"Evidence - {title}", vals={"organization_id": organization.id, "company_id": company.id, "process_id": proc.id if proc else False, "document_id": doc.id, "control_instance_id": ci.id if ci else False, "evidence_requirement_id": req.id if req else False, "owner_id": demo_user.id, "evidence_date": today - relativedelta(days=5), "description": f"Synthetic evidence reference EV-{code[-3:]}: inspection checklist, test log, calibration record, or traceability sample linked to {title}. No real customer data or binary photographs."}, required=False)

# Use the document workflow actions to create review and approval history.
for document in documents:
    revision = document.revision_ids.filtered(lambda item: item.revision == "A")[:1]
    if not revision:
        continue
    if revision.state == "draft":
        document.with_user(demo_user).action_submit_for_review()
    if revision.state == "under_review":
        document.with_user(demo_user).action_approve()
    if revision.state == "approved":
        revision.with_user(demo_user).action_activate()

# Risk, NCR, CAPA, audit, KPI, and performance.
risk_open = upsert("pm.qms.risk", code="APEX-RISK-001", name="Single-source supplier continuity risk", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-SUP"), processes[0].id), "owner_id": users["Quality Supervisor"].id, "description": "Fictional risk: critical alloy depends on one approved supplier.", "cause": "Limited approved supplier base.", "potential_effect": "Production interruption and customer delivery risk.", "mitigation_plan": "Qualify an alternate supplier and increase incoming certificate review.", "target_date": overdue, "review_date": due_soon, "likelihood": 3, "impact": 4}, required=False)
risk_monitor = upsert("pm.qms.risk", code="APEX-RISK-002", name="Controlled final inspection capacity risk", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": users["Process Owner"].id, "description": "Fictional monitored risk: inspection queue grows during peak demand.", "mitigation_plan": "Cross-train backup inspectors and monitor weekly queue aging.", "target_date": due_soon, "review_date": next_month, "likelihood": 2, "impact": 3}, required=False)
risk_specs = [
    ("APEX-RISK-003", "ESD damage to sensitive controller components", "APEX-ESD", "Grounding or packaging lapse can cause latent electrical failure.", "Verify wrist straps each shift and audit ESD packaging at receiving."),
    ("APEX-RISK-004", "Counterfeit power-management component", "APEX-SUP", "Unapproved sourcing may introduce counterfeit ICs.", "Use approved sources, lot certificates, and enhanced incoming sampling."),
    ("APEX-RISK-005", "Solder joint outside process window", "APEX-SMT", "Paste volume or reflow drift can create intermittent joints.", "Review profile records and verify first-piece solder joints per lot."),
    ("APEX-RISK-006", "Electrical test equipment overdue for calibration", "APEX-CAL", "A measurement system out of tolerance could release defective product.", "Quarantine equipment and assess all affected test results."),
    ("APEX-RISK-007", "Loss of component-to-finished-unit traceability", "APEX-TRACE", "Incomplete lot linkage may delay containment and customer response.", "Reconcile receiving lots, work orders, serials, and dispatch records."),
    ("APEX-RISK-008", "Intermittent failure escapes functional test", "APEX-ETEST", "Insufficient soak or sampling may miss temperature-sensitive faults.", "Trend retest failures and review test coverage quarterly."),
]
demo_risks = {}
for index, (code, title, process_code, cause, mitigation) in enumerate(risk_specs, start=1):
    process = process_by_code.get(process_code)
    demo_risks[code] = upsert("pm.qms.risk", code=code, name=title, vals={"organization_id": organization.id, "company_id": company.id, "process_id": process.id if process else processes[0].id, "owner_id": users["Quality Supervisor"].id if index % 2 else users["Process Owner"].id, "description": f"Fictional Apex electronics scenario: {title.lower()}.", "cause": cause, "potential_effect": "Potential customer impact, containment effort, and delivery disruption.", "mitigation_plan": mitigation, "target_date": [overdue, due_soon, next_month][index % 3], "review_date": due_soon, "likelihood": 2 + (index % 3), "impact": 3 + (index % 2)}, required=False)

ncr = upsert("pm.qms.nonconformity", code="APEX-NCR-001", name="Electrical safety test below acceptance window on Lot L-24017", vals={"organization_id": organization.id, "process_id": next((p.id for p in processes if p.code == "APEX-ETEST"), processes[0].id), "source_type": "internal", "description": "Final electrical test detected an intermittent insulation-resistance result outside the fictional Apex acceptance window on Lot L-24017.", "detected_date": today - relativedelta(days=9), "owner_id": users["Quality Supervisor"].id, "severity": "major", "containment_required": True, "containment_action": "Hold Lot L-24017, preserve test logs, and retest related units using the current approved instruction.", "containment_owner_id": users["Quality Supervisor"].id, "containment_date": today - relativedelta(days=8), "containment_completed": True, "disposition": "rework", "disposition_notes": "Fictional demo disposition: rework and repeat electrical safety/function tests.", "root_cause_summary": "Test-instruction revision at point of use was not reconciled with the released test configuration.", "target_date": overdue}, required=False)
ncr_solder = upsert("pm.qms.nonconformity", code="APEX-NCR-002", name="Solder wetting below acceptance criteria on Lot SMT-2609", vals={"organization_id": organization.id, "process_id": process_by_code.get("APEX-SMT", processes[0]).id, "source_type": "internal", "description": "Fictional first-article inspection found incomplete solder wetting on a controller board; lot held pending profile review.", "detected_date": today - relativedelta(days=3), "owner_id": users["Quality Supervisor"].id, "severity": "major", "containment_required": True, "containment_action": "Quarantine the affected reel and boards; inspect adjacent production lots.", "containment_owner_id": users["Quality Supervisor"].id, "containment_date": today - relativedelta(days=2), "containment_completed": True, "disposition": "rework", "disposition_notes": "Fictional controlled rework after engineering review and electrical retest.", "root_cause_summary": "Reflow profile drift combined with incomplete first-piece verification.", "target_date": due_soon}, required=False)

capa = upsert("pm.qms.capa", code="APEX-CAPA-001", name="Intermittent electrical failure linked to test-instruction revision", vals={"organization_id": organization.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": demo_user.id, "source_type": "ncr", "source_reference": "APEX-NCR-001 / Lot L-24017", "source_ncr_id": ncr.id if ncr else False, "problem_statement": "Fictional electrical failure escaped because point-of-use test instructions were not reconciled after revision.", "root_cause_method": "5why", "root_cause_analysis": "5 Why analysis links inconsistent test setup and missing revision reconciliation.", "root_cause": "Document release and electrical test configuration were not synchronized.", "action_plan": "Withdraw obsolete copies, retrain technicians, and add a revision check to first-piece release.", "action_owner_id": demo_user.id, "target_date": due_soon, "effectiveness_required": True, "effectiveness_review_date": due_soon + relativedelta(days=21)}, required=False)
if capa:
    for seq, answer in enumerate(["Insulation-resistance readings varied at final electrical test.", "The station setup did not match the current approved revision.", "Point-of-use instructions were not reconciled after the revision release.", "Document control checks omitted verification at the electrical test cell.", "The release workflow did not require recorded revision confirmation."], start=1):
        upsert_capa_why(capa, seq, answer)
    upsert("pm.qms.capa.action", name="Remove obsolete setup instructions", vals={"capa_id": capa.id, "owner_id": users["Document Controller"].id, "target_date": today - relativedelta(days=2), "description": "Remove superseded point-of-use copies from Final Inspection."}, required=False)
    upsert("pm.qms.capa.action", name="Train inspectors on revised setup instruction", vals={"capa_id": capa.id, "owner_id": users["Quality Supervisor"].id, "target_date": due_today, "description": "Complete refresher training for final inspection team."}, required=False)

# Guided second CAPA demonstrates a genuine analysis-in-progress workflow.
capa_solder = upsert("pm.qms.capa", code="APEX-CAPA-002", name="Reflow profile drift and incomplete solder wetting", vals={"organization_id": organization.id, "process_id": process_by_code.get("APEX-SMT", processes[0]).id, "owner_id": users["Quality Supervisor"].id, "source_type": "ncr", "source_reference": "APEX-NCR-002 / Lot SMT-2609", "source_ncr_id": ncr_solder.id if ncr_solder else False, "problem_statement": "Fictional solder-wetting nonconformity requires cause analysis across paste handling, reflow profile, and first-piece inspection.", "root_cause_method": "fishbone", "root_cause_analysis": "Investigation is in progress; the potential contributors below are evidence-linked hypotheses.", "action_plan": "Confirm the thermal profile, verify paste controls, and update first-piece checks.", "action_owner_id": users["Quality Supervisor"].id, "target_date": due_soon, "effectiveness_required": True, "effectiveness_review_date": next_month}, required=True)
if capa_solder and capa_solder.state == "draft":
    try:
        capa_solder.with_user(demo_user).action_start_analysis()
    except Exception as exc:
        raise RuntimeError("Required CAPA analysis workflow failed for APEX-CAPA-002") from exc
if capa_solder and model_exists("pm.qms.capa.fishbone"):
    for category, cause in [
        ("machine_equipment", "Reflow oven thermal profile may have drifted from the approved window."),
        ("material_inputs", "Solder paste exposure time may not have been consistently recorded."),
        ("method_process", "First-piece solder-wetting review may not have covered the affected joint family."),
        ("measurement_data", "The inspection sample may not have represented the intermittent failure mode."),
    ]:
        upsert_by_identity("pm.qms.capa.fishbone", [("capa_id", "=", capa_solder.id), ("category", "=", category)], {"capa_id": capa_solder.id, "category": category, "potential_cause": cause, "evidence_basis": "Fictional investigation lead linked to the lot, reflow record, or inspection sample; not a real customer record.", "investigation_status": "confirmed" if category == "machine_equipment" else "investigating", "rationale_finding": "Synthetic reflow trend and lot sample indicate a profile shift immediately preceded the solder-wetting finding." if category == "machine_equipment" else False})
if capa_solder and model_exists("pm.qms.capa.is.is.not") and capa_solder.state == "analysis":
    fixed_is_is_not = {
        "what": ("Solder wetting on controller boards", "Other joints on unaffected board families", "Affected boards share Lot SMT-2609", "The reflow profile changed before the lot"),
        "where": ("SMT line 1 reflow output", "Hand-solder repair bench", "Only the reflowed joint family is affected", "Oven zone verification was deferred"),
        "when": ("After the profile adjustment on the current shift", "Lots built before the adjustment", "Failure reports begin with the new lot", "Profile and first-piece review sequence changed"),
        "extent": ("A sample of boards from one production lot", "Other released lots under prior profile", "Failures cluster by lot and joint location", "Sampling did not include a profile-change trigger"),
    }
    for sequence, (dimension, values) in enumerate(fixed_is_is_not.items(), start=1):
        upsert_by_identity("pm.qms.capa.is.is.not", [("capa_id", "=", capa_solder.id), ("dimension", "=", dimension)], {"capa_id": capa_solder.id, "dimension": dimension, "sequence": sequence, "is_value": values[0], "is_not_value": values[1], "distinction": values[2], "change_value": values[3]})
    if capa_solder.root_cause_method != "fishbone":
        capa_solder.with_user(demo_user).write({"root_cause_method": "fishbone"})
    if capa_solder.state == "analysis" and not capa_solder.root_cause:
        capa_solder.with_user(demo_user).write({"root_cause": "Reflow profile adjustment was not followed by a documented first-piece verification sample."})
    if capa_solder.state == "analysis" and capa_solder.root_cause:
        capa_solder.with_user(demo_user).action_plan_actions()
    capa_action = upsert_by_identity("pm.qms.capa.action", [("capa_id", "=", capa_solder.id), ("name", "=", "Verify reflow profile and paste exposure record")], {"capa_id": capa_solder.id, "name": "Verify reflow profile and paste exposure record", "owner_id": users["Quality Supervisor"].id, "target_date": due_soon, "description": "Compare approved thermal limits with the fictional run record and check paste exposure documentation."}, required=True)
    if capa_action and capa_action.status == "open":
        capa_action.with_user(demo_user).action_start()
    if capa_solder.state == "action_planned":
        capa_solder.with_user(demo_user).action_start_implementation()

# A fully closed CAPA demonstrates the auditable end-to-end workflow without
# mutating either of the canonical cost-linked cases.
capa_closed = upsert("pm.qms.capa", code="APEX-CAPA-003", name="ESD handling refresher and verification", vals={"organization_id": organization.id, "process_id": process_by_code.get("APEX-ESD", processes[0]).id, "owner_id": users["Quality Supervisor"].id, "source_type": "risk", "source_reference": "APEX-RISK-003 / ESD handling observation", "source_risk_id": demo_risks.get("APEX-RISK-003").id if demo_risks.get("APEX-RISK-003") else False, "problem_statement": "Fictional ESD handling observation requires refresher training and documented verification.", "root_cause_method": "5why", "root_cause_analysis": "A 5 Why review found the shift handover checklist did not confirm the daily ESD verification.", "root_cause": "The verification handover was not assigned to a named role on each shift.", "action_plan": "Assign a shift verification owner and complete a documented refresher.", "action_owner_id": users["Quality Supervisor"].id, "target_date": today - relativedelta(days=2), "effectiveness_required": True, "effectiveness_review_date": today - relativedelta(days=1), "related_document_ids": [Command.set([documents[6].id])] if len(documents) > 6 else []}, required=True)
if capa_closed and capa_closed.state == "draft":
    for sequence, answer in enumerate(["ESD verification was not recorded.", "Shift handover omitted the check.", "The checklist did not name the responsible role.", "Ownership varied between production shifts.", "The procedure lacked an explicit handover assignment."], start=1):
        upsert_capa_why(capa_closed, sequence, answer)
    capa_closed.with_user(demo_user).action_start_analysis()
if capa_closed and capa_closed.state == "analysis":
    capa_closed.with_user(demo_user).action_plan_actions()
if capa_closed and capa_closed.state == "action_planned":
    closed_action = upsert_by_identity("pm.qms.capa.action", [("capa_id", "=", capa_closed.id), ("name", "=", "Assign ESD shift owner and complete refresher")], {"capa_id": capa_closed.id, "name": "Assign ESD shift owner and complete refresher", "owner_id": users["Quality Supervisor"].id, "target_date": today - relativedelta(days=1), "description": "Fictional completed action: publish the named shift owner and retain refresher attendance evidence."}, required=True)
    capa_closed.with_user(demo_user).action_start_implementation()
    if closed_action and closed_action.status == "open":
        closed_action.with_user(demo_user).action_start()
    if closed_action and closed_action.status == "in_progress":
        closed_action.with_user(demo_user).action_complete()
    if closed_action and closed_action.status == "completed":
        closed_action.with_user(demo_user).action_verify()
    if closed_action and closed_action.status == "verified":
        capa_closed.with_user(demo_user).action_complete_implementation()
if capa_closed and capa_closed.state == "effectiveness_review":
    if not capa_closed.effectiveness_notes:
        capa_closed.with_user(demo_user).write({"effectiveness_notes": "Synthetic follow-up sample confirmed the assigned ESD shift check was completed on each reviewed shift."})
    capa_closed.with_user(demo_user).action_mark_effective()
if capa_closed and capa_closed.state == "effective":
    capa_closed.with_user(demo_user).action_close()

program = upsert("pm.qms.audit.program", code="APEX-AUD-PROG-2026", name="Apex 2026 Internal Audit Program", vals={"organization_id": organization.id, "company_id": company.id, "owner_id": users["Internal Auditor"].id, "year": today.year, "description": "Fictional annual internal audit program for the product demo."}, required=False)
audit = upsert("pm.qms.audit", code="APEX-AUD-001", name="Document control and final inspection audit", vals={"program_id": program.id if program else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-DOC"), processes[0].id), "lead_auditor_id": users["Internal Auditor"].id, "owner_id": users["Internal Auditor"].id, "planned_date": today - relativedelta(days=5), "audit_date": today - relativedelta(days=4), "scope": "Document release, floor copy control, and final inspection evidence.", "criteria": "Perfect Match proprietary QMS controls and Apex internal procedures."}, required=False)
finding = upsert("pm.qms.audit.finding", code="APEX-AF-001", name="Floor copy reconciliation not consistently evidenced", vals={"audit_id": audit.id if audit else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-DOC"), processes[0].id), "owner_id": users["Document Controller"].id, "title": "Floor copy reconciliation not consistently evidenced", "classification": "nonconformity", "objective_evidence": "Fictional objective evidence: floor copy reconciliation was missing for one released setup instruction.", "description": "Fictional actionable finding from the internal audit.", "severity": "minor", "due_date": overdue}, required=False)
upsert("pm.qms.audit.finding", code="APEX-AF-002", name="Training roster evidence closed", vals={"audit_id": audit.id if audit else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-TRN"), processes[0].id), "owner_id": users["Quality Manager"].id, "title": "Training roster evidence closed", "classification": "observation", "objective_evidence": "Fictional objective evidence: prior training roster review was completed.", "description": "Fictional closed audit finding retained for trend context.", "due_date": today - relativedelta(days=30)}, required=False)

if audit:
    audit_scope = upsert_by_identity("pm.qms.audit.scope", [("audit_id", "=", audit.id), ("process_id", "=", process_by_code.get("APEX-SMT", processes[0]).id)], {"audit_id": audit.id, "organization_id": organization.id, "process_id": process_by_code.get("APEX-SMT", processes[0]).id, "description": "SMT process, solder paste controls, reflow records, and first-piece verification."}, required=True)
    upsert_by_identity("pm.qms.audit.plan.line", [("audit_id", "=", audit.id), ("activity", "=", "Sample SMT lot and reflow evidence")], {"audit_id": audit.id, "organization_id": organization.id, "planned_datetime": now, "duration": 1.5, "process_id": process_by_code.get("APEX-SMT", processes[0]).id, "activity": "Sample SMT lot and reflow evidence", "auditor_id": users["Internal Auditor"].id, "auditee_id": users["Process Owner"].id, "notes": "Guided audit step: follow a sampled lot from receiving through electrical test."}, required=True)
    audit_control = control_instances[0] if control_instances else False
    criterion = upsert_by_identity("pm.qms.audit.criterion", [("audit_id", "=", audit.id), ("name", "=", "Approved internal work instruction is used")], {"audit_id": audit.id, "organization_id": organization.id, "name": "Approved internal work instruction is used", "criterion_type": "company_procedure", "control_instance_id": audit_control.id if audit_control else False, "reference": "APEX-DOC-009 revision A", "description": "Verify controlled revision at point of use; no external standard text is reproduced."}, required=True)
    upsert_by_identity("pm.qms.audit.evidence", [("audit_id", "=", audit.id), ("name", "=", "Fictional reflow record sample")], {"audit_id": audit.id, "criterion_id": criterion.id if criterion else False, "name": "Fictional reflow record sample", "source": "record_sample", "description": "Synthetic record reference RFL-2609-014; temperature profile reviewed against internal limits.", "document_id": documents[8].id if len(documents) > 8 else False, "control_instance_id": audit_control.id if audit_control else False, "collected_date": today - relativedelta(days=2)}, required=True)

objective = upsert("pm.qms.objective", code="APEX-OBJ-001", name="Reduce dimensional escapes", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": demo_user.id, "target_value": 98.0, "unit": "%", "target_date": next_month, "description": "Improve right-first-time dimensional acceptance for fictional Apex shipments."}, required=False)
kpi = upsert("pm.qms.kpi", code="APEX-KPI-001", name="First-pass final inspection yield", vals={"objective_id": objective.id if objective else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": demo_user.id, "target_value": 98.0, "unit": "%", "description": "Monthly fictional first-pass yield trend."}, required=False)
for months_back, value in [(3, 94.8), (2, 96.1), (1, 97.0), (0, 96.4)]:
    period_start = (scenario_as_of.replace(day=1) - relativedelta(months=months_back))
    period_end = period_start + relativedelta(months=1, days=-1)
    upsert("pm.qms.kpi.measurement", vals={"kpi_id": kpi.id if kpi else False, "organization_id": organization.id, "company_id": company.id, "measurement_date": period_end, "period_start": period_start, "period_end": period_end, "source_type": "manual", "value": value, "notes": "Fictional trend value for demo analytics."}, extra_domain=[("kpi_id", "=", kpi.id if kpi else 0), ("period_start", "=", period_start), ("period_end", "=", period_end)], required=False)
additional_kpis = [
    ("APEX-KPI-002", "Incoming component rejection rate", "APEX-RECV", 2.0, "%", [3.4, 2.8, 2.1, 2.6]),
    ("APEX-KPI-003", "SMT first-pass yield", "APEX-SMT", 97.0, "%", [93.2, 95.1, 96.4, 95.8]),
    ("APEX-KPI-004", "Electrical test pass rate", "APEX-ETEST", 98.0, "%", [97.4, 98.1, 98.6, 97.9]),
    ("APEX-KPI-005", "Supplier on-time delivery", "APEX-SUP", 95.0, "%", [90.0, 92.0, 95.0, 93.0]),
    ("APEX-KPI-006", "Open nonconformities", "APEX-NC", 0.0, "count", [4.0, 3.0, 2.0, 2.0]),
    ("APEX-KPI-007", "CAPA actions overdue", "APEX-CAPA", 0.0, "count", [3.0, 2.0, 2.0, 1.0]),
    ("APEX-KPI-008", "Customer satisfaction", "APEX-CUST", 90.0, "%", [84.0, 87.0, 89.0, 86.0]),
]
for code, title, process_code, target, unit, values in additional_kpis:
    metric = upsert("pm.qms.kpi", code=code, name=title, vals={"objective_id": objective.id if objective else False, "organization_id": organization.id, "company_id": company.id, "process_id": process_by_code.get(process_code, processes[0]).id, "owner_id": demo_user.id, "target_value": target, "unit": unit, "description": f"Fictional four-period trend for {title.lower()}, linked to the relevant QMS process."}, required=False)
    for months_back, value in zip((3, 2, 1, 0), values):
        period_start = scenario_as_of.replace(day=1) - relativedelta(months=months_back)
        period_end = period_start + relativedelta(months=1, days=-1)
        upsert("pm.qms.kpi.measurement", vals={"kpi_id": metric.id if metric else False, "organization_id": organization.id, "company_id": company.id, "measurement_date": period_end, "period_start": period_start, "period_end": period_end, "source_type": "manual", "value": value, "notes": "Synthetic KPI demonstration point; not a real operating result."}, extra_domain=[("kpi_id", "=", metric.id if metric else 0), ("period_start", "=", period_start), ("period_end", "=", period_end)], required=False)
# Customer/supplier period scorecards are reconciled once below on stable
# customer/supplier + organization identities.

# People, training, qualifications, acknowledgments.
competency = upsert("pm.qms.competency", code="APEX-COMP-001", name="Electrical Inspection and Test Competency", vals={"company_id": company.id, "category": "Electrical Quality", "description": "Qualification to perform electrical inspection, verify test setup, preserve results, and escalate out-of-specification findings."}, required=False)
course = upsert("pm.qms.training.course", code="APEX-TRN-001", name="Electrical Test Revision and ESD Refresher", vals={"company_id": company.id, "description": "Fictional refresher showing course definition, competency linkage, event attendance, and follow-up record.", "training_type": "refresher", "validity_months": 12, "competency_ids": [Command.set([competency.id])] if competency else []}, required=False)
qtype = upsert("pm.qms.qualification.type", code="APEX-QUAL-001", name="Final Inspection Authorization", vals={"company_id": company.id, "description": "Fictional qualification for final inspection release authority."}, required=False)
training_event = upsert("pm.qms.training.event", name="Electrical Test Revision Refresher - Session 01", vals={"course_id": course.id if course else False, "organization_id": organization.id, "event_date": today - relativedelta(days=12), "instructor": "Apex Quality Engineering (fictional)", "delivery_method": "on_the_job", "location": "Manufacturing Plant / Electrical Test Laboratory", "state": "completed", "notes": "Synthetic training event; participant results are held in separate person training records."}, extra_domain=[("course_id", "=", course.id if course else 0), ("name", "=", "Electrical Test Revision Refresher - Session 01")], required=False)
for role in role_records:
    if competency and role.name in ("Quality Supervisor", "Process Owner", "Internal Auditor"):
        upsert_by_identity("pm.qms.role.competency.requirement", [("role_id", "=", role.id), ("competency_id", "=", competency.id)], {"role_id": role.id, "competency_id": competency.id, "required": True, "valid_months": 12, "notes": "Fictional role qualification requirement for electrical inspection and test evidence."})
    if course and role.name in ("Quality Supervisor", "Process Owner"):
        upsert_by_identity("pm.qms.training.requirement", [("role_id", "=", role.id), ("course_id", "=", course.id)], {"role_id": role.id, "course_id": course.id, "required": True, "due_within_days": 30, "notes": "Complete the revision and ESD refresher before assigned production work."})
for idx, person in enumerate(persons):
    upsert("pm.qms.competency.assessment", vals={"person_id": person.id, "competency_id": competency.id if competency else False, "organization_id": organization.id, "company_id": company.id, "assessment_date": today - relativedelta(days=10), "result": "gap" if idx in (1, 4) else "competent", "level": "Observed practical demonstration", "valid_until": next_month + relativedelta(months=11), "notes": "Fictional competency evidence; supervisors review gaps before authorization."}, extra_domain=[("person_id", "=", person.id), ("competency_id", "=", competency.id if competency else 0), ("assessment_date", "=", today - relativedelta(days=10))], required=False)
    training_result = "satisfactory" if idx in (0, 2, 5) else "not_completed"
    upsert("pm.qms.training.record", vals={"person_id": person.id, "course_id": course.id if course else False, "event_id": training_event.id if training_event and training_result == "satisfactory" else False, "organization_id": organization.id, "company_id": company.id, "due_date": [overdue, due_today, due_soon, next_month][idx % 4], "completion_date": today - relativedelta(days=12) if training_result == "satisfactory" else False, "result": training_result, "provider": "Apex Quality Engineering (fictional)", "notes": "Fictional training record: completion, pending refresher, due date, and follow-up are demonstrated without real personnel data."}, extra_domain=training_identity_domain(person.id, course.id if course else 0, organization.id, company.id), required=False)
    upsert("pm.qms.qualification.record", vals={"person_id": person.id, "qualification_type_id": qtype.id if qtype else False, "organization_id": organization.id, "company_id": company.id, "identifier": f"APEX-Q-{idx + 1:03d}", "issuer": "Apex Quality Engineering (fictional)", "issue_date": today - relativedelta(months=10), "expiration_date": [overdue, due_soon, next_month, today + relativedelta(months=6)][idx % 4], "notes": "Fictional qualification demonstrating current, soon-due, and expired states."}, extra_domain=qualification_identity_domain(person.id, qtype.id if qtype else 0, organization.id, company.id), required=False)
if revisions and persons:
    upsert("pm.qms.document.acknowledgment", vals={"revision_id": revisions[2].id, "document_id": documents[2].id if len(documents) > 2 else False, "person_id": persons[2].id if len(persons) > 2 else persons[0].id, "organization_id": organization.id, "company_id": company.id, "due_date": due_today}, extra_domain=[("revision_id", "=", revisions[2].id), ("person_id", "=", persons[2].id if len(persons) > 2 else persons[0].id)], required=False)

# Calibration and OOT.
etype = upsert("pm.qms.equipment.type", code="APEX-EQTYPE-001", name="Electrical test and monitoring equipment", vals={"company_id": company.id, "description": "Fictional type for electrical test, ESD, and assembly verification instruments."}, required=False)
provider = upsert("pm.qms.calibration.provider", code="APEX-CAL-PROV-001", name="Metro Calibration Labs", vals={"company_id": company.id, "partner_id": supplier.id, "description": "Fictional external calibration provider."}, required=False)
equipment_records = []
for code, name, status_date, eq_site, eq_process in [
    ("EQ-0001", "Electrical Safety Analyzer", overdue, "APEX-MFG", "APEX-ETEST"),
    ("EQ-0002", "Bench Multimeter", due_soon, "APEX-MFG", "APEX-CAL"),
    ("EQ-0003", "ESD Surface Resistance Meter", next_month, "APEX-HQ", "APEX-ESD"),
    ("EQ-0004", "SMT Torque Driver", due_today, "APEX-HQ", "APEX-SMT"),
    ("EQ-0005", "Digital Oscilloscope", next_month, "APEX-MFG", "APEX-ETEST"),
]:
    eq = upsert("pm.qms.equipment", code=code, name=name, vals={"organization_id": organization.id, "company_id": company.id, "site_id": site_by_code.get(eq_site).id if site_by_code.get(eq_site) else False, "process_id": process_by_code.get(eq_process, processes[0]).id, "type_id": etype.id if etype else False, "responsible_person_id": persons[1].id if len(persons) > 1 else False, "calibration_required": True, "next_due_date": status_date, "frequency_interval": 90, "default_provider_id": provider.id if provider else False, "purpose": f"Fictional {name} used for {process_by_code.get(eq_process, processes[0]).name} verification.", "notes": "Synthetic equipment record demonstrating overdue, due-soon, due-today, and current calibration states."}, required=False)
    if eq:
        equipment_records.append(eq)
cal_event = upsert("pm.qms.calibration.event", code="APEX-CAL-EVT-001", name="Electrical safety analyzer failed calibration", vals={"equipment_id": equipment_records[0].id if equipment_records else False, "organization_id": organization.id, "company_id": company.id, "provider_id": provider.id if provider else False, "calibration_date": today - relativedelta(days=2), "result": best_selection(env["pm.qms.calibration.event"], "result", ("out_of_tolerance", "fail", "failed")) if model_exists("pm.qms.calibration.event") and "result" in env["pm.qms.calibration.event"]._fields else False, "notes": "Fictional OOT scenario for Lot L-24017 and electrical test record ETR-0087."}, required=False)
if cal_event:
    for parameter, measured, lower, upper, result in [
        ("DC voltage reference", "5.12 V", "4.95 V", "5.05 V", "fail"),
        ("AC frequency reference", "60.01 Hz", "59.90 Hz", "60.10 Hz", "pass"),
        ("Resistance reference", "1.002 kOhm", "0.990 kOhm", "1.010 kOhm", "pass"),
    ]:
        upsert_by_identity("pm.qms.calibration.measurement.line", [("event_id", "=", cal_event.id), ("parameter", "=", parameter)], {"event_id": cal_event.id, "parameter": parameter, "nominal_value": "Traceable laboratory reference", "lower_limit": lower, "upper_limit": upper, "as_found_value": measured, "as_left_value": "Adjusted or quarantined per fictional procedure", "result": result, "notes": "Synthetic measurement values for the isolated Demo scenario."})
impact = upsert("pm.qms.calibration.impact.assessment", code="APEX-OOT-001", name="Electrical safety analyzer OOT impact assessment", vals={"equipment_id": equipment_records[0].id if equipment_records else False, "event_id": cal_event.id if cal_event else False, "organization_id": organization.id, "company_id": company.id, "assessor_person_id": persons[0].id if persons else False, "impact_summary": "Fictional impact review for Lot L-24017 and electrical test record ETR-0087.", "risk_level": "high", "target_date": due_today}, required=False)
upsert("pm.qms.calibration.affected.reference", name="Lot L-24017 / IR-0087", vals={"assessment_id": impact.id if impact else False, "reference": "Lot L-24017", "description": "Fictional affected inspection record IR-0087."}, required=False)
if cal_event and cal_event.state == "draft":
    cal_event.with_user(demo_user).action_start()
    cal_event.with_user(demo_user).action_submit_review()
    cal_event.with_user(demo_user).action_accept()
if len(equipment_records) > 1 and model_exists("pm.qms.calibration.event"):
    passing_event = upsert("pm.qms.calibration.event", code="APEX-CAL-EVT-002", name="Bench multimeter periodic calibration", vals={"equipment_id": equipment_records[1].id, "organization_id": organization.id, "company_id": company.id, "provider_id": provider.id if provider else False, "calibration_date": today, "next_due_date": today + relativedelta(days=18), "result": "pass", "notes": "Fictional accepted certificate; next calibration is due within the configured reminder window."}, required=True)
    if passing_event and passing_event.state == "draft":
        passing_event.with_user(demo_user).action_start()
        passing_event.with_user(demo_user).action_submit_review()
        passing_event.with_user(demo_user).action_accept()
    overdue_event = upsert("pm.qms.calibration.event", code="APEX-CAL-EVT-003", name="ESD resistance meter overdue verification", vals={"equipment_id": equipment_records[2].id, "organization_id": organization.id, "company_id": company.id, "provider_id": provider.id if provider else False, "calibration_date": today - relativedelta(days=100), "next_due_date": today - relativedelta(days=10), "result": "pass", "notes": "Fictional accepted verification with a lapsed next-due date; the instrument is overdue for review."}, required=True)
    if overdue_event and overdue_event.state == "draft":
        overdue_event.with_user(demo_user).action_start()
        overdue_event.with_user(demo_user).action_submit_review()
        overdue_event.with_user(demo_user).action_accept()
    if len(equipment_records) > 4:
        current_event = upsert("pm.qms.calibration.event", code="APEX-CAL-EVT-005", name="Digital oscilloscope current calibration", vals={"equipment_id": equipment_records[4].id, "organization_id": organization.id, "company_id": company.id, "provider_id": provider.id if provider else False, "calibration_date": today, "next_due_date": today + relativedelta(months=6), "result": "pass", "notes": "Fictional accepted certificate supports current electrical test monitoring."}, required=True)
        if current_event and current_event.state == "draft":
            current_event.with_user(demo_user).action_start()
            current_event.with_user(demo_user).action_submit_review()
            current_event.with_user(demo_user).action_accept()
    if current_event and current_event.state == "draft":
        current_event.with_user(demo_user).action_start()
        current_event.with_user(demo_user).action_submit_review()
        current_event.with_user(demo_user).action_accept()
    if len(equipment_records) > 3:
        in_calibration = upsert("pm.qms.calibration.event", code="APEX-CAL-EVT-004", name="SMT torque driver sent for calibration", vals={"equipment_id": equipment_records[3].id, "organization_id": organization.id, "company_id": company.id, "provider_id": provider.id if provider else False, "date_sent": today, "notes": "Fictional instrument is in transit to the calibration provider; service report is pending."}, required=True)
        if in_calibration and in_calibration.state == "draft":
            in_calibration.with_user(demo_user).action_start()

# Customer and supplier quality.
complaint = upsert("pm.qms.customer.complaint", code="APEX-CC-001", name="Nova Aero intermittent power-module complaint", vals={"organization_id": organization.id, "company_id": company.id, "customer_id": customer.id, "partner_id": customer.id, "process_id": next((p.id for p in processes if p.code == "APEX-CUST"), processes[0].id), "response_owner_id": demo_user.id, "containment_owner_id": users["Quality Supervisor"].id, "description": "Fictional customer reports intermittent power-module operation on shipped Lot L-24017; returned unit is linked to its board and component lots.", "received_date": today - relativedelta(days=6), "response_due_date": overdue, "containment_required": True, "containment_due_date": due_today, "containment_action": "Acknowledge the report, quarantine retained units, and review electrical test and traceability records.", "priority": "high", "related_ncr_id": ncr.id if ncr else False}, required=False)
alert = upsert("pm.qms.quality.alert", code="APEX-QA-001", name="Electrical retest alert for Lot L-24017", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-ETEST"), processes[0].id), "owner_id": demo_user.id, "review_date": due_today, "severity": "high", "message": "Fictional alert: preserve test logs and verify current firmware and test-instruction revision before release.", "customer_complaint_id": complaint.id if complaint else False}, required=False)
eightd = upsert("pm.qms.eight.d", code="APEX-8D-001", name="8D - Nova Aero intermittent electrical complaint", vals={"organization_id": organization.id, "company_id": company.id, "customer_complaint_id": complaint.id if complaint else False, "owner_id": demo_user.id, "due_date": due_soon, "problem_statement": "Fictional 8D for intermittent electrical performance reported by Nova Aero Components.", "containment_action": "Contain affected stock, preserve test logs, and verify replacement units with the approved electrical test sequence.", "root_cause": "Test-instruction revision at point of use was not reconciled with the released test configuration.", "corrective_action": "Add cell-level revision confirmation and inspector refresher training."}, required=False)
supplier_issue = upsert("pm.qms.supplier.issue", code="APEX-SI-001", name="Orion Metals lot certificate discrepancy", vals={"organization_id": organization.id, "company_id": company.id, "supplier_id": supplier.id, "partner_id": supplier.id, "process_id": next((p.id for p in processes if p.code == "APEX-SUP"), processes[0].id), "owner_id": users["Quality Supervisor"].id, "description": "Fictional alloy certificate revision does not match the purchase specification; receiving inspection holds the material lot.", "severity": "high", "containment_due_date": due_today}, required=False)
scar = upsert("pm.qms.scar", code="APEX-SCAR-001", name="SCAR - Orion Metals certificate discrepancy", vals={"organization_id": organization.id, "company_id": company.id, "supplier_issue_id": supplier_issue.id if supplier_issue else False, "supplier_id": supplier.id, "partner_id": supplier.id, "owner_id": demo_user.id, "response_due_date": overdue, "severity": "major", "problem_statement": "Fictional supplier corrective action for a material certificate revision mismatch.", "containment_request": "Segregate the affected lot and provide a corrected certificate with lot traceability.", "supplier_response": "Fictional response: controlled certificate template and second-person release review were implemented.", "root_cause": "Certificate template revision was not linked to the order specification.", "corrective_action": "Update supplier document control and verify two subsequent electronic-component lots."}, required=False)
supplier_issue_counterfeit = upsert("pm.qms.supplier.issue", code="APEX-SI-002", name="Beacon Components source authorization review", vals={"organization_id": organization.id, "company_id": company.id, "supplier_id": supplier_alt.id, "partner_id": supplier_alt.id, "process_id": process_by_code.get("APEX-RECV", processes[0]).id, "owner_id": users["Quality Supervisor"].id, "description": "Fictional incoming controller IC lot is held pending authorized-source and authenticity documentation review.", "severity": "critical", "containment_due_date": due_today}, required=False)
scar_counterfeit = upsert("pm.qms.scar", code="APEX-SCAR-002", name="SCAR - Beacon Components source verification", vals={"organization_id": organization.id, "company_id": company.id, "supplier_issue_id": supplier_issue_counterfeit.id if supplier_issue_counterfeit else False, "supplier_id": supplier_alt.id, "partner_id": supplier_alt.id, "owner_id": demo_user.id, "response_due_date": due_soon, "severity": "major", "problem_statement": "Fictional source verification request for a held power-management component lot.", "containment_request": "Provide authorized-distributor evidence, manufacturer lot code, and certificate of conformity.", "supplier_response": "Awaiting fictional supplier response; material remains on hold.", "root_cause": "Supplier approval status was not matched to the purchase source at receipt.", "corrective_action": "Add approved-source verification to receiving inspection and supplier monitoring."}, required=False)

# Supplier/customer scorecards and cause-analysis screens are populated by linked records.
upsert_by_identity("pm.qms.customer.satisfaction", [("customer_id", "=", customer.id), ("organization_id", "=", organization.id), ("measurement_method", "=", "survey")], {"customer_id": customer.id, "organization_id": organization.id, "measurement_date": today, "period_start": today - relativedelta(days=90), "period_end": today, "measurement_method": "survey", "score": 4.3, "score_scale_max": 5.0, "response_count": 3, "owner_id": users["Management User"].id, "notes": "Fictional survey aggregate linked to complaint response and delivery performance."}, required=True)
for partner, quality, delivery in [(supplier, 88.0, 93.0), (supplier_alt, 72.0, 85.0)]:
    evaluation = upsert_by_identity("pm.qms.supplier.evaluation", [("supplier_id", "=", partner.id), ("organization_id", "=", organization.id)], {"supplier_id": partner.id, "organization_id": organization.id, "evaluation_date": today, "period_start": today - relativedelta(days=30), "period_end": today, "evaluator_id": demo_user.id, "quality_score": quality, "delivery_score": delivery, "service_score": quality, "compliance_score": quality, "quality_weight": 40.0, "delivery_weight": 30.0, "service_weight": 20.0, "compliance_weight": 10.0, "status": "monitor" if quality < 80 else "approved", "notes": "Fictional supplier scorecard linked to incoming issue, SCAR, and follow-up."}, required=True)
    if evaluation and evaluation.state == "draft":
        evaluation.with_user(demo_user).action_complete()

# Period scorecards are separate from raw evaluations and feed dashboard/KPI views.
upsert_by_identity(
    "pm.qms.customer.performance",
    [("customer_id", "=", customer.id), ("organization_id", "=", organization.id)],
    {"customer_id": customer.id, "organization_id": organization.id, "period_start": today - relativedelta(days=90), "period_end": today, "customer_satisfaction_score": 86.0, "manual_complaint_count": 1, "return_count": 1, "rejection_count": 2, "delivery_performance": 94.0, "survey_response_count": 3, "notes": "Fictional customer scorecard linked to APEX-CC-001, APEX-NCR-001, and the survey aggregate."},
    required=True,
)
for partner, quality, delivery, received, rejected, late in [
    (supplier, 88.0, 93.0, 2400.0, 12.0, 1),
    (supplier_alt, 72.0, 85.0, 900.0, 28.0, 3),
]:
    upsert_by_identity(
        "pm.qms.supplier.performance",
        [("supplier_id", "=", partner.id), ("organization_id", "=", organization.id)],
        {"supplier_id": partner.id, "organization_id": organization.id, "period_start": today - relativedelta(days=90), "period_end": today, "quality_score": quality, "delivery_score": delivery, "received_quantity": received, "rejected_quantity": rejected, "late_delivery_count": late, "total_delivery_count": 12, "notes": "Fictional supplier scorecard linked to receiving, supplier issue, SCAR, and completed evaluation."},
        required=True,
    )

root_cause = upsert("pm.qms.root.cause.analysis", code="APEX-RCA-001", name="Five Why - SMT solder wetting escape", vals={"organization_id": organization.id, "process_id": process_by_code.get("APEX-SMT", processes[0]).id, "method": "5why", "problem_statement": "Solder wetting defect was identified during first-piece inspection of Lot SMT-2609.", "root_cause": "The approved reflow profile change did not trigger a documented verification sample.", "contributing_causes": "Paste exposure tracking and sample coverage require follow-up.", "evidence_summary": "Synthetic references: APEX-NCR-002, APEX-DOC-009 revision A, and calibration/test records.", "reviewer_id": users["Internal Auditor"].id, "ncr_id": ncr_solder.id if ncr_solder else False}, required=False)
if root_cause:
    for sequence, (question, answer) in enumerate([
        ("Why was wetting incomplete?", "The joint profile did not consistently meet the internal wetting window."),
        ("Why did the profile vary?", "A zone adjustment was made without a recorded first-piece verification."),
        ("Why was verification missed?", "The setup checklist did not require a sample after a profile change."),
        ("Why was the checklist incomplete?", "Change review did not include the SMT process owner."),
        ("What is the systemic cause?", "Process-change control lacked an explicit test-evidence gate."),
    ], start=1):
        upsert_by_identity("pm.qms.root.cause.line", [("analysis_id", "=", root_cause.id), ("sequence", "=", sequence)], {"analysis_id": root_cause.id, "sequence": sequence, "question": question, "answer": answer, "evidence": "Fictional evidence reference only; see the linked NCR and controlled work instruction."})

# Cost of Quality scenario. Cost events are source-linked and workflow-confirmed.
cost_types = {}
for category, code, name in [
    ("prevention", "APEX-CQT-PREV", "Corrective training prevention"),
    ("appraisal", "APEX-CQT-APP", "Additional dimensional verification"),
    ("internal_failure", "APEX-CQT-INT", "Rework and scrap"),
    ("external_failure", "APEX-CQT-EXT", "Customer response effort"),
]:
    cost_types[category] = upsert("pm.qms.cost.type", code=code, name=name, vals={"category": category, "company_id": company.id, "description": f"Fictional {category} cost type for product demo."}, required=False)

def ensure_cost_event(code, name, source_model, source_record, lines):
    if not model_exists("pm.qms.cost.event") or not source_record:
        return env["ir.model"].browse()
    event = env["pm.qms.cost.event"].search([("code", "=", code), ("company_id", "=", company.id)], limit=1)
    if not event:
        event = env["pm.qms.cost.event"].create(filtered("pm.qms.cost.event", {"code": code, "name": name, "organization_id": organization.id, "process_id": processes[0].id, "event_date": today, "source_model": source_model, "source_id": source_record.id, "notes": "Fictional interconnected Cost of Quality demo event."}))
    elif event.state == "confirmed" and event.name != name:
        event.write({"name": name})
    if event.state != "confirmed":
        event.line_ids.unlink()
        for category, desc, amount, recovery in lines:
            ctype = cost_types.get(category)
            if ctype:
                env["pm.qms.cost.line"].create(filtered("pm.qms.cost.line", {"event_id": event.id, "cost_type_id": ctype.id, "description": desc, "amount": amount, "recovery_amount": recovery, "is_estimated": True, "notes": "Fictional amount for demo analytics."}))
        try:
            event.with_user(demo_user).action_confirm()
        except Exception as exc:
            raise RuntimeError(f"Cost event confirmation failed for {code}: {exc}") from exc
    return event

ensure_cost_event("APEX-CQ-001", "Intermittent electrical complaint quality-cost case", "pm.qms.customer.complaint", complaint, [("external_failure", "Customer response and replacement power-module shipment", 1850.0, 250.0), ("internal_failure", "Retest and controlled rework of retained electrical assemblies", 1250.0, 0.0), ("appraisal", "Expanded insulation-resistance and functional test sampling", 640.0, 0.0), ("prevention", "Electrical test revision-control refresher", 420.0, 0.0)])
ensure_cost_event("APEX-CQ-002", "Supplier recovery for component certificate discrepancy", "pm.qms.scar", scar, [("external_failure", "Customer documentation response for affected component lot", 720.0, 0.0), ("internal_failure", "Receiving hold, authenticity review, and controlled sorting", 980.0, 600.0)])

# Management review after source records exist.
review = upsert(
    "pm.qms.management.review",
    code="APEX-MR-001",
    name="Apex QMS Management Review - Demo",
    vals={
        "organization_id": organization.id,
        "company_id": company.id,
        "chair_id": users["Management User"].id,
        "planned_date": today,
        "actual_date": today,
        "period_start": today - relativedelta(months=3),
        "period_end": today,
        "objective": "Fictional management review drawing inputs from QMS performance, risks, audit, customer quality, calibration, training, and Cost of Quality.",
        "agenda_notes": "Review readiness, customer impact, supplier containment, training, calibration, and Cost of Quality signals.",
        "general_notes": "Demo record only; not connected to the retired pilot environment.",
        "conclusion": "Continue the fictional readiness program and rebalance effort toward prevention.",
        "next_review_date": next_month,
    },
    required=False,
)
review_input_specs = [
    ("kpi", "Electrical test pass rate", "kpi_measurement", "APEX-KPI-004", 97.9, "%", "Synthetic current-period test yield below target; review retest trend."),
    ("customer_performance", "Customer complaint response", "customer_performance", "APEX-CC-001", 91.5, "score", "Review the intermittent power-module complaint and containment effectiveness."),
    ("supplier_evaluation", "Beacon source authorization", "supplier_evaluation", "APEX-SUP-EVAL-002", 72.0, "score", "Supplier remains monitored while source documentation is reviewed."),
    ("audit_findings", "SMT reflow evidence gap", "audit_finding", "APEX-AF-001", 1.0, "finding", "Review objective evidence and the linked corrective action."),
    ("risks", "Electrical test escape risk", "risk", "APEX-RISK-008", 12.0, "risk score", "Review functional test coverage and extended soak sampling."),
    ("capa", "Solder wetting analysis", "capa", "APEX-CAPA-002", 1.0, "open CAPA", "Check the fishbone, Is/Is Not analysis, and action owner due dates."),
    ("resources", "Calibration OOT impact", "resource", "APEX-OOT-001", 1.0, "equipment", "Confirm affected references were assessed before equipment return."),
    ("previous_actions", "Supplier certificate follow-up", "management_review_action", "APEX-MRA-001", 1.0, "action", "Carry forward the previous review action and verify evidence."),
]
if review:
    for category, title, source_type, source_identifier, numeric_value, unit, description in review_input_specs:
        upsert_by_identity("pm.qms.management.review.input", [("review_id", "=", review.id), ("category", "=", category), ("title", "=", title)], {"review_id": review.id, "category": category, "title": title, "description": description, "snapshot_date": now, "numeric_value": numeric_value, "unit_of_measure": unit, "period_start": today - relativedelta(months=3), "period_end": today, "source_type": source_type, "source_identifier": source_identifier, "text_value": "Fictional snapshot reference for guided Management Review discussion."})
upsert(
    "pm.qms.management.review.decision",
    name="Alternate supplier qualification decision",
    vals={
        "review_id": review.id if review else False,
        "organization_id": organization.id,
        "company_id": company.id,
        "description": "Proceed with alternate supplier qualification for critical alloy family.",
        "decision_type": "improvement",
        "owner_id": demo_user.id,
        "decision_date": today,
        "notes": "Fictional management decision for the demo environment.",
    },
    extra_domain=[("review_id", "=", review.id if review else 0), ("name", "=", "Alternate supplier qualification decision")],
    required=False,
)
upsert("pm.qms.management.review.action", code="APEX-MRA-001", name="Review COPQ trend with leadership", vals={"review_id": review.id if review else False, "organization_id": organization.id, "company_id": company.id, "owner_id": demo_user.id, "target_date": due_soon, "description": "Fictional management review action to review quality cost trends and prevention spend."}, required=False)
call(review, "action_generate_snapshot", "action_snapshot")

# Refresh Action Center from authoritative source records only.
action_count = 0
if model_exists("pm.qms.action.center.line"):
    try:
        action_count = env["pm.qms.action.center.line"].with_user(demo_user)._refresh_for_current_user()
    except Exception as exc:
        warnings.append(f"action_center_refresh:{exc.__class__.__name__}:{exc}")

env.cr.commit()

summary_models = [
    "pm.qms.organization", "pm.qms.site", "pm.qms.process", "pm.qms.document", "pm.qms.evidence", "pm.qms.risk", "pm.qms.nonconformity", "pm.qms.capa", "pm.qms.audit", "pm.qms.audit.finding", "pm.qms.objective", "pm.qms.kpi.measurement", "pm.qms.person", "pm.qms.training.record", "pm.qms.qualification.record", "pm.qms.equipment", "pm.qms.customer.complaint", "pm.qms.quality.alert", "pm.qms.eight.d", "pm.qms.supplier.issue", "pm.qms.scar", "pm.qms.cost.event", "pm.qms.cost.line", "pm.qms.management.review",
]
print("DEMO_SEED_SUMMARY")
print(f"database={env.cr.dbname}")
print(f"company={company.name}")
print(f"organization={organization.code if organization else 'missing'}")
print(f"demo_login={ADMIN_LOGIN}")
print(f"action_center_rows={action_count}")
for model_name in summary_models:
    if model_exists(model_name):
        domain = [("organization_id", "=", organization.id)] if "organization_id" in env[model_name]._fields else [("company_id", "=", company.id)] if "company_id" in env[model_name]._fields else []
        print(f"{model_name}={env[model_name].search_count(domain)}")
if warnings:
    print("DEMO_SEED_WARNINGS")
    for warning in warnings[:80]:
        print(warning)
