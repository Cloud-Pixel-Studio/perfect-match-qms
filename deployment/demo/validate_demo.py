import os

EXPECTED_DB = os.getenv("PMQMS_DEMO_DB", "pmqms_demo")
if EXPECTED_DB != "pmqms_demo" or env.cr.dbname != "pmqms_demo":
    raise RuntimeError(f"Demo validation refused for database {env.cr.dbname!r}; only pmqms_demo is allowed.")

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

organization = env["pm.qms.organization"].search([("code", "=", "APEX")], limit=1) if "pm.qms.organization" in env else False
require(bool(organization), "APEX organization missing")
if organization:
    require("Apex Precision Systems" in organization.name, "APEX organization does not use fictional demo company name")
    require(not env["pm.qms.organization"].search_count([("name", "ilike", "Oliva Torras"), ("company_id", "=", organization.company_id.id)]), "Oliva name found inside demo company organizations")

org_domain = [("organization_id", "=", organization.id)] if organization else []
company_domain = [("company_id", "=", organization.company_id.id)] if organization else []

require(count("pm.qms.process", org_domain) >= 10, "expected at least 10 demo processes")
require(count("pm.qms.document", org_domain) >= 5, "expected demo documents")
require(count("pm.qms.evidence", org_domain) >= 3, "expected demo evidence")
require(count("pm.qms.risk", org_domain) >= 2, "expected demo risks")
require(count("pm.qms.nonconformity", org_domain) >= 1, "expected demo NCR")
require(count("pm.qms.capa", org_domain) >= 1, "expected demo CAPA")
require(count("pm.qms.audit", org_domain) >= 1, "expected demo audit")
require(count("pm.qms.audit.finding", org_domain) >= 1, "expected demo audit findings")
require(count("pm.qms.objective", org_domain) >= 1, "expected demo objective")
require(count("pm.qms.kpi.measurement", company_domain) >= 3, "expected demo KPI measurements")
require(count("pm.qms.person", org_domain) >= 4, "expected demo people")
require(count("pm.qms.training.record", org_domain) >= 3, "expected demo training records")
require(count("pm.qms.qualification.record", org_domain) >= 3, "expected demo qualification records")
require(count("pm.qms.equipment", org_domain) >= 4, "expected demo equipment")
require(count("pm.qms.customer.complaint", org_domain) >= 1, "expected demo customer complaint")
require(count("pm.qms.quality.alert", org_domain) >= 1, "expected demo quality alert")
require(count("pm.qms.eight.d", org_domain) >= 1, "expected demo 8D")
require(count("pm.qms.supplier.issue", org_domain) >= 1, "expected demo supplier issue")
require(count("pm.qms.scar", org_domain) >= 1, "expected demo SCAR")
require(count("pm.qms.management.review", org_domain) >= 1, "expected demo management review")

if "pm.qms.cost.event" in env:
    confirmed_events = env["pm.qms.cost.event"].search_count(org_domain + [("state", "=", "confirmed")])
    summary["pm.qms.cost.event.confirmed"] = confirmed_events
    require(confirmed_events >= 1, "expected confirmed Cost of Quality events")
else:
    errors.append("missing model: pm.qms.cost.event")
if "pm.qms.cost.line" in env:
    lines = env["pm.qms.cost.line"].search_count(org_domain)
    summary["pm.qms.cost.line"] = lines
    require(lines >= 4, "expected Cost of Quality lines")
else:
    errors.append("missing model: pm.qms.cost.line")

if "pm.qms.action.center.line" in env and organization:
    demo_user = env["res.users"].search([("login", "=", "demo.qm@perfectmatch.local")], limit=1)
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
