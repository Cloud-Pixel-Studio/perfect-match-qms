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
mkdir -p "$INSTANCE_ROOT" "$TMPDIR" "$WORK/users" "$WORK/nginx"
umask 077

RUN_ID="${GITHUB_RUN_ID:-local}-$$"
RUN_SUFFIX="$(printf '%s' "$RUN_ID" | tr -cd '[:alnum:]' | cut -c1-24)"
SLUG="m314-c11-uat-${RUN_SUFFIX}"
ODOO_PORT="$((18000 + ($$ % 700)))"
PROXY_PORT="$((19000 + ($$ % 700)))"
TAG="v99.99.$((100 + ($$ % 800)))-rc0"
NGINX="pmqms-customer-uat-nginx-${RUN_SUFFIX}"
TAG_CREATED=0

fail() { echo "authenticated customer UAT: FAIL: $*" >&2; exit 1; }
cleanup() {
  local rc=$?
  trap - EXIT
  docker rm -f "$NGINX" >/dev/null 2>&1 || true
  if [[ -f "$INSTANCE_ROOT/$SLUG/config/instance.env" ]]; then
    bash "$CUSTOMER_SCRIPT" destroy "$SLUG" --confirm-ephemeral >/dev/null 2>&1 || rc=1
  fi
  docker rm -f $(docker ps -aq --filter "label=com.docker.compose.project=pmqms-customer-${SLUG}") >/dev/null 2>&1 || true
  docker volume rm "pmqms_${SLUG}_odoo_data" "pmqms_${SLUG}_postgres" >/dev/null 2>&1 || true
  rm -rf -- "$WORK" || rc=1
  if [[ "$TAG_CREATED" == 1 ]]; then git -C "$REPO_ROOT" tag -d "$TAG" >/dev/null 2>&1 || rc=1; fi
  exit "$rc"
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
bash "$CUSTOMER_SCRIPT" provision "$SLUG" --bundle "$WORK/customer-bundle.tar.gz" --type test --port "$ODOO_PORT" >/dev/null
ROOT="$INSTANCE_ROOT/$SLUG"

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

printf '%s' "qm-${RUN_SUFFIX}" > "$WORK/users/qm-password"
bash "$CUSTOMER_SCRIPT" bootstrap-customer "$SLUG" \
  --company-name "M31 Fictional Components" --company-code M31-C11 \
  --user-login "quality.manager.${RUN_SUFFIX}@example.invalid" --user-name "M31 Fictional Quality Manager" \
  --user-email "quality.manager.${RUN_SUFFIX}@example.invalid" --user-password-file "$WORK/users/qm-password" >/dev/null
bash "$CUSTOMER_SCRIPT" create-site "$SLUG" --code M31-HQ --name "M31 Fictional Headquarters" --type headquarters >/dev/null

for role in auditor owner viewer api; do
  printf '%s' "${role}-${RUN_SUFFIX}" > "$WORK/users/${role}-password"
done

# Fixture creation is ORM-based and confined to the disposable database.
docker run --rm --user root -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" -v "$WORK:/work" "$ALPINE_IMAGE" sh -c 'chown -R 100:101 /work/users && chmod 600 /work/users/*' >/dev/null
docker run --rm --user root -v "$WORK:/var/lib/pmqms-uat:ro" -v "$ROOT/config/odoo.conf:/etc/odoo/odoo.conf:ro" \
  -v "$ROOT/runtime/addons:/mnt/extra-addons:ro" "$ODOO_IMAGE" odoo shell -c /etc/odoo/odoo.conf -d "pmqms_${SLUG//-/_}" --log-level=error <<PY >/dev/null
from pathlib import Path
company = env.company
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
export M31_QM_PASSWORD_FILE="$WORK/users/qm-password"
export M31_ADMIN_LOGIN="admin"
export M31_ADMIN_PASSWORD_FILE="$ROOT/secrets/initial_admin_password"
export M31_AUDITOR_LOGIN="m31.auditor.${RUN_SUFFIX}@example.invalid"
export M31_AUDITOR_PASSWORD_FILE="$WORK/users/auditor-password"
export M31_OWNER_LOGIN="m31.owner.${RUN_SUFFIX}@example.invalid"
export M31_OWNER_PASSWORD_FILE="$WORK/users/owner-password"
export M31_VIEWER_LOGIN="m31.viewer.${RUN_SUFFIX}@example.invalid"
export M31_VIEWER_PASSWORD_FILE="$WORK/users/viewer-password"
export M31_API_LOGIN="m31.api.${RUN_SUFFIX}@example.invalid"
export M31_API_PASSWORD_FILE="$WORK/users/api-password"
export M31_HEADLESS=true
export M31_BROWSER_CHANNEL=chromium
export M31_JSON_REPORT="$WORK/playwright.json"
export M31_OUTPUT_DIR="$WORK/playwright-output"
npm --prefix "$UAT_DIR" test -- --reporter=line
echo 'authenticated customer UAT: PASS'
