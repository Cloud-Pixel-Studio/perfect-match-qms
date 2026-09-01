#!/usr/bin/env bash
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT" || exit 2

OPENGREP_VERSION="v1.29.0"
OPENGREP_LINUX_X86_SHA256="3365ef49d04893e01338d85d9bbd49b2bd5261ad4c9c0df0a6a0f8d44232ae13"
OPENGREP_WINDOWS_X86_SHA256="ee485b31912704dc6410bc43f04b5c6ad896697db56e360a98204abf95fa1025"
OPENGREP_LINUX_X86_URL="https://github.com/opengrep/opengrep/releases/download/${OPENGREP_VERSION}/opengrep_manylinux_x86"
OPENGREP_WINDOWS_X86_URL="https://github.com/opengrep/opengrep/releases/download/${OPENGREP_VERSION}/opengrep_windows_x86.exe"

TRIVY_VERSION="0.74.0"
TRIVY_LINUX_X86_SHA256="2ae6fe3ee734b7fdf11335663e18c75ea12dccc76062f09f164a3b0f8be4371a"
TRIVY_WINDOWS_X86_SHA256="94c40e0696e4b907a74b7b2e1438d5d72ebaca83115817407f568a002d520842"
TRIVY_LINUX_X86_URL="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
TRIVY_WINDOWS_X86_URL="https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_windows-64bit.zip"

PYLINT_VERSION="4.0.8"
PYLINT_ODOO_VERSION="10.0.11"
PIP_AUDIT_VERSION="2.10.1"

RUN_ID="${PMQMS_SECURITY_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
REPORT_ROOT="${PMQMS_SECURITY_REPORT_ROOT:-$REPO_ROOT/.security-audit/reports}"
REPORT_DIR="$REPORT_ROOT/$RUN_ID"
CACHE_DIR="${PMQMS_SECURITY_CACHE_DIR:-$REPO_ROOT/.security-audit/cache}"
TOOLS_DIR="$CACHE_DIR/tools"
PYTHON_TOOLS_DIR="$CACHE_DIR/python-tools-pylint-${PYLINT_VERSION}-pylint-odoo-${PYLINT_ODOO_VERSION}-pip-audit-${PIP_AUDIT_VERSION}"
SUMMARY_JSON="$REPORT_DIR/summary.json"
EXIT_CODE_FILE="$REPORT_DIR/exit-code.txt"
ENFORCEMENT_MODE="${PMQMS_SECURITY_ENFORCEMENT_MODE:-baseline}"

INFRA_FAILURES=0
POLICY_FAILURES=0
SECRET_FINDINGS=0
PYTHON_BIN=()
PLATFORM="linux"
EXE_SUFFIX=""

EXPECTED_OPENGREP_RULES=(
  pmqms.python.dangerous-eval-exec
  pmqms.python.unsafe-pickle
  pmqms.python.shell-command
  pmqms.python.insecure-token-random
  pmqms.python.external-path-write
  pmqms.odoo.sudo-review
  pmqms.odoo.superuser-elevation
  pmqms.odoo.sql-string-construction
  pmqms.odoo.dynamic-model-access
  pmqms.controller.public-or-none-auth
  pmqms.controller.csrf-disabled
  pmqms.controller.public-request-env-sudo
  pmqms.controller.attachment-sudo-download
  pmqms.controller.public-sensitive-model-write
  pmqms.xml.server-action-eval
  pmqms.xml.server-action-sudo-review
  pmqms.xml.cron-code-review
  pmqms.xml.qweb-raw-output
)

mkdir -p "$REPORT_DIR" "$TOOLS_DIR"

detect_platform() {
  local uname_s
  uname_s="$(uname -s)"
  case "$uname_s" in
    Linux*) PLATFORM="linux"; EXE_SUFFIX="" ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM="windows"; EXE_SUFFIX=".exe" ;;
    *)
      printf 'Unsupported platform for pinned scanner downloads: %s\n' "$uname_s" >&2
      status_json "$REPORT_DIR/platform.json" "platform" "INFRA_FAILURE" 2 "Unsupported platform: $uname_s"
      printf '2\n' > "$EXIT_CODE_FILE"
      exit 2
      ;;
  esac
}

detect_python() {
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    PYTHON_BIN=(python3)
    return 0
  fi
  if command -v py >/dev/null 2>&1 && py -3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    PYTHON_BIN=(py -3)
    return 0
  fi
  if command -v python >/dev/null 2>&1 && python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    PYTHON_BIN=(python)
    return 0
  fi
  return 1
}

status_json() {
  local file="$1"
  local tool="$2"
  local status="$3"
  local exit_code="$4"
  local notes="$5"
  printf '{\n  "tool": "%s",\n  "status": "%s",\n  "exit_code": %s,\n  "notes": "%s"\n}\n' \
    "$tool" "$status" "$exit_code" "$notes" > "$file"
}

require_prerequisites() {
  local missing=()
  local cmd
  for cmd in curl git sha256sum tar; do
    command -v "$cmd" >/dev/null 2>&1 || missing+=("$cmd")
  done
  if [[ "$PLATFORM" == "windows" ]]; then
    command -v unzip >/dev/null 2>&1 || missing+=("unzip")
  fi
  detect_python || missing+=("python3 or py -3")
  if (( ${#missing[@]} > 0 )); then
    printf 'Missing prerequisites: %s\n' "${missing[*]}" >&2
    status_json "$REPORT_DIR/prerequisites.json" "prerequisites" "INFRA_FAILURE" 2 "Missing required command(s): ${missing[*]}"
    printf '2\n' > "$EXIT_CODE_FILE"
    exit 2
  fi
  status_json "$REPORT_DIR/prerequisites.json" "prerequisites" "PASS" 0 "Required local commands are available."
}

install_opengrep() {
  local dir="$TOOLS_DIR/opengrep-${OPENGREP_VERSION}"
  local bin="$dir/opengrep${EXE_SUFFIX}"
  local url="$OPENGREP_LINUX_X86_URL"
  local sha="$OPENGREP_LINUX_X86_SHA256"
  if [[ "$PLATFORM" == "windows" ]]; then
    url="$OPENGREP_WINDOWS_X86_URL"
    sha="$OPENGREP_WINDOWS_X86_SHA256"
  fi
  mkdir -p "$dir"
  if [[ ! -x "$bin" ]]; then
    local tmp="$dir/opengrep.download${EXE_SUFFIX}"
    curl -fsSL "$url" -o "$tmp"
    printf '%s  %s\n' "$sha" "$tmp" | sha256sum -c - > "$REPORT_DIR/opengrep-checksum.txt"
    mv "$tmp" "$bin"
    chmod 755 "$bin"
  fi
  "$bin" --version > "$REPORT_DIR/opengrep-version.txt" 2>&1
  printf '%s\n' "$bin"
}

install_trivy() {
  local dir="$TOOLS_DIR/trivy-${TRIVY_VERSION}"
  local bin="$dir/trivy${EXE_SUFFIX}"
  mkdir -p "$dir"
  if [[ ! -x "$bin" ]]; then
    if [[ "$PLATFORM" == "windows" ]]; then
      local tmp="$dir/trivy.zip"
      curl -fsSL "$TRIVY_WINDOWS_X86_URL" -o "$tmp"
      printf '%s  %s\n' "$TRIVY_WINDOWS_X86_SHA256" "$tmp" | sha256sum -c - > "$REPORT_DIR/trivy-checksum.txt"
      unzip -o -q "$tmp" trivy.exe -d "$dir"
    else
      local tmp="$dir/trivy.tar.gz"
      curl -fsSL "$TRIVY_LINUX_X86_URL" -o "$tmp"
      printf '%s  %s\n' "$TRIVY_LINUX_X86_SHA256" "$tmp" | sha256sum -c - > "$REPORT_DIR/trivy-checksum.txt"
      tar -xzf "$tmp" -C "$dir" trivy
    fi
    chmod 755 "$bin"
  fi
  "$bin" --version > "$REPORT_DIR/trivy-version.txt" 2>&1
  printf '%s\n' "$bin"
}

install_python_tools() {
  local venv_python="$PYTHON_TOOLS_DIR/bin/python"
  local pylint_bin="$PYTHON_TOOLS_DIR/bin/pylint"
  local pip_audit_bin="$PYTHON_TOOLS_DIR/bin/pip-audit"
  if [[ "$PLATFORM" == "windows" ]]; then
    venv_python="$PYTHON_TOOLS_DIR/Scripts/python.exe"
    pylint_bin="$PYTHON_TOOLS_DIR/Scripts/pylint.exe"
    pip_audit_bin="$PYTHON_TOOLS_DIR/Scripts/pip-audit.exe"
  fi
  if [[ ! -x "$venv_python" ]]; then
    "${PYTHON_BIN[@]}" -m venv "$PYTHON_TOOLS_DIR"
    "$venv_python" -m pip install --disable-pip-version-check \
      "pylint==${PYLINT_VERSION}" \
      "pylint-odoo==${PYLINT_ODOO_VERSION}" \
      "pip-audit==${PIP_AUDIT_VERSION}"
  fi
  "$pylint_bin" --version > "$REPORT_DIR/pylint-odoo-version.txt" 2>&1
  "$pip_audit_bin" --version > "$REPORT_DIR/pip-audit-version.txt" 2>&1
  "$venv_python" -m pip freeze > "$REPORT_DIR/python-tools-freeze.txt"
}

run_opengrep_rule_tests() {
  local opengrep_bin="$1"
  local positive_json="$REPORT_DIR/opengrep-rule-tests-positive.json"
  local negative_json="$REPORT_DIR/opengrep-rule-tests-negative.json"
  local summary="$REPORT_DIR/opengrep-rule-tests.json"
  local rc=0

  "$opengrep_bin" scan --disable-version-check --no-git-ignore --config "$REPO_ROOT/security/opengrep/rules" \
    --json-output "$positive_json" "$REPO_ROOT/security/opengrep/tests/positive" >/dev/null 2>&1 || rc=$?
  "$opengrep_bin" scan --disable-version-check --no-git-ignore --config "$REPO_ROOT/security/opengrep/rules" \
    --json-output "$negative_json" "$REPO_ROOT/security/opengrep/tests/negative" >/dev/null 2>&1 || rc=$?

  local test_result
  test_result="$("${PYTHON_BIN[@]}" - "$positive_json" "$negative_json" "$summary" "${EXPECTED_OPENGREP_RULES[@]}" <<'PY'
import json
import sys
from pathlib import Path

positive_path = Path(sys.argv[1])
negative_path = Path(sys.argv[2])
summary_path = Path(sys.argv[3])
expected = sys.argv[4:]

try:
    positive = json.loads(positive_path.read_text(encoding="utf-8"))
    negative = json.loads(negative_path.read_text(encoding="utf-8"))
except Exception as exc:
    summary_path.write_text(json.dumps({
        "tool": "opengrep-rule-tests",
        "status": "FAIL",
        "reason": f"Could not parse OpenGrep rule-test JSON: {exc}",
    }, indent=2) + "\n", encoding="utf-8")
    print("0 999 parse-error")
    raise SystemExit(1)

ids = [result.get("check_id", "") for result in positive.get("results", [])]
missing = [rule for rule in expected if not any(check_id.endswith(rule) for check_id in ids)]
negative_count = len(negative.get("results", []))
positive_count = len(ids)
status = "PASS" if not missing and negative_count == 0 else "FAIL"
summary_path.write_text(json.dumps({
    "tool": "opengrep-rule-tests",
    "status": status,
    "positive_findings": positive_count,
    "negative_findings": negative_count,
    "missing_rules": missing,
}, indent=2) + "\n", encoding="utf-8")
print(f"{positive_count} {negative_count} {','.join(missing) if missing else 'none'}")
raise SystemExit(0 if status == "PASS" else 1)
PY
)"
  local test_rc=$?
  local positive_count negative_count missing_text
  read -r positive_count negative_count missing_text <<< "$test_result"

  if (( rc != 0 )) || (( test_rc != 0 )); then
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
    printf 'OpenGrep rule tests failed. Missing rules: %s; negative findings: %s\n' "${missing_text:-unknown}" "${negative_count:-unknown}" >&2
    return 1
  fi

  printf 'OpenGrep rule tests passed with %s positive findings and 0 negative findings.\n' "$positive_count"
}

run_opengrep_scan() {
  local opengrep_bin="$1"
  local rc=0
  local targets=(addons deployment tools .github docs)
  local excludes=(
    --exclude ".git"
    --exclude ".security-audit"
    --exclude "security/opengrep/tests"
    --exclude "plane"
    --exclude "__pycache__"
    --exclude ".pytest_cache"
    --exclude "deployment/docker/.volumes"
    --exclude "deployment/docker/data"
    --exclude "deployment/docker/secrets"
    --exclude "filestore"
    --exclude "sessions"
    --exclude "exports"
    --exclude "backups"
    --exclude "standards-private"
    --exclude "licensed-standards"
  )

  "$opengrep_bin" scan --disable-version-check --no-git-ignore --config "$REPO_ROOT/security/opengrep/rules" \
    "${excludes[@]}" --json-output "$REPORT_DIR/opengrep.json" "${targets[@]}" >/dev/null 2>&1 || rc=$?
  "$opengrep_bin" scan --disable-version-check --no-git-ignore --config "$REPO_ROOT/security/opengrep/rules" \
    "${excludes[@]}" --sarif-output "$REPORT_DIR/opengrep.sarif" "${targets[@]}" >/dev/null 2>&1 || rc=$?

  if (( rc != 0 )) || [[ ! -s "$REPORT_DIR/opengrep.json" ]] || [[ ! -s "$REPORT_DIR/opengrep.sarif" ]]; then
    status_json "$REPORT_DIR/opengrep.status.json" "opengrep" "INFRA_FAILURE" "$rc" "OpenGrep did not generate required JSON and SARIF reports."
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
    return 1
  fi
  status_json "$REPORT_DIR/opengrep.status.json" "opengrep" "EXECUTED" 0 "OpenGrep completed with local repository rules."
}

run_pylint_odoo() {
  local pylint_bin="$PYTHON_TOOLS_DIR/bin/pylint"
  if [[ "$PLATFORM" == "windows" ]]; then
    pylint_bin="$PYTHON_TOOLS_DIR/Scripts/pylint.exe"
  fi
  local rc=0
  local addons=()
  while IFS= read -r -d '' manifest; do
    addons+=("$(dirname "$manifest")")
  done < <(find "$REPO_ROOT/addons" -mindepth 2 -maxdepth 2 -name __manifest__.py -print0 | sort -z)

  if (( ${#addons[@]} == 0 )); then
    status_json "$REPORT_DIR/pylint-odoo.status.json" "pylint-odoo" "INFRA_FAILURE" 2 "No local pm_qms addons were found."
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
    return 1
  fi

  "$pylint_bin" --load-plugins=pylint_odoo --valid-odoo-versions=19.0 \
    --output-format=json --exit-zero "${addons[@]}" > "$REPORT_DIR/pylint-odoo.json" 2> "$REPORT_DIR/pylint-odoo.stderr" || rc=$?

  if (( rc != 0 )) || [[ ! -s "$REPORT_DIR/pylint-odoo.json" ]]; then
    status_json "$REPORT_DIR/pylint-odoo.status.json" "pylint-odoo" "INFRA_FAILURE" "$rc" "pylint-odoo did not produce JSON output."
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
    return 1
  fi
  status_json "$REPORT_DIR/pylint-odoo.status.json" "pylint-odoo" "EXECUTED_BASELINE" 0 "pylint-odoo completed in baseline reporting mode against local addons only."
}

run_trivy() {
  local trivy_bin="$1"
  local rc=0
  local skip_args=(
    --skip-dirs "$REPO_ROOT/.git"
    --skip-dirs "$REPO_ROOT/.security-audit"
    --skip-dirs "$REPO_ROOT/plane"
    --skip-dirs "$REPO_ROOT/security/opengrep/tests"
    --skip-dirs "$REPO_ROOT/deployment/docker/.volumes"
    --skip-dirs "$REPO_ROOT/deployment/docker/data"
    --skip-dirs "$REPO_ROOT/deployment/docker/secrets"
    --skip-dirs "$REPO_ROOT/filestore"
    --skip-dirs "$REPO_ROOT/sessions"
    --skip-dirs "$REPO_ROOT/exports"
    --skip-dirs "$REPO_ROOT/backups"
    --skip-dirs "$REPO_ROOT/standards-private"
    --skip-dirs "$REPO_ROOT/licensed-standards"
  )

  "$trivy_bin" fs --scanners vuln,misconfig,secret --format json \
    --output "$REPORT_DIR/trivy.json" "${skip_args[@]}" "$REPO_ROOT" >/dev/null 2> "$REPORT_DIR/trivy.stderr" || rc=$?
  "$trivy_bin" fs --scanners vuln,misconfig,secret --format sarif \
    --output "$REPORT_DIR/trivy.sarif" "${skip_args[@]}" "$REPO_ROOT" >/dev/null 2>> "$REPORT_DIR/trivy.stderr" || rc=$?
  "$trivy_bin" fs --format cyclonedx \
    --output "$REPORT_DIR/sbom.cyclonedx.json" "${skip_args[@]}" "$REPO_ROOT" >/dev/null 2>> "$REPORT_DIR/trivy.stderr" || rc=$?

  if (( rc != 0 )) || [[ ! -s "$REPORT_DIR/trivy.json" ]] || [[ ! -s "$REPORT_DIR/trivy.sarif" ]] || [[ ! -s "$REPORT_DIR/sbom.cyclonedx.json" ]]; then
    status_json "$REPORT_DIR/trivy.status.json" "trivy" "INFRA_FAILURE" "$rc" "Trivy did not generate JSON, SARIF and CycloneDX SBOM artifacts."
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
    return 1
  fi
  status_json "$REPORT_DIR/trivy.status.json" "trivy" "EXECUTED" 0 "Trivy completed for vuln, misconfig and secret scanners, including unfixed findings."
}

dependency_input() {
  local candidate
  for candidate in requirements.txt requirements-dev.txt requirements/requirements.txt requirements/base.txt requirements/prod.txt requirements/production.txt; do
    if [[ -f "$REPO_ROOT/$candidate" ]]; then
      printf '%s\n' "$REPO_ROOT/$candidate"
      return 0
    fi
  done
  return 1
}

run_pip_audit() {
  local pip_audit_bin="$PYTHON_TOOLS_DIR/bin/pip-audit"
  if [[ "$PLATFORM" == "windows" ]]; then
    pip_audit_bin="$PYTHON_TOOLS_DIR/Scripts/pip-audit.exe"
  fi
  local input_file
  if ! input_file="$(dependency_input)"; then
    cat > "$REPORT_DIR/pip-audit.json" <<'JSON'
{
  "tool": "pip-audit",
  "status": "NOT_EXECUTED",
  "reason": "No canonical requirements or Python lockfile exists in the repository, so a reproducible dependency audit input is unavailable.",
  "recommendation": "Add a reviewed requirements lock or constraints file for the non-Odoo Python tooling/runtime before claiming dependency PASS."
}
JSON
    "${PYTHON_BIN[@]}" "$REPO_ROOT/tools/security/pip_audit_evidence.py" \
      --missing-input --input-path "" --output "$REPORT_DIR/pip-audit.status.json" >/dev/null
    return 0
  fi

  local rc=0
  "$pip_audit_bin" -r "$input_file" --format json --output "$REPORT_DIR/pip-audit.json" > "$REPORT_DIR/pip-audit.stdout" 2> "$REPORT_DIR/pip-audit.stderr" || rc=$?
  if [[ ! -s "$REPORT_DIR/pip-audit.json" ]]; then
    "${PYTHON_BIN[@]}" "$REPO_ROOT/tools/security/pip_audit_evidence.py" \
      --input-path "$input_file" --tool-exit-code "$rc" --output "$REPORT_DIR/pip-audit.status.json" >/dev/null || true
    return 1
  fi
  local classifier_rc=0
  "${PYTHON_BIN[@]}" "$REPO_ROOT/tools/security/pip_audit_evidence.py" \
    --input "$REPORT_DIR/pip-audit.json" --input-path "$input_file" --tool-exit-code "$rc" \
    --output "$REPORT_DIR/pip-audit.status.json" >/dev/null || classifier_rc=$?
  if (( classifier_rc == 1 )); then
    return 1
  fi
  if (( classifier_rc != 0 )); then
    return 1
  fi
}

run_secret_scan() {
  local current_log="$REPORT_DIR/secret-scan-current.log"
  local history_locations="$REPORT_DIR/secret-scan-history-locations.txt"
  local current_rc=0
  "${PYTHON_BIN[@]}" "$REPO_ROOT/deployment/scripts/secret-scan.py" > "$current_log" 2>&1 || current_rc=$?

  : > "$history_locations"
  local pattern="-----BEGIN (RSA |DSA |EC |OPENSSH |)PRIVATE KEY-----|([Aa][Pp][Ii][_-]?[Kk][Ee][Yy]|[Aa][Pp][Ii][_-]?[Tt][Oo][Kk][Ee][Nn]|[Aa][Cc][Cc][Ee][Ss][Ss][_-]?[Tt][Oo][Kk][Ee][Nn]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt])[[:space:]]*[:=][[:space:]]*['\"][^'\"]{12,}['\"]|([Aa][Pp][Ii][_-]?[Kk][Ee][Yy]|[Aa][Pp][Ii][_-]?[Tt][Oo][Kk][Ee][Nn]|[Aa][Cc][Cc][Ee][Ss][Ss][_-]?[Tt][Oo][Kk][Ee][Nn]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Pp][Aa][Ss][Ss][Ww][Dd]|[Ss][Ee][Cc][Rr][Ee][Tt])[[:space:]]*=[[:space:]]*[A-Za-z0-9_./+@!#$%^&*=-]{16,}"
  local commit
  while IFS= read -r commit; do
    git grep -I -n -E "$pattern" "$commit" -- . \
      ':!*.png' ':!*.jpg' ':!*.jpeg' ':!*.gif' ':!*.pdf' ':!*.zip' ':!*.gz' ':!*.tgz' \
      ':!deployment/scripts/secret-scan.py' ':!security/opengrep/tests/**' ':!security/README.md' \
      2>/dev/null | awk -F: '{print $1 ":" $2 ":" $3}' >> "$history_locations" || true
  done < <(git rev-list --all)
  sort -u "$history_locations" -o "$history_locations"

  local current_status="PASS"
  local history_status="PASS"
  local history_count
  history_count="$(wc -l < "$history_locations" | tr -d ' ')"
  if (( current_rc != 0 )); then
    current_status="FOUND"
  fi
  if (( history_count > 0 )); then
    history_status="FOUND"
  fi
  if [[ "$current_status" == "FOUND" || "$history_status" == "FOUND" ]]; then
    SECRET_FINDINGS=$((SECRET_FINDINGS + history_count + current_rc))
  fi

  "${PYTHON_BIN[@]}" - "$REPORT_DIR/secret-scan.json" "$current_status" "$history_status" "$history_count" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
current_status = sys.argv[2]
history_status = sys.argv[3]
history_count = int(sys.argv[4])
status = "PASS" if current_status == "PASS" and history_status == "PASS" else "FOUND"
path.write_text(json.dumps({
    "tool": "pmqms-secret-scan",
    "status": status,
    "current_code": current_status,
    "git_history": history_status,
    "masked_history_locations": history_count,
}, indent=2) + "\n", encoding="utf-8")
PY
}

run_zap_placeholder() {
  cat > "$REPORT_DIR/zap.json" <<'JSON'
{
  "tool": "OWASP ZAP",
  "status": "NOT_EXECUTED",
  "reason": "No disposable local Odoo target URL and non-destructive test-account configuration are defined for this repository baseline.",
  "required_to_execute": [
    "A local throwaway Odoo instance URL",
    "Non-production credentials supplied through environment variables or GitHub Secrets",
    "A passive or baseline ZAP configuration that excludes destructive attacks"
  ]
}
JSON
}

build_summary() {
  local summary_line
  summary_line="$("${PYTHON_BIN[@]}" - "$REPORT_DIR" "$SUMMARY_JSON" "$EXIT_CODE_FILE" "$ENFORCEMENT_MODE" "$INFRA_FAILURES" "$POLICY_FAILURES" "$SECRET_FINDINGS" "$OPENGREP_VERSION" "$PYLINT_VERSION" "$PYLINT_ODOO_VERSION" "$TRIVY_VERSION" "$PIP_AUDIT_VERSION" <<'PY'
import json
import sys
from pathlib import Path

report_dir = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
exit_code_path = Path(sys.argv[3])
enforcement_mode = sys.argv[4]
infra_failures = int(sys.argv[5])
policy_failures = int(sys.argv[6])
secret_findings = int(sys.argv[7])
versions = {
    "opengrep": sys.argv[8],
    "pylint": sys.argv[9],
    "pylint_odoo": sys.argv[10],
    "trivy": sys.argv[11],
    "pip_audit": sys.argv[12],
}

sys.path.insert(0, str(report_dir.parents[2] / "tools" / "security"))
from pip_audit_evidence import apply_to_summary

def load_json(name):
    path = report_dir / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def count_opengrep(severity):
    data = load_json("opengrep.json")
    count = 0
    for result in data.get("results", []):
        extra = result.get("extra", {})
        metadata = extra.get("metadata", {})
        value = metadata.get("security_severity") or extra.get("severity") or "INFO"
        if str(value).upper() == severity:
            count += 1
    return count

def count_trivy(severity):
    data = load_json("trivy.json")
    count = 0
    for result in data.get("Results", []):
        for key in ("Vulnerabilities", "Misconfigurations", "Secrets"):
            for item in result.get(key, []) or []:
                if str(item.get("Severity", "INFO")).upper() == severity:
                    count += 1
    return count

severity = {
    "CRITICAL": count_opengrep("CRITICAL") + count_trivy("CRITICAL") + secret_findings,
    "HIGH": count_opengrep("HIGH") + count_trivy("HIGH"),
    "MEDIUM": count_opengrep("MEDIUM") + count_trivy("MEDIUM"),
    "LOW": count_opengrep("LOW") + count_trivy("LOW"),
    "INFO": count_opengrep("INFO") + count_trivy("INFO"),
}

if severity["CRITICAL"] > 0:
    policy_failures += 1

exit_code = 0
status = "PASS"
if infra_failures > 0:
    exit_code = 2
    status = "INFRA_FAILURE"
elif policy_failures > 0:
    exit_code = 1
    status = "POLICY_FAILURE"
elif enforcement_mode == "baseline":
    status = "BASELINE"

pip_audit = load_json("pip-audit.status.json")
summary = {
    "status": status,
    "enforcement_mode": enforcement_mode,
    "report_dir": str(report_dir),
    "tools": versions,
    "severity": severity,
    "infra_failures": infra_failures,
    "policy_failures": policy_failures,
    "exit_code": exit_code,
}
summary = apply_to_summary(summary, pip_audit or {
    "status": "ERROR/BLOCKED",
    "policy_result": "ERROR",
    "findings_count": 0,
})
exit_code = summary["exit_code"]
summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
exit_code_path.write_text(f"{exit_code}\n", encoding="utf-8")
print(
    "SECURITY_AUDIT_SUMMARY "
    f"status={summary['status']} enforcement={enforcement_mode} critical={severity['CRITICAL']} "
    f"high={severity['HIGH']} medium={severity['MEDIUM']} low={severity['LOW']} "
    f"info={severity['INFO']} pip_audit={summary['pip_audit_status']} "
    f"pip_audit_policy={summary['pip_audit_policy_result']} report_dir={report_dir}"
)
raise SystemExit(exit_code)
PY
)"
  local exit_code=$?
  printf '%s\n' "$summary_line"
  return "$exit_code"
}

main() {
  detect_platform
  require_prerequisites

  local opengrep_bin=""
  local trivy_bin=""
  if ! opengrep_bin="$(install_opengrep)"; then
    status_json "$REPORT_DIR/opengrep.status.json" "opengrep" "INFRA_FAILURE" 2 "OpenGrep installation or checksum verification failed."
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
  fi
  if ! trivy_bin="$(install_trivy)"; then
    status_json "$REPORT_DIR/trivy.status.json" "trivy" "INFRA_FAILURE" 2 "Trivy installation or checksum verification failed."
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
  fi
  if ! install_python_tools; then
    status_json "$REPORT_DIR/python-tools.status.json" "python-tools" "INFRA_FAILURE" 2 "Python security tool installation failed."
    INFRA_FAILURES=$((INFRA_FAILURES + 1))
  fi

  if [[ -n "$opengrep_bin" && -x "$opengrep_bin" ]]; then
    run_opengrep_rule_tests "$opengrep_bin" || true
    run_opengrep_scan "$opengrep_bin" || true
  fi
  run_pylint_odoo || true
  if [[ -n "$trivy_bin" && -x "$trivy_bin" ]]; then
    run_trivy "$trivy_bin" || true
  fi
  run_pip_audit || true
  run_secret_scan || true
  run_zap_placeholder

  build_summary
}

main "$@"
