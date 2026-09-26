import json
import os
from odoo.addons.pm_qms_license.services.environment import read_environment_id

GUIDED_EXCLUDED_MENU_IDS = {
    "menu_pm_qms_users_access",
    "menu_pm_qms_license",
    "menu_pm_qms_activation_requests",
    "menu_pm_qms_project_generator",
    "menu_pm_qms_document_import",
    "menu_pm_qms_evidence_import",
    "menu_pm_qms_quality_mapping_import",
}
GUIDED_TRANSIENT_MODEL_EXAMPLES = {
    "pm.qms.dashboard": "computed dashboard over seeded KPI, risk, CAPA, audit, equipment and Action Center sources",
}
GUIDED_MODEL_EXAMPLES = {
    "pm.qms.site": "APEX-HQ / APEX-MFG / APEX-INS",
    "pm.qms.audit.program": "APEX-AUD-PROG-2026",
    "pm.qms.audit": "APEX-AUD-001",
    "pm.qms.audit.finding": "findings linked to APEX-AUD-001",
    "pm.qms.audit.evidence": "synthetic reflow sample linked to audit criterion",
    "pm.qms.equipment": "EQ-0001 through EQ-0005 with lifecycle states",
    "pm.qms.calibration.event": "APEX-CAL-EVT-001 through APEX-CAL-EVT-005",
    "pm.qms.calibration.impact.assessment": "APEX-OOT-001",
    "pm.qms.equipment.type": "APEX-EQTYPE-001",
    "pm.qms.calibration.provider": "APEX-CAL-PROV-001",
    "pm.qms.capa": "APEX-CAPA-001 through APEX-CAPA-003",
    "pm.qms.capa.action": "actions linked to all three CAPA cases",
    "pm.qms.control.instance": "APEX-CI-001 through APEX-CI-006",
    "pm.qms.control": "APEX-CTRL-001 through APEX-CTRL-006",
    "pm.qms.activity": "APEX-ACT-001 through APEX-ACT-006",
    "pm.qms.evidence.requirement": "APEX-REQ-001 through APEX-REQ-013",
    "pm.qms.organization": "APEX",
    "pm.qms.process": "APEX-ESD / SMT / ASM / ETEST / CAL / NC / CAPA / TRACE / RECV / DISP",
    "pm.qms.external.mapping": "CUST-DWG-EL-014",
    "pm.qms.event": "workflow history from audited QMS transitions",
    "pm.qms.cost.event": "APEX-CQ-001 and APEX-CQ-002",
    "pm.qms.cost.type": "APEX-CQT-PREV / APP / INT / EXT",
    "pm.qms.customer.complaint": "APEX-CC-001",
    "pm.qms.quality.alert": "APEX-QA-001",
    "pm.qms.root.cause.analysis": "APEX-RCA-001 linked to APEX-NCR-002",
    "pm.qms.eight.d": "APEX-8D-001 linked to APEX-CC-001",
    "pm.qms.supplier.issue": "APEX-SI-001 and APEX-SI-002",
    "pm.qms.scar": "APEX-SCAR-001 and APEX-SCAR-002",
    "pm.qms.document": "APEX-DOC-001 through APEX-DOC-013",
    "pm.qms.document.revision": "controlled revisions for APEX-DOC-001 through APEX-DOC-013",
    "pm.qms.evidence": "synthetic evidence linked to canonical controlled documents",
    "pm.qms.framework.pack": "PM-QMS-QUALITY",
    "pm.qms.implementation.project": "Apex Precision Electronics QMS Guided Implementation",
    "pm.qms.implementation.control": "controls synchronized from PM-QMS-QUALITY",
    "project.task": "implementation activities synchronized to the guided project",
    "pm.qms.readiness.assessment": "Apex guided implementation readiness snapshot",
    "pm.qms.mapping.profile": "active PM-QMS mapping profile",
    "pm.qms.iso9001.transition.scenario": "ISO9001-2026-TRANSITION-2015",
    "pm.qms.iso9001.transition.action": "two controlled actions from the Apex guided 2015-to-2026 gap assessment",
    "pm.qms.iso9001.transition.review": "submitted Apex transition readiness review with an independent reviewer",
    "pm.qms.objective": "APEX-OBJ-001",
    "pm.qms.kpi": "APEX yield, supplier, NCR/CAPA, calibration and customer indicators",
    "pm.qms.kpi.measurement": "four measurements for each of eight KPIs",
    "pm.qms.customer.performance": "fictional Nova Aero scorecard",
    "pm.qms.customer.satisfaction": "fictional Nova Aero survey aggregate",
    "pm.qms.supplier.performance": "Orion and Beacon scorecards",
    "pm.qms.supplier.evaluation": "completed Orion and monitored Beacon evaluations",
    "pm.qms.management.review": "APEX management review snapshot",
    "pm.qms.management.review.action": "APEX-MRA-001",
    "pm.qms.management.review.decision": "alternate supplier qualification decision",
    "pm.qms.management.review.input": "eight cross-functional snapshot inputs",
    "pm.qms.nonconformity": "APEX-NCR-001 and APEX-NCR-002",
    "pm.qms.person": "seven official Demo personas",
    "pm.qms.role": "QMS role definitions used by the seven personas",
    "pm.qms.competency": "APEX electrical inspection competency",
    "pm.qms.competency.matrix.line": "role-linked competency requirements",
    "pm.qms.competency.assessment": "assessments for the seven personas",
    "pm.qms.training.course": "APEX-TRN-001",
    "pm.qms.training.event": "APEX electrical test and ESD refresher",
    "pm.qms.training.record": "one record per persona with varied due states",
    "pm.qms.qualification.record": "one qualification record per persona",
    "pm.qms.qualification.type": "APEX-QUAL-001",
    "pm.qms.document.acknowledgment": "required acknowledgment for assigned operator",
    "pm.qms.risk": "APEX-RISK-001 through APEX-RISK-008",
}

DEMO_INSTANCE = os.getenv("PMQMS_DEMO_INSTANCE", "demo")
APPROVED_DEMO_DATABASES = {"demo": "pmqms_demo", "demo2": "pmqms_demo2"}
EXPECTED_DB = os.getenv("PMQMS_DEMO_DB", APPROVED_DEMO_DATABASES.get(DEMO_INSTANCE, ""))
EXPECTED_ADMIN_LOGIN = os.getenv("PMQMS_DEMO_ADMIN_LOGIN", "admin")
EXPECTED_QMS_PERSONAS = {
    "Quality Manager": os.getenv("PMQMS_DEMO_QUALITY_MANAGER_LOGIN", "olivia.parker.demo@perfectmatch.local"),
    "Quality Supervisor": "daniel.brooks.demo@perfectmatch.local",
    "Document Controller": "maria.lewis.demo@perfectmatch.local",
    "Internal Auditor": "james.carter.demo@perfectmatch.local",
    "Process Owner": "emma.reed.demo@perfectmatch.local",
    "Management User": "michael.stone.demo@perfectmatch.local",
    "QMS Viewer": "qms.viewer.demo@perfectmatch.local",
}
ROLE_DEMO_READ_CHECKS = {
    "Quality Manager": ("pm.qms.document", "pm.qms.risk", "pm.qms.capa", "pm.qms.audit", "pm.qms.kpi", "pm.qms.management.review"),
    "Quality Supervisor": ("pm.qms.process", "pm.qms.risk", "pm.qms.capa", "pm.qms.nonconformity", "pm.qms.equipment"),
    "Document Controller": ("pm.qms.document", "pm.qms.document.revision", "pm.qms.evidence", "pm.qms.document.acknowledgment"),
    "Internal Auditor": ("pm.qms.audit", "pm.qms.audit.finding", "pm.qms.audit.evidence", "pm.qms.document", "pm.qms.risk"),
    "Process Owner": ("pm.qms.process", "pm.qms.activity", "pm.qms.nonconformity", "pm.qms.capa", "pm.qms.equipment"),
    "Management User": ("pm.qms.kpi", "pm.qms.management.review", "pm.qms.risk", "pm.qms.capa"),
    "QMS Viewer": ("pm.qms.document", "pm.qms.risk", "pm.qms.capa", "pm.qms.audit"),
}
EXPECTED_PERSONA_SITE_CODES = {
    "Quality Manager": {"APEX-HQ", "APEX-MFG", "APEX-INS"},
    "Quality Supervisor": {"APEX-HQ"},
    "Document Controller": {"APEX-HQ", "APEX-MFG", "APEX-INS"},
    "Internal Auditor": {"APEX-HQ", "APEX-MFG", "APEX-INS"},
    "Process Owner": {"APEX-HQ", "APEX-MFG"},
    "Management User": {"APEX-HQ", "APEX-MFG", "APEX-INS"},
    "QMS Viewer": {"APEX-HQ", "APEX-MFG", "APEX-INS"},
}
CANONICAL_APEX_PROCESS_CODES = (
    "APEX-LEAD",
    "APEX-QMS",
    "APEX-CUST",
    "APEX-SUP",
    "APEX-REC",
    "APEX-PROD",
    "APEX-FIN",
    "APEX-SHIP",
    "APEX-DOC",
    "APEX-AUD",
    "APEX-TRN",
    "APEX-CAL",
    "APEX-ESD",
    "APEX-SMT",
    "APEX-ASM",
    "APEX-ETEST",
    "APEX-NC",
    "APEX-CAPA",
    "APEX-TRACE",
    "APEX-RECV",
    "APEX-DISP",
)
def validate_demo_database(instance_name, configured_db, actual_db):
    """Allow validation only for explicitly approved Demo instance/database pairs."""
    expected_db = APPROVED_DEMO_DATABASES.get(instance_name)
    if not expected_db or configured_db != expected_db or actual_db != expected_db:
        raise RuntimeError(
            f"Demo validation refused for instance {instance_name!r} and database {actual_db!r}; "
            "only approved Demo instance/database pairs are allowed."
        )
    return expected_db


validate_demo_database(DEMO_INSTANCE, EXPECTED_DB, env.cr.dbname)

errors = []
summary = {}

def require(condition, message):
    if not condition:
        errors.append(message)

def count(model_name, domain=None):
    if model_name not in env:
        errors.append(f"missing model: {model_name}")
        return 0
    total = env[model_name].search_count(domain or [])
    summary[model_name] = total
    return total


def relation_id(record, field_name):
    value = getattr(record, field_name, False)
    return value.id if value else False


def duplicate_groups(records, field_name):
    grouped = {}
    for record in records:
        grouped.setdefault(relation_id(record, field_name), []).append(record.id)
    return {key: ids for key, ids in grouped.items() if len(ids) > 1}

organization = env["pm.qms.organization"].search([("code", "=", "APEX")], limit=1) if "pm.qms.organization" in env else False
require(bool(organization), "APEX organization missing")
if organization:
    require("Apex Precision Electronics" in organization.name, "APEX organization does not use the guided fictional electronics company name")
    require(not env["pm.qms.organization"].search_count([("name", "ilike", "Oliva Torras"), ("company_id", "=", organization.company_id.id)]), "Oliva name found inside demo company organizations")

if "pm.qms.site" in env and organization:
    sites = env["pm.qms.site"].search([("organization_id", "=", organization.id)])
    summary["pm.qms.site"] = len(sites)
    expected_sites = {
        "APEX-HQ": "Manufacturing Plant",
        "APEX-MFG": "Electrical Test Laboratory",
        "APEX-INS": "Warehouse & Receiving",
    }
    require(len(sites) == 3, f"expected exactly 3 Apex demo sites, found {len(sites)}")
    require(
        {site.code: site.name for site in sites} == expected_sites,
        "Apex demo sites do not match the canonical three-site seed",
    )
    require(sum(1 for site in sites if site.active and site.is_primary) == 1, "expected exactly one active primary demo site")
    require(all(site.company_id == organization.company_id for site in sites), "demo site company alignment failed")
    for code in expected_sites:
        duplicates = env["pm.qms.site"].search_count(
            [("organization_id", "=", organization.id), ("code", "=", code)]
        )
        require(duplicates == 1, f"site idempotency failed for {code}: {duplicates}")
elif "pm.qms.site" not in env:
    errors.append("missing model: pm.qms.site")

org_domain = [("organization_id", "=", organization.id)] if organization else []
company_domain = [("company_id", "=", organization.company_id.id)] if organization else []

require(count("pm.qms.process", org_domain) >= 10, "expected at least 10 demo processes")
if "pm.qms.process" in env and organization:
    process_model = env["pm.qms.process"].with_context(active_test=False)
    for process_code in CANONICAL_APEX_PROCESS_CODES:
        matches = process_model.search(org_domain + [("code", "=", process_code)])
        require(
            len(matches) == 1 and matches.active,
            f"canonical Apex process must exist exactly once and be active: {process_code}",
        )
    summary["canonical_apex_processes"] = len(
        process_model.search(
            org_domain + [("code", "in", list(CANONICAL_APEX_PROCESS_CODES))]
        )
    )
require(count("pm.qms.document", org_domain) >= 13, "expected guided examples for all canonical controlled documents")
require(count("pm.qms.evidence", org_domain) >= 13, "expected linked synthetic evidence references for every canonical document")
require(count("pm.qms.risk", org_domain) >= 8, "expected guided electrical, supplier, ESD, calibration, and traceability risks")
require(count("pm.qms.nonconformity", org_domain) >= 2, "expected dimensional/electrical and SMT nonconformity examples")
require(count("pm.qms.capa", org_domain) >= 3, "expected draft, in-progress, and closed linked CAPA examples")
if "pm.qms.capa" in env and organization:
    capa_states = set(env["pm.qms.capa"].search(org_domain).mapped("state"))
    summary["guided_capa_states"] = ",".join(sorted(capa_states))
    require({"draft", "implementation", "closed"} <= capa_states, "expected draft, implementation, and closed CAPA workflow states")
require(count("pm.qms.audit", org_domain) >= 1, "expected demo audit")
require(count("pm.qms.audit.program", org_domain) >= 1, "expected an annual audit program")
require(count("pm.qms.audit.finding", org_domain) >= 1, "expected demo audit findings")
require(count("pm.qms.audit.scope", org_domain) >= 1, "expected an audit scope example")
require(count("pm.qms.audit.plan.line", org_domain) >= 1, "expected an audit plan example")
require(count("pm.qms.audit.criterion", org_domain) >= 1, "expected an audit criterion example")
require(count("pm.qms.audit.evidence", org_domain) >= 1, "expected linked audit evidence")
require(count("pm.qms.capa.fishbone", org_domain) >= 1, "expected CAPA fishbone analysis example")
require(count("pm.qms.capa.is.is.not", org_domain) >= 4, "expected the four fixed CAPA Is/Is Not dimensions")
require(count("pm.qms.capa.action", org_domain) >= 3, "expected multiple linked CAPA actions")
if "pm.qms.iso9001.gap.assessment" in env and organization:
    guided_transition_assessment = env["pm.qms.iso9001.gap.assessment"].search(
        [
            ("name", "=", "Apex ISO 9001:2015 to 2026 guided gap assessment"),
            ("company_id", "=", organization.company_id.id),
        ],
        limit=1,
    )
    require(bool(guided_transition_assessment), "expected guided ISO 9001 transition gap assessment")
    if guided_transition_assessment:
        require(guided_transition_assessment.state == "completed", "guided ISO 9001 gap assessment must be completed")
        transition_actions = env["pm.qms.iso9001.transition.action"].search(
            [("assessment_id", "=", guided_transition_assessment.id)]
        )
        summary["pm.qms.iso9001.transition.action"] = len(transition_actions)
        require(len(transition_actions) == 2, "expected exactly two guided ISO 9001 transition actions")
        require(
            set(transition_actions.mapped("source_status_snapshot")) == {"partial", "gap"},
            "guided ISO 9001 transition actions must preserve partial and gap source snapshots",
        )
        require(
            all(action.implementation_project_id for action in transition_actions),
            "guided ISO 9001 transition actions must link to the implementation project",
        )
        transition_review = env["pm.qms.iso9001.transition.review"].search(
            [("assessment_id", "=", guided_transition_assessment.id)], limit=1
        )
        summary["pm.qms.iso9001.transition.review"] = int(bool(transition_review))
        require(bool(transition_review), "expected guided ISO 9001 transition readiness review")
        if transition_review:
            require(transition_review.state == "submitted", "guided transition readiness review must be submitted")
            require(
                transition_review.reviewer_id.login
                == "daniel.brooks.demo@perfectmatch.local",
                "guided transition readiness review must use the independent Quality Supervisor",
            )
            require(
                transition_review.total_action_count_snapshot == 2
                and transition_review.open_action_count_snapshot == 2,
                "guided transition readiness review action snapshot is inconsistent",
            )
            require(
                transition_review.implementation_project_id
                == transition_actions.mapped("implementation_project_id"),
                "guided transition readiness review project alignment failed",
            )
require(count("pm.qms.objective", org_domain) >= 1, "expected demo objective")
require(count("pm.qms.kpi", company_domain) >= 8, "expected KPI examples for yield, suppliers, NCR/CAPA, and customer satisfaction")
require(count("pm.qms.kpi.measurement", company_domain) >= 32, "expected four synthetic historical/current measurements for eight KPIs")
require(count("pm.qms.person", org_domain) >= 4, "expected demo people")
require(count("pm.qms.training.record", org_domain) >= 7, "expected training status for all seven demo personas")
require(count("pm.qms.training.event", org_domain) >= 1, "expected a training event")
require(count("pm.qms.training.requirement", company_domain) >= 1, "expected a role-linked training requirement")
require(count("pm.qms.competency.matrix.line", org_domain) >= 1, "expected role competency matrix lines")
require(count("pm.qms.qualification.record", org_domain) >= 7, "expected qualification status for all seven demo personas")
require(count("pm.qms.equipment", org_domain) >= 5, "expected analyzer, multimeter, ESD meter, torque driver, and oscilloscope examples")
require(count("pm.qms.calibration.event", org_domain) >= 5, "expected failed, overdue, due-soon, current, and in-progress calibration events")
require(count("pm.qms.calibration.impact.assessment", org_domain) >= 1, "expected an out-of-tolerance impact assessment")
require(count("pm.qms.calibration.measurement.line", org_domain) >= 3, "expected calibration measurement evidence lines")
require(count("pm.qms.customer.complaint", org_domain) >= 1, "expected demo customer complaint")
require(count("pm.qms.quality.alert", org_domain) >= 1, "expected demo quality alert")
require(count("pm.qms.eight.d", org_domain) >= 1, "expected demo 8D")
require(count("pm.qms.supplier.issue", org_domain) >= 2, "expected multiple supplier quality scenarios")
require(count("pm.qms.scar", org_domain) >= 2, "expected linked supplier corrective action requests")
require(count("pm.qms.supplier.evaluation", org_domain) >= 2, "expected supplier evaluation records")
require(count("pm.qms.customer.satisfaction", org_domain) >= 1, "expected customer satisfaction measurement")
require(count("pm.qms.customer.performance", org_domain) >= 1, "expected customer performance scorecard")
require(count("pm.qms.supplier.performance", org_domain) >= 2, "expected supplier performance scorecards")
require(count("pm.qms.equipment.type", company_domain) >= 1, "expected a monitoring resource type")
require(count("pm.qms.calibration.provider", company_domain) >= 1, "expected a calibration provider")
if "pm.qms.equipment" in env and organization:
    equipment_states = set(env["pm.qms.equipment"].search(org_domain).mapped("calibration_status"))
    summary["guided_equipment_states"] = ",".join(sorted(equipment_states))
    require({"overdue", "due_soon", "current", "quarantined", "out_for_calibration"} <= equipment_states, "expected overdue, due-soon, current, quarantined, and in-calibration equipment examples")
require(count("pm.qms.root.cause.analysis", org_domain) >= 1, "expected a linked root-cause analysis")
require(count("pm.qms.root.cause.line", org_domain) >= 5, "expected five linked root-cause analysis lines")
require(count("pm.qms.management.review", org_domain) >= 1, "expected demo management review")
require(count("pm.qms.management.review.input", org_domain) >= 8, "expected cross-functional Management Review inputs")

# Keep the static menu inventory and runtime fixture contract in lockstep.
for model_name, fixture_anchor in GUIDED_MODEL_EXAMPLES.items():
    if model_name in env:
        total = env[model_name].search_count([])
        summary[f"guided_menu_example.{model_name}"] = total
        require(total > 0, f"functional menu has no demo example: {model_name} ({fixture_anchor})")
    else:
        errors.append(f"functional menu model is not installed: {model_name}")

# Dashboard screens are transient/computed; validate their persistent source
# records rather than expecting a database row that Odoo may vacuum.
for transient_model, fixture_anchor in GUIDED_TRANSIENT_MODEL_EXAMPLES.items():
    if transient_model == "pm.qms.dashboard":
        for source_model in ("pm.qms.kpi", "pm.qms.risk", "pm.qms.capa", "pm.qms.audit", "pm.qms.equipment", "pm.qms.action.center.line"):
            if source_model not in env:
                errors.append(f"dashboard source model is not installed: {source_model}")
                continue
            source_count = env[source_model].search_count([])
            summary[f"dashboard_source.{source_model}"] = source_count
            require(source_count > 0, f"computed dashboard source is empty: {source_model} ({fixture_anchor})")

if "pm.qms.license" in env:
    license_record = env["pm.qms.license"].search([("is_current", "=", True)], order="id desc", limit=1)
    require(bool(license_record), "current Demo commercial license missing")
    if license_record:
        summary["license.state"] = license_record.state
        summary["license.environment"] = license_record.environment_short
        summary["license.company"] = f"{license_record.company_usage}/{license_record.company_limit}"
        summary["license.site"] = f"{license_record.site_usage}/{license_record.site_limit}"
        summary["license.named_user"] = f"{license_record.named_user_usage}/{license_record.named_user_limit}"
        require(license_record.state in ("valid", "expiring"), f"Demo commercial license is not usable: {license_record.state}")
        require(license_record.company_usage == 1, "Demo license usage must report one operational company")
        require(license_record.site_usage == 3, "Demo license usage must report three active sites")
        require((license_record.company_limit, license_record.site_limit, license_record.named_user_limit) == (1, 3, 7), "Demo license limits must be exactly 1/3/7")
        require(license_record.site_usage <= license_record.site_limit, "Demo site entitlement is exceeded")
        require(license_record.named_user_usage <= license_record.named_user_limit, "Demo named-user entitlement is exceeded")
        try:
            signed_payload = json.loads(license_record.payload_json or "{}")
        except (TypeError, ValueError):
            signed_payload = {}
            errors.append("current license signed payload is not valid JSON")
        environment_id = read_environment_id()
        require(bool(environment_id) and license_record.environment_id == environment_id, "Demo license UUID does not match this instance")
        if DEMO_INSTANCE == "demo2":
            require(license_record.key_id == "pmqms-demo-2026-v3", "Demo2 must use the approved v3 Demo/QA authority")
            require(signed_payload.get("deployment_scope") == "demo-qa", "Demo2 license scope must be demo-qa")
else:
    errors.append("missing model: pm.qms.license")


if "pm.qms.training.record" in env and "pm.qms.training.course" in env and organization:
    course = env["pm.qms.training.course"].search(
        [("code", "=", "APEX-TRN-001"), ("company_id", "=", organization.company_id.id)],
        limit=1,
    )
    if course:
        training_records = env["pm.qms.training.record"].search(
            org_domain + [("course_id", "=", course.id)]
        )
        training_duplicates = duplicate_groups(training_records, "person_id")
        summary["canonical_training_duplicate_groups"] = len(training_duplicates)
        require(
            not training_duplicates,
            "duplicate canonical Demo training records detected",
        )


if "pm.qms.qualification.record" in env and "pm.qms.qualification.type" in env and organization:
    qualification_type = env["pm.qms.qualification.type"].search(
        [("code", "=", "APEX-QUAL-001"), ("company_id", "=", organization.company_id.id)],
        limit=1,
    )
    if qualification_type:
        qualification_records = env["pm.qms.qualification.record"].search(
            org_domain + [("qualification_type_id", "=", qualification_type.id)]
        )
        qualification_duplicates = duplicate_groups(qualification_records, "person_id")
        summary["canonical_qualification_duplicate_groups"] = len(qualification_duplicates)
        require(
            not qualification_duplicates,
            "duplicate canonical Demo qualification records detected",
        )

if "pm.qms.capa" in env and "pm.qms.capa.why" in env and organization:
    capa = env["pm.qms.capa"].search([("code", "=", "APEX-CAPA-001"), ("organization_id", "=", organization.id)], limit=1)
    if capa:
        why_rows = env["pm.qms.capa.why"].search([("capa_id", "=", capa.id)])
        by_sequence = {}
        for row in why_rows:
            by_sequence.setdefault(row.sequence, []).append(row.id)
        summary["canonical_capa_why_count"] = len(why_rows)
        summary["canonical_capa_why_sequences"] = sorted(by_sequence)
        require(len(why_rows) == 5, f"canonical CAPA must contain exactly five 5 Why rows, found {len(why_rows)}")
        require(set(by_sequence) == {1, 2, 3, 4, 5}, "canonical CAPA 5 Why sequences must be exactly 1 through 5")
        require(all(len(ids) == 1 for ids in by_sequence.values()), "duplicate canonical CAPA 5 Why sequence detected")

for role, login in EXPECTED_QMS_PERSONAS.items():
    persona = env["res.users"].search([("login", "=", login)], limit=1)
    require(bool(persona), f"Demo persona missing: {role}")
    if persona:
        require(not persona.has_group("base.group_system"), f"QMS persona is System Administrator: {role}")
        for model_name in ROLE_DEMO_READ_CHECKS.get(role, ()):
            if model_name not in env:
                errors.append(f"missing role-visible model for {role}: {model_name}")
                continue
            try:
                visible_count = env[model_name].with_user(persona).search_count([])
            except Exception as exc:
                visible_count = 0
                errors.append(f"role read failed for {role} on {model_name}: {exc.__class__.__name__}")
            summary[f"role_visible.{role}.{model_name}"] = visible_count
            require(visible_count > 0, f"expected a visible guided example for {role} in {model_name}")
        if role == "Quality Manager":
            for model_name in GUIDED_MODEL_EXAMPLES:
                try:
                    visible_count = env[model_name].with_user(persona).search_count([])
                except Exception as exc:
                    visible_count = 0
                    errors.append(f"full organization read failed for Quality Manager on {model_name}: {exc.__class__.__name__}")
                require(visible_count > 0, f"Quality Manager must see a guided example in {model_name}")
        if "qms_effective_site_ids" in persona._fields and "pm.qms.equipment" in env:
            effective_site_ids = set(persona.qms_effective_site_ids.ids)
            effective_site_codes = set(persona.qms_effective_site_ids.mapped("code"))
            visible_equipment = env["pm.qms.equipment"].with_user(persona).search([])
            visible_site_ids = {record.site_id.id for record in visible_equipment if record.site_id}
            summary[f"site_scope.{role}.assigned"] = len(effective_site_ids)
            summary[f"site_scope.{role}.visible_equipment_sites"] = len(visible_site_ids)
            require(bool(visible_equipment), f"expected in-scope equipment examples for {role}")
            require(visible_site_ids <= effective_site_ids, f"equipment site isolation failed for {role}")
            require(effective_site_codes == EXPECTED_PERSONA_SITE_CODES[role], f"configured site scope mismatch for {role}")

canonical_cost_lines = 0
if "pm.qms.cost.event" in env:
    expected_cost_lines = {"APEX-CQ-001": 4, "APEX-CQ-002": 2}
    cost_events = env["pm.qms.cost.event"].search(
        org_domain + [("code", "in", list(expected_cost_lines))]
    )
    confirmed_events = sum(1 for event in cost_events if event.state == "confirmed")
    summary["pm.qms.cost.event.confirmed"] = confirmed_events
    require(len(cost_events) == 2, "expected both canonical Cost of Quality events")
    require(confirmed_events == 2, "expected both canonical Cost of Quality events confirmed")
    for code, expected_lines in expected_cost_lines.items():
        event = cost_events.filtered(lambda candidate: candidate.code == code)
        line_count = sum(len(candidate.line_ids) for candidate in event)
        summary[f"cost_lines.{code}"] = line_count
        canonical_cost_lines += line_count
        require(bool(event), f"missing canonical Cost of Quality event: {code}")
        require(line_count == expected_lines, f"expected {expected_lines} lines for {code}, found {line_count}")
    summary["pm.qms.cost.line.canonical"] = canonical_cost_lines
else:
    errors.append("missing model: pm.qms.cost.event")
if "pm.qms.cost.line" in env:
    lines = env["pm.qms.cost.line"].search_count(org_domain)
    summary["pm.qms.cost.line"] = lines
    require(lines >= 6, "expected six Cost of Quality lines")
    require(canonical_cost_lines == 6, "expected six canonical Cost of Quality lines")
else:
    errors.append("missing model: pm.qms.cost.line")

if "pm.qms.action.center.line" in env and organization:
    demo_user = env["res.users"].search(
        [("login", "=", EXPECTED_QMS_PERSONAS["Quality Manager"])], limit=1
    )
    values = env["pm.qms.action.center.line"].with_user(demo_user or env.user)._collect_action_values(organization)
    summary["pm.qms.action.center.source_values"] = len(values)
    require(len(values) >= 8, "expected source-driven Action Center values")
    source_types = sorted(set(v.get("source_model") for v in values if v.get("source_model")))
    summary["pm.qms.action.center.source_types"] = ",".join(source_types)
    require(len(source_types) >= 6, "expected multiple Action Center source types")
else:
    errors.append("missing model: pm.qms.action.center.line")

# Idempotency checks for stable demo keys.
for model_name, field, value in [
    ("pm.qms.organization", "code", "APEX"),
    ("pm.qms.process", "code", "APEX-FIN"),
    ("pm.qms.nonconformity", "code", "APEX-NCR-001"),
    ("pm.qms.capa", "code", "APEX-CAPA-001"),
    ("pm.qms.cost.event", "code", "APEX-CQ-001"),
]:
    if model_name in env and field in env[model_name]._fields:
        duplicates = env[model_name].search_count([(field, "=", value)] + ([("organization_id", "=", organization.id)] if organization and "organization_id" in env[model_name]._fields else []))
        summary[f"duplicate_check.{model_name}.{value}"] = duplicates
        require(duplicates == 1, f"idempotency failed for {model_name} {value}: {duplicates}")

print("DEMO_VALIDATION_SUMMARY")
for key in sorted(summary):
    print(f"{key}={summary[key]}")
if errors:
    print("DEMO_VALIDATION_ERRORS")
    for error in errors:
        print(error)
    raise RuntimeError(f"Demo validation failed with {len(errors)} error(s)")
print("demo_validation=pass")
