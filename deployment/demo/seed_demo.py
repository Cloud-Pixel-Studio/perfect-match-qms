import base64
import os
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import Command, fields

EXPECTED_DB = os.getenv("PMQMS_DEMO_DB", "pmqms_demo")
COMPANY_NAME = os.getenv("PMQMS_DEMO_COMPANY_NAME", "Apex Precision Systems, Inc.")
ADMIN_LOGIN = os.getenv("PMQMS_DEMO_ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.getenv("PMQMS_DEMO_ADMIN_PASSWORD")
QUALITY_MANAGER_LOGIN = os.getenv("PMQMS_DEMO_QUALITY_MANAGER_LOGIN", "olivia.parker.demo@perfectmatch.local")
PERSONA_PASSWORD_DIR = Path(os.getenv("PMQMS_DEMO_PERSONA_PASSWORD_DIR", "/run/pmqms-demo-persona-passwords"))
ORG_CODE = "APEX"

if EXPECTED_DB != "pmqms_demo" or env.cr.dbname != "pmqms_demo":
    raise RuntimeError(f"Demo seed refused for database {env.cr.dbname!r}; only pmqms_demo is allowed.")

now = fields.Datetime.now()
today = fields.Date.context_today(env["res.company"])
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
                writable = {k: v for k, v in payload.items() if k not in ("code",) and not model._fields[k].readonly}
                if writable:
                    record.write(writable)
            else:
                record = model.create(payload)
        return record
    except Exception as exc:
        warnings.append(f"{model_name}:{code or name}:{exc.__class__.__name__}:{exc}")
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
if ADMIN_PASSWORD:
    technical_admin_values["password"] = ADMIN_PASSWORD
if technical_admin:
    technical_admin.write(technical_admin_values)
else:
    technical_admin_values["login"] = ADMIN_LOGIN
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
        "Headquarters & Quality Center",
        "headquarters",
        True,
        "Leadership, QMS governance, document control, audit coordination, and training administration.",
    ),
    (
        "APEX-MFG",
        "Manufacturing Plant",
        "manufacturing",
        False,
        "Receiving, production, calibration, and process-owner activities for fictional Apex operations.",
    ),
    (
        "APEX-INS",
        "Inspection & Distribution Center",
        "inspection",
        False,
        "Final inspection, customer release, shipping, and distribution activities.",
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
    if persona_password_file.is_file():
        vals["password"] = persona_password_file.read_text(encoding="utf-8").strip()
    user = env["res.users"].with_context(no_reset_password=True).search([("login", "=", login)], limit=1)
    if user:
        writable = {k: v for k, v in vals.items() if k != "login"}
        user.write(writable)
    else:
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

process_specs = [
    ("APEX-LEAD", "Leadership", "management"),
    ("APEX-QMS", "Quality Management", "support"),
    ("APEX-CUST", "Customer Service", "core"),
    ("APEX-SUP", "Purchasing / Supplier Management", "support"),
    ("APEX-REC", "Receiving Inspection", "core"),
    ("APEX-PROD", "Production", "core"),
    ("APEX-FIN", "Final Inspection", "core"),
    ("APEX-SHIP", "Shipping", "core"),
    ("APEX-DOC", "Document Control", "support"),
    ("APEX-AUD", "Internal Audit", "support"),
    ("APEX-TRN", "Training & Competency", "support"),
    ("APEX-CAL", "Calibration", "support"),
]
process_site_codes = {
    "APEX-LEAD": ["APEX-HQ"],
    "APEX-QMS": ["APEX-HQ"],
    "APEX-CUST": ["APEX-INS"],
    "APEX-SUP": ["APEX-MFG"],
    "APEX-REC": ["APEX-MFG"],
    "APEX-PROD": ["APEX-MFG"],
    "APEX-FIN": ["APEX-INS"],
    "APEX-SHIP": ["APEX-INS"],
    "APEX-DOC": ["APEX-HQ"],
    "APEX-AUD": ["APEX-HQ"],
    "APEX-TRN": ["APEX-HQ"],
    "APEX-CAL": ["APEX-MFG", "APEX-INS"],
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
    "Quality Supervisor": {"site_codes": ["APEX-MFG"], "process_codes": [code for code, sites_for_process in process_site_codes.items() if "APEX-MFG" in sites_for_process]},
    "Document Controller": {"all_sites": True, "all_processes": True},
    "Internal Auditor": {"all_sites": True, "all_processes": True},
    "Process Owner": {"site_codes": ["APEX-MFG", "APEX-INS"], "process_codes": ["APEX-PROD", "APEX-FIN"]},
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
    "Quality Supervisor": "APEX-MFG",
    "Document Controller": "APEX-HQ",
    "Internal Auditor": "APEX-HQ",
    "Process Owner": "APEX-MFG",
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
project = env["pm.qms.implementation.project"].search([("name", "=", "Apex Precision QMS Demo Implementation"), ("organization_id", "=", organization.id)], limit=1) if model_exists("pm.qms.implementation.project") else False
if pack and not project:
    try:
        project = env["pm.qms.implementation.project"].generate_from_wizard({
            "name": "Apex Precision QMS Demo Implementation",
            "company_id": company.id,
            "organization_id": organization.id,
            "project_manager_id": demo_user.id,
            "date_start": today - relativedelta(days=45),
            "target_date": today + relativedelta(days=75),
            "implementation_type": "migration",
            "pack_ids": pack.ids,
            "create_odoo_project": True,
            "notes": "Fictional full-product demo implementation using original Perfect Match control wording only.",
        })
    except Exception as exc:
        warnings.append(f"implementation_project:{exc.__class__.__name__}:{exc}")
elif project:
    call(project, "action_sync_framework")

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

# Documents, revisions, evidence, and acknowledgments.
document_specs = [
    ("APEX-DOC-001", "Quality Policy", "APEX-LEAD"),
    ("APEX-DOC-002", "Quality Manual / QMS Overview", "APEX-QMS"),
    ("APEX-DOC-003", "SOP - Control of Nonconforming Outputs", "APEX-FIN"),
    ("APEX-DOC-004", "SOP - Document Control", "APEX-DOC"),
    ("APEX-DOC-005", "Work Instruction - Final Inspection", "APEX-FIN"),
    ("APEX-DOC-006", "Form - Equipment Verification", "APEX-CAL"),
]
documents = []
revisions = []
for code, title, process_code in document_specs:
    proc = next((p for p in processes if p.code == process_code), processes[0] if processes else False)
    doc = upsert("pm.qms.document", code=code, name=title, vals={"organization_id": organization.id, "company_id": company.id, "process_id": proc.id if proc else False, "owner_id": demo_user.id, "document_type": best_selection(env["pm.qms.document"], "document_type", ("procedure", "policy", "form")) if model_exists("pm.qms.document") and "document_type" in env["pm.qms.document"]._fields else False, "description": f"Original fictional Apex document for demo: {title}."}, required=False)
    if doc:
        documents.append(doc)
        rev = upsert("pm.qms.document.revision", vals={"document_id": doc.id, "revision": "A", "version": "A", "title": title, "content": f"Fictional demo content for {title}. No copyrighted standards text is included.", "effective_date": today - relativedelta(days=20), "owner_id": demo_user.id}, extra_domain=[("document_id", "=", doc.id), ("revision", "=", "A")], required=False)
        if rev:
            revisions.append(rev)
        ci = control_instances[(len(documents) - 1) % len(control_instances)] if control_instances else False
        req = upsert("pm.qms.evidence.requirement", code=f"APEX-REQ-{code[-3:]}", name=f"Required evidence - {title}", vals={"organization_id": organization.id, "company_id": company.id, "process_id": proc.id if proc else False, "control_id": ci.control_id.id if ci else (controls[:1].id if controls else False), "control_instance_id": ci.id if ci else False, "description": f"Required evidence demo item for {title}."}, required=False)
        upsert("pm.qms.evidence", code=f"APEX-EV-{code[-3:]}", name=f"Evidence - {title}", vals={"organization_id": organization.id, "company_id": company.id, "process_id": proc.id if proc else False, "document_id": doc.id, "control_instance_id": ci.id if ci else False, "evidence_requirement_id": req.id if req else False, "owner_id": demo_user.id, "evidence_date": today - relativedelta(days=5), "description": f"Linked fictional evidence package for {title}."}, required=False)

# Risk, NCR, CAPA, audit, KPI, and performance.
risk_open = upsert("pm.qms.risk", code="APEX-RISK-001", name="Single-source supplier continuity risk", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-SUP"), processes[0].id), "owner_id": users["Quality Supervisor"].id, "description": "Fictional risk: critical alloy depends on one approved supplier.", "cause": "Limited approved supplier base.", "potential_effect": "Production interruption and customer delivery risk.", "mitigation_plan": "Qualify an alternate supplier and increase incoming certificate review.", "target_date": overdue, "review_date": due_soon, "likelihood": 3, "impact": 4}, required=False)
risk_monitor = upsert("pm.qms.risk", code="APEX-RISK-002", name="Controlled final inspection capacity risk", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": users["Process Owner"].id, "description": "Fictional monitored risk: inspection queue grows during peak demand.", "mitigation_plan": "Cross-train backup inspectors and monitor weekly queue aging.", "target_date": due_soon, "review_date": next_month, "likelihood": 2, "impact": 3}, required=False)

ncr = upsert("pm.qms.nonconformity", code="APEX-NCR-001", name="Incorrect hole diameter on Lot L-24017", vals={"organization_id": organization.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "source_type": "internal", "description": "Final inspection found a hole diameter outside the fictional Apex tolerance window on Lot L-24017.", "detected_date": today - relativedelta(days=9), "owner_id": users["Quality Supervisor"].id, "severity": "major", "containment_required": True, "containment_action": "Hold Lot L-24017 and reinspect related lots with current setup instruction.", "containment_owner_id": users["Quality Supervisor"].id, "containment_date": today - relativedelta(days=8), "containment_completed": True, "disposition": "rework", "disposition_notes": "Fictional demo disposition: rework and reinspect affected units.", "root_cause_summary": "Setup instruction revision mismatch at point of use.", "target_date": overdue}, required=False)

capa = upsert("pm.qms.capa", code="APEX-CAPA-001", name="Repeated inspection escape from outdated setup instruction", vals={"organization_id": organization.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": demo_user.id, "source_type": "ncr", "source_reference": "APEX-NCR-001 / Lot L-24017", "source_ncr_id": ncr.id if ncr else False, "problem_statement": "Fictional repeated inspection escape linked to obsolete setup instruction at the work cell.", "root_cause_method": "5why", "root_cause_analysis": "5 Why analysis indicates obsolete setup instructions remained available after revision release.", "root_cause": "Document release and point-of-use verification were not synchronized.", "action_plan": "Remove obsolete copies, train inspectors, add layered verification.", "action_owner_id": demo_user.id, "target_date": due_soon, "effectiveness_required": True, "effectiveness_review_date": due_soon + relativedelta(days=21)}, required=False)
if capa:
    for seq, answer in enumerate(["Diameter drift repeated at final inspection.", "Setup sheet at the station was obsolete.", "Point-of-use copy was not reconciled after revision.", "Document control checklist did not include floor copy verification.", "Release workflow lacked a confirmation action for production cells."], start=1):
        upsert("pm.qms.capa.why", name=f"APEX-CAPA-001 Why {seq}", vals={"capa_id": capa.id, "sequence": seq, "question": "Why is it happening?", "answer": answer, "organization_id": organization.id, "company_id": company.id}, required=False)
    upsert("pm.qms.capa.action", name="Remove obsolete setup instructions", vals={"capa_id": capa.id, "owner_id": users["Document Controller"].id, "target_date": today - relativedelta(days=2), "description": "Remove superseded point-of-use copies from Final Inspection."}, required=False)
    upsert("pm.qms.capa.action", name="Train inspectors on revised setup instruction", vals={"capa_id": capa.id, "owner_id": users["Quality Supervisor"].id, "target_date": due_today, "description": "Complete refresher training for final inspection team."}, required=False)

program = upsert("pm.qms.audit.program", code="APEX-AUD-PROG-2026", name="Apex 2026 Internal Audit Program", vals={"organization_id": organization.id, "company_id": company.id, "owner_id": users["Internal Auditor"].id, "year": today.year, "description": "Fictional annual internal audit program for the product demo."}, required=False)
audit = upsert("pm.qms.audit", code="APEX-AUD-001", name="Document control and final inspection audit", vals={"program_id": program.id if program else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-DOC"), processes[0].id), "lead_auditor_id": users["Internal Auditor"].id, "owner_id": users["Internal Auditor"].id, "planned_date": today - relativedelta(days=5), "audit_date": today - relativedelta(days=4), "scope": "Document release, floor copy control, and final inspection evidence.", "criteria": "Perfect Match proprietary QMS controls and Apex internal procedures."}, required=False)
finding = upsert("pm.qms.audit.finding", code="APEX-AF-001", name="Floor copy reconciliation not consistently evidenced", vals={"audit_id": audit.id if audit else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-DOC"), processes[0].id), "owner_id": users["Document Controller"].id, "title": "Floor copy reconciliation not consistently evidenced", "classification": "nonconformity", "objective_evidence": "Fictional objective evidence: floor copy reconciliation was missing for one released setup instruction.", "description": "Fictional actionable finding from the internal audit.", "severity": "minor", "due_date": overdue}, required=False)
upsert("pm.qms.audit.finding", code="APEX-AF-002", name="Training roster evidence closed", vals={"audit_id": audit.id if audit else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-TRN"), processes[0].id), "owner_id": users["Quality Manager"].id, "title": "Training roster evidence closed", "classification": "observation", "objective_evidence": "Fictional objective evidence: prior training roster review was completed.", "description": "Fictional closed audit finding retained for trend context.", "due_date": today - relativedelta(days=30)}, required=False)

objective = upsert("pm.qms.objective", code="APEX-OBJ-001", name="Reduce dimensional escapes", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": demo_user.id, "target_value": 98.0, "unit": "%", "target_date": next_month, "description": "Improve right-first-time dimensional acceptance for fictional Apex shipments."}, required=False)
kpi = upsert("pm.qms.kpi", code="APEX-KPI-001", name="First-pass final inspection yield", vals={"objective_id": objective.id if objective else False, "organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": demo_user.id, "target_value": 98.0, "unit": "%", "description": "Monthly fictional first-pass yield trend."}, required=False)
for months_back, value in [(3, 94.8), (2, 96.1), (1, 97.0), (0, 96.4)]:
    period_start = (today.replace(day=1) - relativedelta(months=months_back))
    period_end = period_start + relativedelta(months=1, days=-1)
    upsert("pm.qms.kpi.measurement", vals={"kpi_id": kpi.id if kpi else False, "organization_id": organization.id, "company_id": company.id, "measurement_date": period_end, "period_start": period_start, "period_end": period_end, "source_type": "manual", "value": value, "notes": "Fictional trend value for demo analytics."}, extra_domain=[("kpi_id", "=", kpi.id if kpi else 0), ("period_start", "=", period_start), ("period_end", "=", period_end)], required=False)
upsert("pm.qms.customer.performance", vals={"organization_id": organization.id, "company_id": company.id, "partner_id": customer.id, "customer_id": customer.id, "period_start": today - relativedelta(days=30), "period_end": today, "measurement_date": today - relativedelta(days=15), "quality_score": 91.5, "delivery_score": 96.0, "complaint_count": 1, "notes": "Fictional customer performance demo."}, extra_domain=[("customer_id", "=", customer.id), ("organization_id", "=", organization.id), ("period_start", "=", today - relativedelta(days=30)), ("period_end", "=", today)], required=False)
upsert("pm.qms.supplier.performance", vals={"organization_id": organization.id, "company_id": company.id, "partner_id": supplier.id, "supplier_id": supplier.id, "period_start": today - relativedelta(days=30), "period_end": today, "measurement_date": today - relativedelta(days=15), "quality_score": 88.0, "delivery_score": 93.0, "issue_count": 1, "notes": "Fictional supplier performance demo."}, extra_domain=[("supplier_id", "=", supplier.id), ("organization_id", "=", organization.id), ("period_start", "=", today - relativedelta(days=30)), ("period_end", "=", today)], required=False)

# People, training, qualifications, acknowledgments.
competency = upsert("pm.qms.competency", code="APEX-COMP-001", name="Dimensional inspection competency", vals={"company_id": company.id, "description": "Ability to verify critical dimensions and record inspection evidence."}, required=False)
course = upsert("pm.qms.training.course", code="APEX-TRN-001", name="Revised setup instruction refresher", vals={"company_id": company.id, "description": "Fictional refresher course for revised setup and inspection instructions."}, required=False)
qtype = upsert("pm.qms.qualification.type", code="APEX-QUAL-001", name="Final Inspection Authorization", vals={"company_id": company.id, "description": "Fictional qualification for final inspection release authority."}, required=False)
for idx, person in enumerate(persons[:4]):
    upsert("pm.qms.competency.assessment", vals={"person_id": person.id, "competency_id": competency.id if competency else False, "organization_id": organization.id, "company_id": company.id, "assessment_date": today - relativedelta(days=10), "score": 4 if idx == 0 else 2, "notes": "Fictional competency assessment for demo."}, extra_domain=[("person_id", "=", person.id), ("competency_id", "=", competency.id if competency else 0), ("assessment_date", "=", today - relativedelta(days=10))], required=False)
    upsert("pm.qms.training.record", vals={"person_id": person.id, "course_id": course.id if course else False, "organization_id": organization.id, "company_id": company.id, "due_date": [overdue, due_today, due_soon, next_month][idx], "result": ["not_completed", "not_completed", "not_completed", "satisfactory"][idx], "notes": "Fictional training status for Action Center."}, extra_domain=[("person_id", "=", person.id), ("course_id", "=", course.id if course else 0), ("due_date", "=", [overdue, due_today, due_soon, next_month][idx])], required=False)
    upsert("pm.qms.qualification.record", vals={"person_id": person.id, "qualification_type_id": qtype.id if qtype else False, "organization_id": organization.id, "company_id": company.id, "issue_date": today - relativedelta(months=10), "expiration_date": [overdue, due_soon, next_month, today + relativedelta(months=6)][idx], "notes": "Fictional qualification for demo."}, extra_domain=[("person_id", "=", person.id), ("qualification_type_id", "=", qtype.id if qtype else 0), ("expiration_date", "=", [overdue, due_soon, next_month, today + relativedelta(months=6)][idx])], required=False)
if revisions and persons:
    upsert("pm.qms.document.acknowledgment", vals={"revision_id": revisions[2].id, "document_id": documents[2].id if len(documents) > 2 else False, "person_id": persons[2].id if len(persons) > 2 else persons[0].id, "organization_id": organization.id, "company_id": company.id, "due_date": due_today}, extra_domain=[("revision_id", "=", revisions[2].id), ("person_id", "=", persons[2].id if len(persons) > 2 else persons[0].id)], required=False)

# Calibration and OOT.
etype = upsert("pm.qms.equipment.type", code="APEX-EQTYPE-001", name="Dimensional measuring equipment", vals={"company_id": company.id, "description": "Fictional equipment type."}, required=False)
provider = upsert("pm.qms.calibration.provider", code="APEX-CAL-PROV-001", name="Metro Calibration Labs", vals={"company_id": company.id, "partner_id": supplier.id, "description": "Fictional external calibration provider."}, required=False)
equipment_records = []
for code, name, status_date in [("EQ-0001", "Digital Caliper", overdue), ("EQ-0002", "Micrometer", due_soon), ("EQ-0003", "Height Gauge", next_month), ("EQ-0004", "Torque Tester", due_today)]:
    eq_site = "APEX-MFG" if code in ("EQ-0001", "EQ-0002") else "APEX-INS"
    eq = upsert("pm.qms.equipment", code=code, name=name, vals={"organization_id": organization.id, "company_id": company.id, "site_id": site_by_code.get(eq_site).id if site_by_code.get(eq_site) else False, "process_id": next((p.id for p in processes if p.code == "APEX-CAL"), processes[0].id), "type_id": etype.id if etype else False, "responsible_person_id": persons[1].id if len(persons) > 1 else False, "calibration_required": True, "next_due_date": status_date, "frequency_interval": 90, "default_provider_id": provider.id if provider else False, "notes": "Fictional calibration status for demo."}, required=False)
    if eq:
        equipment_records.append(eq)
cal_event = upsert("pm.qms.calibration.event", code="APEX-CAL-EVT-001", name="Digital caliper failed calibration", vals={"equipment_id": equipment_records[0].id if equipment_records else False, "organization_id": organization.id, "company_id": company.id, "provider_id": provider.id if provider else False, "calibration_date": today - relativedelta(days=2), "result": best_selection(env["pm.qms.calibration.event"], "result", ("out_of_tolerance", "fail", "failed")) if model_exists("pm.qms.calibration.event") and "result" in env["pm.qms.calibration.event"]._fields else False, "notes": "Fictional OOT scenario for Lot L-24017 / Inspection Record IR-0087."}, required=False)
impact = upsert("pm.qms.calibration.impact.assessment", code="APEX-OOT-001", name="Digital caliper OOT impact assessment", vals={"equipment_id": equipment_records[0].id if equipment_records else False, "event_id": cal_event.id if cal_event else False, "organization_id": organization.id, "company_id": company.id, "assessor_person_id": persons[0].id if persons else False, "impact_summary": "Fictional impact review for Lot L-24017 and Inspection Record IR-0087.", "risk_level": "high", "target_date": due_today}, required=False)
upsert("pm.qms.calibration.affected.reference", name="Lot L-24017 / IR-0087", vals={"assessment_id": impact.id if impact else False, "reference": "Lot L-24017", "description": "Fictional affected inspection record IR-0087."}, required=False)

# Customer and supplier quality.
complaint = upsert("pm.qms.customer.complaint", code="APEX-CC-001", name="Nova Aero dimensional nonconformance complaint", vals={"organization_id": organization.id, "company_id": company.id, "customer_id": customer.id, "partner_id": customer.id, "process_id": next((p.id for p in processes if p.code == "APEX-CUST"), processes[0].id), "response_owner_id": demo_user.id, "containment_owner_id": users["Quality Supervisor"].id, "description": "Fictional customer reports dimensional nonconformance on delivered units from Lot L-24017.", "received_date": today - relativedelta(days=6), "response_due_date": overdue, "containment_required": True, "containment_due_date": due_today, "containment_action": "Notify customer, quarantine retained sample, and reverify shipped dimensions.", "priority": "high", "related_ncr_id": ncr.id if ncr else False}, required=False)
alert = upsert("pm.qms.quality.alert", code="APEX-QA-001", name="Dimensional verification alert for Lot L-24017", vals={"organization_id": organization.id, "company_id": company.id, "process_id": next((p.id for p in processes if p.code == "APEX-FIN"), processes[0].id), "owner_id": demo_user.id, "review_date": due_today, "severity": "high", "message": "Fictional alert: verify current setup instruction before final inspection release.", "customer_complaint_id": complaint.id if complaint else False}, required=False)
eightd = upsert("pm.qms.eight.d", code="APEX-8D-001", name="8D - Nova Aero dimensional complaint", vals={"organization_id": organization.id, "company_id": company.id, "customer_complaint_id": complaint.id if complaint else False, "owner_id": demo_user.id, "due_date": due_soon, "problem_statement": "Fictional 8D for dimensional nonconformance reported by Nova Aero Components.", "containment_action": "Contain affected stock and verify replacement parts.", "root_cause": "Obsolete setup instruction available at point of use.", "corrective_action": "Document control floor-copy verification and inspector refresher training."}, required=False)
supplier_issue = upsert("pm.qms.supplier.issue", code="APEX-SI-001", name="Orion Metals certificate discrepancy", vals={"organization_id": organization.id, "company_id": company.id, "supplier_id": supplier.id, "partner_id": supplier.id, "process_id": next((p.id for p in processes if p.code == "APEX-SUP"), processes[0].id), "owner_id": users["Quality Supervisor"].id, "description": "Fictional raw material dimensional certification discrepancy found at receiving inspection.", "severity": "high", "containment_due_date": due_today}, required=False)
scar = upsert("pm.qms.scar", code="APEX-SCAR-001", name="SCAR - Orion Metals certificate discrepancy", vals={"organization_id": organization.id, "company_id": company.id, "supplier_issue_id": supplier_issue.id if supplier_issue else False, "supplier_id": supplier.id, "partner_id": supplier.id, "owner_id": demo_user.id, "response_due_date": overdue, "severity": "major", "problem_statement": "Fictional SCAR requesting containment and root cause for certificate discrepancy.", "containment_request": "Segregate affected certificate lot and provide corrected material certification.", "supplier_response": "Fictional response: certificate template control corrected and second-person review added.", "root_cause": "Supplier certificate template revision mismatch.", "corrective_action": "Supplier document control update and verification of subsequent shipments."}, required=False)

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
    if event.state != "confirmed":
        event.line_ids.unlink()
        for category, desc, amount, recovery in lines:
            ctype = cost_types.get(category)
            if ctype:
                env["pm.qms.cost.line"].create(filtered("pm.qms.cost.line", {"event_id": event.id, "cost_type_id": ctype.id, "description": desc, "amount": amount, "recovery_amount": recovery, "is_estimated": True, "notes": "Fictional amount for demo analytics."}))
        try:
            event.action_confirm()
        except Exception as exc:
            warnings.append(f"cost_confirm:{code}:{exc.__class__.__name__}:{exc}")
    return event

ensure_cost_event("APEX-CQ-001", "Dimensional complaint quality cost story", "pm.qms.customer.complaint", complaint, [("external_failure", "Replacement shipment and customer response", 1850.0, 250.0), ("internal_failure", "Reinspection and rework of retained inventory", 1250.0, 0.0), ("appraisal", "Additional dimensional verification", 640.0, 0.0), ("prevention", "Inspector refresher training", 420.0, 0.0)])
ensure_cost_event("APEX-CQ-002", "Supplier recovery for certificate discrepancy", "pm.qms.scar", scar, [("external_failure", "Customer documentation response effort", 720.0, 0.0), ("internal_failure", "Receiving inspection hold and sorting", 980.0, 600.0)])

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
