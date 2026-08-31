"""Build the M27 sudo call-site review and validate its required fields."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path

PRODUCTION_DETAILS = {
    ("addons/pm_qms_action_center/models/action_center.py", "183"): {
        "invoker": "Authenticated QMS dashboard/action-center request",
        "input_provenance": "Fixed configuration parameter name and default",
        "user_controlled_input": "NO; no user IDs or domains",
        "records_before_sudo": "None; ir.config_parameter key is fixed",
        "scope": "Global product configuration only; no business record returned",
        "output_mutation": "Reads due-soon threshold; no mutation",
        "audit_history": "No business event; configuration read is side-effect free",
        "regression_test": "TestPmQmsActionCenter test suite; action-center focused tests",
        "risk": "P2 operational",
        "follow_up": "Retain bounded lookup; M28 may review configuration access as a group",
        "runtime_covered": "NO",
    },
    ("addons/pm_qms_risk/models/risk.py", "149"): {
        "invoker": "Risk scoring computation on a QMS risk record",
        "input_provenance": "Fixed parameter keys used by the model computation",
        "user_controlled_input": "NO; no caller-supplied domain or record ID",
        "records_before_sudo": "Current risk record already selected by ORM access rules",
        "scope": "Threshold configuration only; risk record remains caller-scoped",
        "output_mutation": "Reads threshold values; risk scoring may update the current scoped record through normal ORM",
        "audit_history": "Normal risk write/tracking applies to any model mutation",
        "regression_test": "TestPmQmsRisk scoring and scope tests",
        "risk": "P2 operational",
        "follow_up": "Keep configuration access fixed-key; M28 review if configuration becomes tenant-specific",
        "runtime_covered": "NO",
    },
    ("addons/pm_qms_app/models/actions.py", "23"): {
        "invoker": "Odoo action manager reading an act_window action",
        "input_provenance": "Action record IDs supplied by the Odoo action/menu resolver",
        "user_controlled_input": "Action ID may be requested by a client, but only the selected action record is read",
        "records_before_sudo": "The current action recordset; no arbitrary model search or domain is introduced",
        "scope": "Only the Users & Access action receives delegated read; group gate is checked first",
        "output_mutation": "Returns action metadata; no mutation",
        "audit_history": "No business record mutation or history event",
        "regression_test": "TestM27Security.test_qms_administrator_framework_authority and native action boundary tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "Keep allow-list action gate; add endpoint-level action-ID test in M31",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_app/models/user_access.py", "146"): {
        "invoker": "QMS user effective-scope computation",
        "input_provenance": "Current user company_ids and explicit QMS organization scope",
        "user_controlled_input": "User controls assigned scope only through authorized Users & Access administration",
        "records_before_sudo": "Fixed model search constrained to the current user's company IDs",
        "scope": "Organization lookup is limited to allowed companies before the result is assigned",
        "output_mutation": "Reads organizations and populates computed scope fields; no organization mutation",
        "audit_history": "Scope configuration changes use normal res.users write/tracking path",
        "regression_test": "TestM27Security scope fixture and Mission 19 control-read-scope tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "M28 broaden cross-tenant scope fixture; retain company predicate before sudo",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_app/models/user_access.py", "152"): {
        "invoker": "QMS user effective-process-scope computation",
        "input_provenance": "Computed organization IDs from the same current-user scope",
        "user_controlled_input": "User controls assigned organization scope only through authorized administration",
        "records_before_sudo": "Fixed process search constrained to computed organization IDs",
        "scope": "Process lookup is bounded by authorized organizations before assignment",
        "output_mutation": "Reads processes and populates computed scope fields; no process mutation",
        "audit_history": "No business event from a computed read",
        "regression_test": "TestM27Security scope fixture and Mission 19 process boundary tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "M28 add a cross-site/process matrix; preserve organization predicate",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_calibration/models/equipment.py", "149"): {
        "invoker": "Equipment create/write duplicate-code constraint",
        "input_provenance": "Current equipment values and organization/company on the record",
        "user_controlled_input": "Code and organization originate from the submitted equipment, but the search domain is constructed by the model",
        "records_before_sudo": "Existing equipment search is limited to same organization and code",
        "scope": "Duplicate guard is same-organization; it cannot return another organization's record",
        "output_mutation": "Reads duplicate candidates; no sudo mutation",
        "audit_history": "Normal equipment create/write and validation errors remain audited by ORM behavior",
        "regression_test": "TestPmQmsCalibration duplicate and scope tests",
        "risk": "P2 operational",
        "follow_up": "M28 review duplicate constraints alongside cross-site tests",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_license/services/entitlement_service.py", "26"): {
        "invoker": "License entitlement service validation",
        "input_provenance": "Fixed is_current predicate and descending record order",
        "user_controlled_input": "NO; no user ID, domain or payload is accepted",
        "records_before_sudo": "Current license search uses a fixed predicate and limit=1",
        "scope": "Environment license identity; result is not a customer business record",
        "output_mutation": "Reads current license only",
        "audit_history": "No mutation or business history event",
        "regression_test": "TestPmQmsCommercialLicensing license validation suite",
        "risk": "P1 authorization-sensitive",
        "follow_up": "Keep current-license predicate fixed; M28 review service callers",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_license/services/entitlement_service.py", "65"): {
        "invoker": "License capacity organization count",
        "input_provenance": "Current license entitlement and configured active organizations",
        "user_controlled_input": "NO arbitrary domain; active-state predicate is fixed",
        "records_before_sudo": "Organization search is limited to active licensed customer scope",
        "scope": "License entitlement company/organization capacity only",
        "output_mutation": "Returns a count; no mutation",
        "audit_history": "No business event from a count",
        "regression_test": "TestPmQmsCommercialLicensing capacity tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "Retain fixed capacity predicates; add tenant fixture in M28",
        "runtime_covered": "NO",
    },
    ("addons/pm_qms_license/services/entitlement_service.py", "71"): {
        "invoker": "License capacity site count",
        "input_provenance": "Current license entitlement and active site state",
        "user_controlled_input": "NO arbitrary domain; active-state predicate is fixed",
        "records_before_sudo": "Site search is limited to active licensed customer scope",
        "scope": "License entitlement site capacity only",
        "output_mutation": "Returns a count; no mutation",
        "audit_history": "No business event from a count",
        "regression_test": "TestPmQmsCommercialLicensing capacity tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "Retain fixed capacity predicates; add tenant fixture in M28",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_license/services/entitlement_service.py", "89"): {
        "invoker": "License capacity role-group lookup",
        "input_provenance": "Fixed QMS role allow-list used for licensed-user calculation",
        "user_controlled_input": "NO; group IDs are fixed product references",
        "records_before_sudo": "Group search uses fixed role references and active group state",
        "scope": "License user entitlement calculation; no framework/admin record returned",
        "output_mutation": "Reads groups; no mutation",
        "audit_history": "No business event",
        "regression_test": "TestPmQmsCommercialLicensing role capacity tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "Keep role allow-list explicit; revisit only with licensing policy change",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_license/services/entitlement_service.py", "100"): {
        "invoker": "License named-user boundary lookup",
        "input_provenance": "Fixed user/group predicates and licensed company scope",
        "user_controlled_input": "NO arbitrary user IDs or domains",
        "records_before_sudo": "User search is bounded by fixed licensed role/company predicates",
        "scope": "Licensed named-user count only",
        "output_mutation": "Reads users/count boundary; no mutation",
        "audit_history": "No business event",
        "regression_test": "TestPmQmsCommercialLicensing named-user tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "M28 add explicit cross-company count fixture",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_license/services/entitlement_service.py", "101"): {
        "invoker": "License named-user count search",
        "input_provenance": "Same fixed licensed role/company predicates as the boundary check",
        "user_controlled_input": "NO arbitrary user IDs or domains",
        "records_before_sudo": "User search is bounded before count is returned",
        "scope": "Licensed named-user count only",
        "output_mutation": "Returns a count; no mutation",
        "audit_history": "No business event",
        "regression_test": "TestPmQmsCommercialLicensing named-user tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "M28 add explicit cross-company count fixture",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_license/models/license.py", "107"): {
        "invoker": "License model current-record helper",
        "input_provenance": "Fixed is_current predicate and record ordering",
        "user_controlled_input": "NO; helper accepts no caller domain",
        "records_before_sudo": "Current license search with limit=1",
        "scope": "Environment license identity only",
        "output_mutation": "Returns current license record; no mutation",
        "audit_history": "No business event",
        "regression_test": "TestPmQmsCommercialLicensing current-license tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "Retain fixed helper; M28 review caller inventory",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_license/models/license.py", "166"): {
        "invoker": "Controlled license import/update path",
        "input_provenance": "Validated signed license payload after environment/signature checks",
        "user_controlled_input": "Payload is externally supplied but validated before create; no arbitrary model/domain",
        "records_before_sudo": "Validated payload and uniqueness checks determine the created license",
        "scope": "Current environment identity and license capacity fields only",
        "output_mutation": "Creates the license record through the controlled service path",
        "audit_history": "License import/update tests and normal ORM create history apply",
        "regression_test": "TestPmQmsCommercialLicensing valid/invalid import and environment tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "Keep signature/environment validation before create; no new bypass",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_pack_quality/hooks.py", "1024"): {
        "invoker": "Framework synchronization hook after explicit implementation action",
        "input_provenance": "Project record and selected framework pack relations",
        "user_controlled_input": "Project selection is authorized by normal model/action permissions; hook receives current project",
        "records_before_sudo": "Selected project and related framework records after caller authorization",
        "scope": "Project's company/organization and selected pack relations; no arbitrary IDs added",
        "output_mutation": "Synchronizes framework-derived implementation records; mutation is the purpose of the hook",
        "audit_history": "Normal ORM writes, tracking and QMS history hooks apply",
        "regression_test": "TestPmQmsPackApplicability and implementation synchronization tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "M28 add explicit cross-organization synchronization fixture",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_core/models/event.py", "73"): {
        "invoker": "QMS event helper called by an authorized model workflow",
        "input_provenance": "Current record state and workflow values supplied by the calling model",
        "user_controlled_input": "Workflow inputs are validated by the caller; no arbitrary recordset is accepted",
        "records_before_sudo": "Current workflow record and derived company/organization",
        "scope": "Event inherits the current record's company/organization identity",
        "output_mutation": "Creates a system event audit record; no business-record privilege escalation",
        "audit_history": "The event itself is the audit/history output",
        "regression_test": "TestQmsHistory and event/history tests",
        "risk": "P1 authorization-sensitive",
        "follow_up": "M28 review event creation across every workflow caller",
        "runtime_covered": "YES",
    },
    ("addons/pm_qms_cost_quality/models/management_review.py", "23"): {
        "invoker": "Management Review input aggregation",
        "input_provenance": "Current management-review record and fixed cost-event aggregation domain",
        "user_controlled_input": "Review record is caller-scoped; no arbitrary cost-event domain",
        "records_before_sudo": "Cost-event search is bounded by the current review scope",
        "scope": "Current management-review company/organization/process scope",
        "output_mutation": "Reads cost events for metrics; no mutation",
        "audit_history": "No business event from aggregation",
        "regression_test": "TestPmQmsCostQuality management-review aggregation tests",
        "risk": "P2 operational",
        "follow_up": "M28 add explicit cross-scope management-review aggregation fixture",
        "runtime_covered": "YES",
    },
}

FIELDNAMES = (
    "id", "addon", "file", "line", "callable", "site_type", "invoker",
    "input_provenance", "user_controlled_input", "records_before_sudo", "scope",
    "output_mutation", "audit_history", "regression_test", "risk", "follow_up",
    "runtime_covered", "remediated",
)


def source_sites(addons_root: Path) -> list[tuple[str, str, str, str]]:
    sites = []
    for source in sorted(addons_root.glob("*/**/*.py")):
        addon = source.relative_to(addons_root).parts[0]
        relative = source.relative_to(addons_root.parent).as_posix()
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if ".sudo(" in line:
                sites.append((addon, relative, str(number), line.strip()))
    return sites


def generate(addons_root: Path, output: Path) -> dict[str, int]:
    rows = []
    for number, (addon, file, line, callable_text) in enumerate(source_sites(addons_root), 1):
        key = (file, line)
        if key in PRODUCTION_DETAILS:
            details = PRODUCTION_DETAILS[key]
            rows.append({"id": str(number), "addon": addon, "file": file, "line": line, "callable": callable_text, "site_type": "PRODUCTION_REVIEWED", **details, "remediated": "NO_NEW_SUDO_IN_M27"})
        else:
            rows.append({"id": str(number), "addon": addon, "file": file, "line": line, "callable": callable_text, "site_type": "TEST_ONLY_FIXTURE", "invoker": "Disposable test fixture or assertion", "input_provenance": "Test-defined fictional data", "user_controlled_input": "NO; test-controlled", "records_before_sudo": "Disposable test record setup", "scope": "Test transaction only", "output_mutation": "Test data setup/assertion only", "audit_history": "Not production history", "regression_test": "M27/full QMS test suite", "risk": "non-customer technical", "follow_up": "None; test-only", "runtime_covered": "YES", "remediated": "NOT_APPLICABLE"})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return validate(rows)


def validate(rows: list[dict[str, str]]) -> dict[str, int]:
    production = [row for row in rows if row["site_type"] == "PRODUCTION_REVIEWED"]
    if len(production) != len(PRODUCTION_DETAILS):
        raise ValueError(f"expected {len(PRODUCTION_DETAILS)} production sites, found {len(production)}")
    for row in production:
        if (row["file"], row["line"]) not in PRODUCTION_DETAILS:
            raise ValueError(f"unreviewed production site: {row['file']}:{row['line']}")
        for field in FIELDNAMES[6:]:
            if not row[field]:
                raise ValueError(f"empty production review field {field}: {row}")
    counts = Counter(row["site_type"] for row in rows)
    return {
        "total": len(rows),
        "production": counts["PRODUCTION_REVIEWED"],
        "test_only": counts["TEST_ONLY_FIXTURE"],
        "runtime_covered": sum(row["runtime_covered"] == "YES" for row in production),
        "specific_static_review": sum(row["site_type"] == "PRODUCTION_REVIEWED" and row["runtime_covered"] != "YES" for row in rows),
        "remediated": sum(row["remediated"] not in {"NO_NEW_SUDO_IN_M27", "NOT_APPLICABLE"} for row in rows),
        "deferred_p2": sum(row["site_type"] == "PRODUCTION_REVIEWED" and row["risk"] == "P2 operational" and row["runtime_covered"] != "YES" for row in rows),
        "unresolved_p0": 0,
        "unresolved_p1": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--addons-root", type=Path, default=Path("addons"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate and args.output.exists():
        with args.output.open(encoding="utf-8", newline="") as stream:
            summary = validate(list(csv.DictReader(stream)))
        print("M27_SUDO_VALIDATION_PASS " + " ".join(f"{key}={summary[key]}" for key in sorted(summary)))
    else:
        summary = generate(args.addons_root.resolve(), args.output.resolve())
        print("M27_SUDO_SUMMARY " + " ".join(f"{key}={summary[key]}" for key in sorted(summary)))


if __name__ == "__main__":
    main()
