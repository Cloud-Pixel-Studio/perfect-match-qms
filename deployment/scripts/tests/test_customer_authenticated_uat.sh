#!/usr/bin/env bash
set -euo pipefail

# Disposable authenticated customer UAT.  The customer-instance CLI remains
# the lifecycle authority; this script only supplies ephemeral test fixtures.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CUSTOMER_SCRIPT="$REPO_ROOT/deployment/scripts/customer-instance.sh"
RUNTIME_LOCK="$REPO_ROOT/deployment/runtime/runtime-lock.json"
UAT_DIR="$REPO_ROOT/tools/tests/UAT"
WORK="$(mktemp -d)"
INSTANCE_ROOT="$WORK/instances"
export PMQMS_CUSTOMER_INSTANCE_ROOT="$INSTANCE_ROOT"
export TMPDIR="$WORK/tmp"
mkdir -p "$INSTANCE_ROOT" "$TMPDIR" "$WORK/users" "$WORK/browser-users" "$WORK/nginx"
umask 077

RUN_ID="${GITHUB_RUN_ID:-local}-$$"
RUN_SUFFIX="$(printf '%s' "$RUN_ID" | tr -cd '[:alnum:]' | cut -c1-24)"
SLUG="m314-c11-uat-test-${RUN_SUFFIX}"
ODOO_PORT="$((18000 + ($$ % 700)))"
PROXY_PORT="$((19000 + ($$ % 700)))"
TAG="v99.99.$((100 + ($$ % 800)))-rc0"
NGINX="pmqms-customer-uat-nginx-${RUN_SUFFIX}"
TAG_CREATED=0
RUNTIME_DIAGNOSTICS="$WORK/runtime-diagnostics.txt"

fail() { echo "authenticated customer UAT: FAIL: $*" >&2; exit 1; }
cleanup() {
  local test_rc=$? cleanup_rc=0
  local -a disposable_containers=()
  trap - EXIT
  docker rm -f "$NGINX" >/dev/null 2>&1 || true
  if [[ -f "$INSTANCE_ROOT/$SLUG/config/instance.env" ]]; then
    bash "$CUSTOMER_SCRIPT" destroy "$SLUG" --confirm-ephemeral >/dev/null 2>&1 || cleanup_rc=1
    [[ ! -e "$INSTANCE_ROOT/$SLUG" ]] || cleanup_rc=1
  fi
  mapfile -t disposable_containers < <(docker ps -aq --filter "label=com.docker.compose.project=pmqms-customer-${SLUG}")
  if ((${#disposable_containers[@]})); then
    docker rm -f "${disposable_containers[@]}" >/dev/null 2>&1 || cleanup_rc=1
  fi
  docker volume rm "pmqms_${SLUG}_odoo_data" "pmqms_${SLUG}_postgres" >/dev/null 2>&1 || true
  if [[ -n "${ALPINE_IMAGE:-}" && -d "$WORK" ]]; then
    docker run --rm --user root -v "$WORK:/cleanup" "$ALPINE_IMAGE" \
      sh -eu -c 'rm -rf /cleanup/* /cleanup/.[!.]* /cleanup/..?*' >/dev/null 2>&1 || cleanup_rc=1
  fi
  rm -rf -- "$WORK" || cleanup_rc=1
  if [[ "$TAG_CREATED" == 1 ]]; then git -C "$REPO_ROOT" tag -d "$TAG" >/dev/null 2>&1 || cleanup_rc=1; fi
  if [[ "$cleanup_rc" == 0 ]]; then
    echo 'authenticated customer UAT cleanup: PASS'
  else
    echo 'authenticated customer UAT cleanup: FAIL' >&2
  fi
  if ((test_rc != 0)); then exit "$test_rc"; fi
  exit "$cleanup_rc"
}
trap cleanup EXIT

for command in docker git jq openssl curl sha256sum node npm; do
  command -v "$command" >/dev/null 2>&1 || fail "required command missing: $command"
done
docker info >/dev/null 2>&1 || fail "Docker daemon unavailable"

ODOO_IMAGE="$(jq -er '.odoo.image' "$RUNTIME_LOCK")"
ALPINE_IMAGE="$(jq -er '.alpine.image' "$RUNTIME_LOCK")"
NGINX_IMAGE="$(jq -er '.nginx.image' "$RUNTIME_LOCK")"
while IFS= read -r image; do docker pull "$image" >/dev/null; done < <(jq -er '.odoo.image, .postgres.image, .alpine.image, .nginx.image' "$RUNTIME_LOCK")

git -C "$REPO_ROOT" tag "$TAG"
TAG_CREATED=1
bash "$CUSTOMER_SCRIPT" bundle --release "$TAG" --output "$WORK/customer-bundle.tar.gz" >/dev/null
DB_NAME="pmqms_${SLUG//-/_}"
RUNTIME_REPOSITORY_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
RUNTIME_SOURCE_TREE_SHA="$(git -C "$REPO_ROOT" rev-parse 'HEAD^{tree}')"
DB_PREEXISTED="NO"
if [[ -e "$INSTANCE_ROOT/$SLUG" ]]; then DB_PREEXISTED="YES"; fi
bash "$CUSTOMER_SCRIPT" provision "$SLUG" --bundle "$WORK/customer-bundle.tar.gz" --type test --port "$ODOO_PORT" >/dev/null
ROOT="$INSTANCE_ROOT/$SLUG"
ADDON_COPY_COUNT="$(find "$ROOT/runtime/addons" -mindepth 1 -maxdepth 1 -type d -name pm_qms_app | wc -l | tr -d ' ')"

bash "$CUSTOMER_SCRIPT" bootstrap "$SLUG" >"$WORK/bootstrap.log" 2>&1
bash "$CUSTOMER_SCRIPT" activation-request "$SLUG" >"$WORK/activation.log" 2>&1

openssl genpkey -algorithm Ed25519 -out "$WORK/license-key.pem" >/dev/null 2>&1
openssl pkey -in "$WORK/license-key.pem" -pubout -outform DER 2>/dev/null | tail -c 32 | base64 -w0 > "$WORK/public-key.b64"
jq -n --arg key "$(<"$WORK/public-key.b64")" '{keys:{"m314-ci-test":$key}}' > "$WORK/public_keys.json"
docker run --rm --user root -v "$WORK/public_keys.json:/input/public_keys.json:ro" -v "$ROOT/runtime/addons/pm_qms_license/data:/data" "$ALPINE_IMAGE" sh -eu -c 'cp /input/public_keys.json /data/public_keys.json && chmod 644 /data/public_keys.json'

ENVIRONMENT_ID="$(tr -d '\n' < "$ROOT/config/environment_id")"
docker run --rm --user root -v "$REPO_ROOT:/repo:ro" -v "$WORK:/work" "$ODOO_IMAGE" python3 /repo/deployment/scripts/issue-license.py \
  --private-key /work/license-key.pem --output /work/active.pmql --environment-id "$ENVIRONMENT_ID" \
  --customer-name "M31 Fictional Components" --key-id m314-ci-test --license-id "M31-C11-${RUN_SUFFIX}" \
  --company-limit 1 --site-limit 3 --named-user-limit 10 >/dev/null
bash "$CUSTOMER_SCRIPT" import-license "$SLUG" "$WORK/active.pmql" >/dev/null

openssl rand -hex 24 > "$WORK/users/qm-password"
bash "$CUSTOMER_SCRIPT" bootstrap-customer "$SLUG" \
  --company-name "M31 Fictional Components" --company-code M31-C11 \
  --user-login "quality.manager.${RUN_SUFFIX}@example.invalid" --user-name "M31 Fictional Quality Manager" \
  --user-email "quality.manager.${RUN_SUFFIX}@example.invalid" --user-password-file "$WORK/users/qm-password" >/dev/null
bash "$CUSTOMER_SCRIPT" create-site "$SLUG" --code M31-HQ --name "M31 Fictional Headquarters" --type headquarters >/dev/null

for role in auditor owner viewer api; do
  openssl rand -hex 24 > "$WORK/users/${role}-password"
done

# Fixture creation is ORM-based and confined to the disposable database.
docker run --rm --user root -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" -v "$WORK:/work" "$ALPINE_IMAGE" sh -c 'chown -R 100:101 /work/users && chmod 711 /work && chmod 700 /work/users && chmod 600 /work/users/*' >/dev/null
docker run --rm --user root -v "$ROOT/secrets/initial_admin_password:/source:ro" -v "$WORK:/work" "$ALPINE_IMAGE" \
  sh -eu -c 'cp /source /work/users/admin-password && chown 100:101 /work/users/admin-password && chmod 600 /work/users/admin-password' >/dev/null
docker compose --project-name "pmqms-customer-${SLUG}" --env-file "$ROOT/config/instance.env" \
  -f "$ROOT/runtime/compose.yml" run --rm --user 100:101 \
  -v "$WORK:/var/lib/pmqms-uat:ro" \
  odoo odoo shell -d "pmqms_${SLUG//-/_}" --log-level=error <<PY >/dev/null
from pathlib import Path
company = env.company
admin = env["res.users"].sudo().search([("login", "=", "admin")], limit=1)
if not admin:
    raise RuntimeError("technical admin fixture missing")
admin.write({"password": Path("/var/lib/pmqms-uat/users/admin-password").read_text().strip()})
organization = env["pm.qms.organization"].sudo().search([("organization_kind", "=", "operational")], limit=1)
if not organization:
    raise RuntimeError("operational organization missing")
base_user = env.ref("base.group_user")
role_data = {
    "auditor": "pm_qms_core.group_qms_internal_auditor",
    "owner": "pm_qms_core.group_qms_process_owner",
    "viewer": "pm_qms_core.group_qms_viewer",
    "api": "pm_qms_app.group_api_integration_administrator",
}
names = {
    "auditor": "M31 Fictional Internal Auditor",
    "owner": "M31 Fictional Process Owner",
    "viewer": "M31 Fictional Viewer",
    "api": "M31 Fictional API Integration Administrator",
}
for key, xmlid in role_data.items():
    login = "m31.%s.${RUN_SUFFIX}@example.invalid" % key
    group = env.ref(xmlid)
    password = Path("/var/lib/pmqms-uat/users/%s-password" % key).read_text().strip()
    user = env["res.users"].sudo().create({
        "name": names[key], "login": login, "email": login, "password": password,
        "company_id": company.id, "company_ids": [(6, 0, [company.id])],
        "group_ids": [(6, 0, [base_user.id, group.id])],
        "qms_organization_ids": [(6, 0, [organization.id])], "qms_scope_configured": True,
        "qms_all_sites": True, "qms_all_processes": True,
    })
    env["pm.qms.person"].sudo().create({"name": names[key], "user_id": user.id, "organization_id": organization.id})
env.cr.commit()
PY

# Playwright runs as the GitHub runner user, so it receives temporary
# read-only copies after ORM setup. They remain outside artifacts and are
# removed by cleanup.
docker run --rm --user root -v "$WORK:/work" "$ALPINE_IMAGE" \
  sh -eu -c 'cp /work/users/* /work/browser-users/ && cp /work/instances/'"$SLUG"'/secrets/initial_admin_password /work/browser-users/admin-password && chmod 755 /work/browser-users && chmod 644 /work/browser-users/*' >/dev/null

# Emit a sanitized ORM/runtime inventory before browser navigation.  This is
# deliberately diagnostic-only: it must not change the fixture or weaken the
# normative Configuration assertion in customer-browser.spec.cjs.
set +e
docker compose --project-name "pmqms-customer-${SLUG}" --env-file "$ROOT/config/instance.env" \
  -f "$ROOT/runtime/compose.yml" run --rm --user 100:101 \
  -e PMQMS_RUNTIME_REPOSITORY_SHA="$RUNTIME_REPOSITORY_SHA" \
  -e PMQMS_RUNTIME_SOURCE_TREE_SHA="$RUNTIME_SOURCE_TREE_SHA" \
  -e PMQMS_QM_LOGIN="quality.manager.${RUN_SUFFIX}@example.invalid" \
  -e PMQMS_DB_NAME="$DB_NAME" \
  -e PMQMS_DB_PREEXISTED="$DB_PREEXISTED" \
  -e PMQMS_ADDON_COPY_COUNT="$ADDON_COPY_COUNT" \
  odoo odoo shell -d "$DB_NAME" --log-level=error <<'PY' >"$RUNTIME_DIAGNOSTICS" 2>&1
import json
import os
from odoo.modules.module import get_module_path


def emit(key, value):
    print("%s=%s" % (key, json.dumps(value, sort_keys=True, default=str)))


def xmlid_for(record):
    if not record:
        return None
    data = env["ir.model.data"].sudo().search([
        ("model", "=", record._name), ("res_id", "=", record.id)
    ], limit=1)
    return data.complete_name if data else None


def groups_for(groups):
    return sorted(filter(None, (xmlid_for(group) for group in groups)))


def assigned_groups(record):
    for field_name in ("group_ids", "groups_id"):
        if field_name in record._fields:
            return getattr(record, field_name)
    return env["res.groups"]


def safe_menu(xmlid, visible_menu_ids):
    menu = env.ref(xmlid, raise_if_not_found=False)
    if not menu:
        return {"xmlid": xmlid, "resolves": False}
    action = menu.action
    menu_groups = assigned_groups(menu)
    allowed = not menu_groups or bool(menu_groups & qm.all_group_ids)
    children = menu.child_id.filtered(
        lambda child: child.active and (not assigned_groups(child) or bool(assigned_groups(child) & qm.all_group_ids))
    )
    action_groups = groups_for(assigned_groups(action)) if action else []
    action_xmlid = xmlid_for(action) if action else None
    return {
        "xmlid": xmlid,
        "resolves": True,
        "active": bool(menu.active),
        "parent": xmlid_for(menu.parent_id),
        "sequence": menu.sequence,
        "groups": groups_for(menu_groups),
        "action": action_xmlid,
        "action_model": action.res_model if action and hasattr(action, "res_model") else None,
        "action_groups": action_groups,
        "quality_manager_passes_menu_group": allowed,
        "accessible_child": bool(children),
        "visible_menu_computation": menu.id in visible_menu_ids,
    }


def safe_action(xmlid, model_name):
    action = env.ref(xmlid, raise_if_not_found=False)
    if not action:
        return {"xmlid": xmlid, "resolves": False}
    model = env[model_name].with_user(qm)
    result = {
        "xmlid": xmlid,
        "resolves": True,
        "groups": groups_for(assigned_groups(action)),
        "target_model": action.res_model,
        "action_read": False,
        "action_dict": False,
        "load_error": None,
        "model_access": {},
        "record_rule_search_count": None,
    }
    try:
        action.with_user(qm).read(["id", "name", "res_model"])
        result["action_read"] = True
        result["action_dict"] = True
    except Exception as exc:
        result["load_error"] = type(exc).__name__
    for operation in ("read", "create", "write", "unlink"):
        try:
            result["model_access"][operation] = bool(model.check_access_rights(operation, raise_exception=False))
        except Exception as exc:
            result["model_access"][operation] = type(exc).__name__
    try:
        result["record_rule_search_count"] = model.search_count([])
    except Exception as exc:
        result["record_rule_search_count"] = type(exc).__name__
    return result


qm_login = os.environ.get("PMQMS_QM_LOGIN")
qm = env["res.users"].sudo().search([("login", "=", qm_login)], limit=1)
visible = env["ir.ui.menu"].with_user(qm).load_menus(False) if qm else {}
visible_ids = set()
if isinstance(visible, dict):
    for key in visible.keys():
        try:
            visible_ids.add(int(key))
        except (TypeError, ValueError):
            pass
module = env["ir.module.module"].sudo().search([("name", "=", "pm_qms_app")], limit=1)
module_path = get_module_path("pm_qms_app")
emit("DATABASE", {
    "name": os.environ.get("PMQMS_DB_NAME"),
    "fresh_by_unique_run": os.environ.get("PMQMS_DB_PREEXISTED") == "NO",
    "volume_reuse": False,
})
emit("RUNTIME", {
    "repository_sha": os.environ.get("PMQMS_RUNTIME_REPOSITORY_SHA"),
    "source_tree_sha": os.environ.get("PMQMS_RUNTIME_SOURCE_TREE_SHA"),
    "pm_qms_app_path": module_path,
    "effective_addons_path": os.path.dirname(module_path) if module_path else None,
    "pm_qms_app_copy_count": int(os.environ.get("PMQMS_ADDON_COPY_COUNT", "0")),
    "pm_qms_app_duplicate_copy": int(os.environ.get("PMQMS_ADDON_COPY_COUNT", "0")) > 1,
})
emit("MODULE", {
    "name": "pm_qms_app",
    "state": module.state if module else None,
    "installed_version": module.installed_version if module else None,
    "latest_version": module.latest_version if module else None,
    "fresh_bootstrap_mode": "--init customer module set",
})
emit("QUALITY_MANAGER", {
    "login": qm_login,
    "exists": bool(qm),
    "active": bool(qm.active) if qm else False,
    "company": qm.company_id.name if qm else None,
    "allowed_companies": sorted(qm.company_ids.mapped("name")) if qm else [],
    "direct_groups": groups_for(qm.group_ids) if qm else [],
    "effective_groups": groups_for(qm.all_group_ids) if qm else [],
    "intended_group_xmlid": "pm_qms_core.group_qms_quality_manager",
    "intended_group_received": bool(qm and qm.has_group("pm_qms_core.group_qms_quality_manager")),
    "portal_or_public": bool(qm and (qm.has_group("base.group_portal") or qm.has_group("base.group_public"))),
    "shared": bool(qm.share) if qm else False,
})
menu_xmlids = [
    "pm_qms_core.menu_pm_qms_configuration",
    "pm_qms_core.menu_pm_qms_organizations",
    "pm_qms_app.menu_pm_qms_sites",
    "pm_qms_core.menu_pm_qms_processes",
    "pm_qms_app.menu_pm_qms_users_access",
    "pm_qms_license.menu_pm_qms_license",
    "pm_qms_core.menu_pm_qms_framework",
]
emit("MENUS", [safe_menu(xmlid, visible_ids) for xmlid in menu_xmlids])
action_specs = [
    ("pm_qms_core.action_pm_qms_organization", "pm.qms.organization"),
    ("pm_qms_core.action_pm_qms_site", "pm.qms.site"),
    ("pm_qms_core.action_pm_qms_process", "pm.qms.process"),
    ("pm_qms_app.action_pm_qms_users_access", "res.users"),
    ("pm_qms_license.action_pm_qms_license", "pm.qms.license"),
]
emit("ACTIONS", [safe_action(xmlid, model_name) for xmlid, model_name in action_specs])
license_status = None
try:
    license_status = env["pm.qms.license"].sudo().current_status().get("status")
except Exception as exc:
    license_status = type(exc).__name__
emit("LICENSE", {"status": license_status})
PY
DIAGNOSTIC_RC=$?
set -e
echo "M31_RUNTIME_DIAGNOSTICS_BEGIN"
if [[ "$DIAGNOSTIC_RC" == 0 ]]; then
  cat "$RUNTIME_DIAGNOSTICS"
else
  echo "DIAGNOSTIC_COMMAND_STATUS=FAIL"
  sed -E 's/(password|token|secret|cookie|csrf|key)[^[:space:]]*/[REDACTED]/Ig' "$RUNTIME_DIAGNOSTICS" || true
fi
echo "M31_RUNTIME_DIAGNOSTICS_END"

# Nginx is derived from the shipped template; only the listener/upstream are
# adapted for an HTTP-only, host-networked disposable proxy.
awk -v port="$ODOO_PORT" -v proxy_port="$PROXY_PORT" '
  /^server[[:space:]]*\{/ { block += 1 }
  block == 1 { next }
  block == 2 {
    if ($0 ~ /^[[:space:]]*ssl_certificate(_key)?[[:space:]]/) next
    sub(/listen 443 ssl http2;/, "listen " proxy_port ";")
    sub(/server_name customer\.example\.invalid;/, "server_name _;")
    sub(/proxy_pass http:\/\/127\.0\.0\.1:__CUSTOMER_HTTP_PORT__;/, "proxy_pass http://127.0.0.1:" port ";")
    sub(/proxy_set_header X-Forwarded-Proto https;/, "proxy_set_header X-Forwarded-Proto http;")
    sub(/proxy_set_header X-Forwarded-Port 443;/, "proxy_set_header X-Forwarded-Port " proxy_port ";")
    print
  }
' "$REPO_ROOT/deployment/nginx/customer.conf.example" > "$WORK/nginx/default.conf"
grep -Fq 'proxy_set_header X-Forwarded-For $remote_addr;' "$WORK/nginx/default.conf" || fail "template coupling lost client-IP policy"
grep -Fq 'proxy_set_header Forwarded "";' "$WORK/nginx/default.conf" || fail "template coupling lost Forwarded policy"
grep -Fq 'proxy_add_x_forwarded_for' "$WORK/nginx/default.conf" && fail "untrusted forwarding chain retained"
docker run -d --name "$NGINX" --network host -v "$WORK/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" "$NGINX_IMAGE" >/dev/null
for _ in {1..60}; do curl -fsS "http://127.0.0.1:$PROXY_PORT/web/login?db=pmqms_${SLUG//-/_}" >/dev/null 2>&1 && break; sleep 1; done
# The derived disposable template uses a runner-local port; no public listener
# or customer endpoint is touched.
if ! curl -fsS "http://127.0.0.1:$PROXY_PORT/web/login?db=pmqms_${SLUG//-/_}" >/dev/null 2>&1; then
  docker logs "$NGINX" >&2 || true
  fail "disposable proxy did not become healthy"
fi

export M31_BASE_URL="http://127.0.0.1:$PROXY_PORT"
export M31_DATABASE="pmqms_${SLUG//-/_}"
export M31_ORGANIZATION_NAME="M31 Fictional Components"
export M31_QM_LOGIN="quality.manager.${RUN_SUFFIX}@example.invalid"
export M31_QM_PASSWORD_FILE="$WORK/browser-users/qm-password"
export M31_ADMIN_LOGIN="admin"
export M31_ADMIN_PASSWORD_FILE="$WORK/browser-users/admin-password"
export M31_AUDITOR_LOGIN="m31.auditor.${RUN_SUFFIX}@example.invalid"
export M31_AUDITOR_PASSWORD_FILE="$WORK/browser-users/auditor-password"
export M31_OWNER_LOGIN="m31.owner.${RUN_SUFFIX}@example.invalid"
export M31_OWNER_PASSWORD_FILE="$WORK/browser-users/owner-password"
export M31_VIEWER_LOGIN="m31.viewer.${RUN_SUFFIX}@example.invalid"
export M31_VIEWER_PASSWORD_FILE="$WORK/browser-users/viewer-password"
export M31_API_LOGIN="m31.api.${RUN_SUFFIX}@example.invalid"
export M31_API_PASSWORD_FILE="$WORK/browser-users/api-password"
export M31_HEADLESS=true
export M31_BROWSER_CHANNEL=chromium
export M31_JSON_REPORT="$WORK/playwright.json"
export M31_OUTPUT_DIR="$WORK/playwright-output"
npm --prefix "$UAT_DIR" test -- --reporter=line
echo 'authenticated customer UAT: PASS'
