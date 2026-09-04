#!/usr/bin/env bash
set -euo pipefail

# Disposable Linux-only recovery rehearsal. All state is temporary and
# fictional; Demo, DEV, and customer instances are never addressed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
REPO_ROOT="$SOURCE_REPO_ROOT"
CUSTOMER_SCRIPT="$SOURCE_REPO_ROOT/deployment/scripts/customer-instance.sh"
RUNTIME_LOCK="$SOURCE_REPO_ROOT/deployment/runtime/runtime-lock.json"
AGE_VERSION="1.2.1"
AGE_SHA256="7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50"
TAG_A="v99.99.98-rc0"
TAG_B="v99.99.99-rc0"
AGE_URL="https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
RUN_NUMBER="${GITHUB_RUN_ID:-$$}"
RUN_ID="${RUN_NUMBER}-$$"
SLUG="m291-dr-test-${RUN_ID}"
PORT="$((18000 + (RUN_NUMBER % 900) + (${GITHUB_RUN_ATTEMPT:-1} % 50)))"
WORK="$(mktemp -d)"
INSTANCE_ROOT="$WORK/instances"
HISTORY_REPO=""
HIST_CUSTOMER_SCRIPT="$CUSTOMER_SCRIPT"
HIST_BACKUP_TOOL="$SOURCE_REPO_ROOT/tools/backup/m29_backup.py"
export PMQMS_CUSTOMER_INSTANCE_ROOT="$INSTANCE_ROOT"
export PMQMS_AGE_VERSION="$AGE_VERSION"
umask 077

cleanup() {
  local rc=$?
  trap - EXIT
  if [[ -f "$INSTANCE_ROOT/$SLUG/config/instance.env" ]]; then
    bash "$CUSTOMER_SCRIPT" destroy "$SLUG" --confirm-ephemeral >/dev/null 2>&1 || rc=1
  fi
  if [[ -d "$WORK" ]]; then
    if [[ -n "${ALPINE_IMAGE:-}" ]] && command -v docker >/dev/null 2>&1; then
      docker run --rm --user root -v "$WORK:/cleanup" "$ALPINE_IMAGE" \
        sh -eu -c 'rm -rf /cleanup/* /cleanup/.[!.]* /cleanup/..?*' >/dev/null 2>&1 || rc=1
    else
      rm -rf -- "$WORK" || rc=1
    fi
  fi
  if [[ -n "${HISTORY_REPO:-}" ]]; then
    git -C "$HISTORY_REPO" tag -d "$TAG_A" "$TAG_B" >/dev/null 2>&1 || true
  fi
  exit "$rc"
}
trap cleanup EXIT

for command in docker jq openssl curl sha256sum; do command -v "$command" >/dev/null; done
mkdir -p "$INSTANCE_ROOT" "$WORK/bundle" "$WORK/off-host"

curl --fail --silent --show-error --location "$AGE_URL" -o "$WORK/age.tar.gz"
printf '%s  %s\n' "$AGE_SHA256" "$WORK/age.tar.gz" | sha256sum --check --status
tar -xzf "$WORK/age.tar.gz" -C "$WORK"
AGE_BIN="$(find "$WORK" -type f -name age -perm -u+x -print -quit)"
AGE_KEYGEN="$(find "$WORK" -type f -name age-keygen -perm -u+x -print -quit)"
[[ -x "$AGE_BIN" && -x "$AGE_KEYGEN" ]]
export PMQMS_AGE_BIN="$AGE_BIN"
"$AGE_BIN" --version | grep -Eq "(^|[[:space:]])v?${AGE_VERSION//./\\.}([[:space:]]|$)"
"$AGE_KEYGEN" > "$WORK/identity.age" 2>/dev/null
chmod 600 "$WORK/identity.age"
RECIPIENT="$(sed -n -e 's/^# public key: //p' -e 's/^Public key: //p' "$WORK/identity.age")"
[[ "$RECIPIENT" =~ ^age1[[:alnum:]]+$ ]]
printf '%s\n' "$RECIPIENT" > "$WORK/recipient.age"
export PMQMS_BACKUP_RECIPIENT_FILE="$WORK/recipient.age"
export PMQMS_AGE_BIN="$AGE_BIN" PMQMS_AGE_VERSION="$AGE_VERSION"

# Generate an ephemeral test authority. Neither key is copied to the bundle.
openssl genpkey -algorithm Ed25519 -out "$WORK/license-key.pem" >/dev/null 2>&1
chmod 600 "$WORK/license-key.pem"
openssl pkey -in "$WORK/license-key.pem" -pubout -outform DER 2>/dev/null | tail -c 32 | base64 -w0 > "$WORK/public-key.b64"
PUBLIC_KEY="$(<"$WORK/public-key.b64")"
jq -n --arg key "$PUBLIC_KEY" '{keys:{"m29-ci-test":$key}}' > "$WORK/public_keys.json"

# Build two fictional, lineaged releases in a disposable repository. The
# source is provisioned at A, then upgraded to B before A is restored.
HISTORY_REPO="$WORK/history-repo"
mkdir -p "$HISTORY_REPO/deployment/scripts" "$HISTORY_REPO/tools/backup"
cp -a "$SOURCE_REPO_ROOT/addons" "$HISTORY_REPO/addons"
find "$HISTORY_REPO/addons" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$HISTORY_REPO/addons" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
mkdir -p "$HISTORY_REPO/deployment/customer" "$HISTORY_REPO/deployment/docker/customer" "$HISTORY_REPO/deployment/nginx" "$HISTORY_REPO/deployment/runtime"
cp "$SOURCE_REPO_ROOT/deployment/customer/modules.txt" "$HISTORY_REPO/deployment/customer/modules.txt"
cp "$SOURCE_REPO_ROOT/deployment/docker/customer/compose.yml.template" "$HISTORY_REPO/deployment/docker/customer/compose.yml.template"
cp "$SOURCE_REPO_ROOT/deployment/docker/customer/odoo.conf.template" "$HISTORY_REPO/deployment/docker/customer/odoo.conf.template"
cp "$SOURCE_REPO_ROOT/deployment/nginx/customer.conf.example" "$HISTORY_REPO/deployment/nginx/customer.conf.example"
cp "$SOURCE_REPO_ROOT/deployment/runtime/runtime-lock.json" "$HISTORY_REPO/deployment/runtime/runtime-lock.json"
cp "$CUSTOMER_SCRIPT" "$HISTORY_REPO/deployment/scripts/customer-instance.sh"
cp "$SOURCE_REPO_ROOT/tools/backup/m29_backup.py" "$HISTORY_REPO/tools/backup/m29_backup.py"
cp "$WORK/public_keys.json" "$HISTORY_REPO/addons/pm_qms_license/data/public_keys.json"
printf '%s\n' 'm30.8 historical release A' > "$HISTORY_REPO/addons/pm_qms_core/data/m30_8_history_marker.txt"
printf '%s\n' '# historical release A' >> "$HISTORY_REPO/deployment/customer/modules.txt"
printf '%s\n' '# historical release A' >> "$HISTORY_REPO/deployment/docker/customer/compose.yml.template"
printf '%s\n' '# historical release A' >> "$HISTORY_REPO/deployment/docker/customer/odoo.conf.template"
git -C "$HISTORY_REPO" init -q
git -C "$HISTORY_REPO" config user.email m30.8-ci@example.invalid
git -C "$HISTORY_REPO" config user.name 'M30.8 CI'
git -C "$HISTORY_REPO" add -A
git -C "$HISTORY_REPO" commit -qm 'historical release A'
git -C "$HISTORY_REPO" tag "$TAG_A"
cp "$SOURCE_REPO_ROOT/deployment/customer/modules.txt" "$HISTORY_REPO/deployment/customer/modules.txt"
cp "$SOURCE_REPO_ROOT/deployment/docker/customer/compose.yml.template" "$HISTORY_REPO/deployment/docker/customer/compose.yml.template"
cp "$SOURCE_REPO_ROOT/deployment/docker/customer/odoo.conf.template" "$HISTORY_REPO/deployment/docker/customer/odoo.conf.template"
printf '%s\n' 'm30.8 historical release B' > "$HISTORY_REPO/addons/pm_qms_core/data/m30_8_history_marker.txt"
printf '%s\n' '# historical release B' >> "$HISTORY_REPO/deployment/customer/modules.txt"
printf '%s\n' '# historical release B' >> "$HISTORY_REPO/deployment/docker/customer/compose.yml.template"
printf '%s\n' '# historical release B' >> "$HISTORY_REPO/deployment/docker/customer/odoo.conf.template"
git -C "$HISTORY_REPO" add -A
git -C "$HISTORY_REPO" commit -qm 'historical release B'
git -C "$HISTORY_REPO" tag "$TAG_B"
HIST_CUSTOMER_SCRIPT="$HISTORY_REPO/deployment/scripts/customer-instance.sh"
HIST_BACKUP_TOOL="$HISTORY_REPO/tools/backup/m29_backup.py"
RUNTIME_LOCK="$HISTORY_REPO/deployment/runtime/runtime-lock.json"
ODOO_IMAGE="$(jq -er '.odoo.image' "$RUNTIME_LOCK")"
ALPINE_IMAGE="$(jq -er '.alpine.image' "$RUNTIME_LOCK")"
while IFS= read -r image; do docker pull "$image" >/dev/null; done < <(jq -er '.odoo.image, .postgres.image, .alpine.image' "$RUNTIME_LOCK")
"$HIST_CUSTOMER_SCRIPT" bundle --release "$TAG_A" --output "$WORK/bundle-a.tar.gz" >/dev/null
"$HIST_CUSTOMER_SCRIPT" bundle --release "$TAG_B" --output "$WORK/bundle-b.tar.gz" >/dev/null
CUSTOMER_SCRIPT="$HIST_CUSTOMER_SCRIPT"

bash "$CUSTOMER_SCRIPT" provision "$SLUG" --bundle "$WORK/bundle-a.tar.gz" --type test --port "$PORT" >/dev/null
SOURCE_ROOT="$INSTANCE_ROOT/$SLUG"
# The provisioned addon tree is intentionally read-only. Overlay the ephemeral
# test key through a root container so the rehearsal never weakens that boundary.
docker run --rm --user root -v "$WORK/public_keys.json:/input/public_keys.json:ro" \
  -v "$SOURCE_ROOT/runtime/addons/pm_qms_license/data:/data" "$ALPINE_IMAGE" \
  sh -eu -c 'cp /input/public_keys.json /data/public_keys.json && chmod 644 /data/public_keys.json'
SOURCE_DB="$(jq -r .database_name "$SOURCE_ROOT/config/deployment-manifest.json")"
SOURCE_COMPOSE=(docker compose --project-name "pmqms-customer-$SLUG" --env-file "$SOURCE_ROOT/config/instance.env" -f "$SOURCE_ROOT/runtime/compose.yml")
bash "$CUSTOMER_SCRIPT" up "$SLUG" >/dev/null
"${SOURCE_COMPOSE[@]}" run --rm odoo odoo -d "$SOURCE_DB" \
  --init "pm_qms_core,pm_qms_people,pm_qms_license" --without-demo=all --stop-after-init >/dev/null
SOURCE_ENVIRONMENT_ID="$(tr -d '\n' < "$SOURCE_ROOT/config/environment_id")"
docker run --rm --user root -v "$SOURCE_REPO_ROOT:/repo:ro" -v "$WORK:/work" "$ODOO_IMAGE" \
  python3 /repo/deployment/scripts/issue-license.py --private-key /work/license-key.pem --output /work/active.pmql \
  --environment-id "$SOURCE_ENVIRONMENT_ID" --customer-name "M29 Fictional Recovery Lab" \
  --key-id m29-ci-test --license-id "M29-CI-${RUN_ID}" --company-limit 1 --site-limit 2 --named-user-limit 2 >/dev/null
bash "$CUSTOMER_SCRIPT" import-license "$SLUG" "$WORK/active.pmql" >/dev/null
bash "$CUSTOMER_SCRIPT" bootstrap "$SLUG" >/dev/null
printf 'M29 fictional attachment bytes for %s\n' "$RUN_ID" > "$WORK/attachment.txt"
chmod 644 "$WORK/attachment.txt"
mkdir "$WORK/evidence"
chmod 777 "$WORK/evidence"
cp "$WORK/attachment.txt" "$WORK/evidence/attachment.txt"
chmod 644 "$WORK/evidence/attachment.txt"
touch "$WORK/evidence/source.json"
chmod 666 "$WORK/evidence/source.json"
printf '%s' "$RUN_ID" > "$WORK/qm-password"
chmod 600 "$WORK/qm-password"
bash "$CUSTOMER_SCRIPT" bootstrap-customer "$SLUG" --company-name "M29 Fictional Recovery Lab" \
  --company-code "M29-DR-${RUN_ID}" --user-login "quality.manager.${RUN_ID}@example.invalid" \
  --user-name "M29 Recovery Quality Manager" --user-email "quality.manager.${RUN_ID}@example.invalid" \
  --user-password-file "$WORK/qm-password" >/dev/null

export M29_ORG_CODE="M29-DR-${RUN_ID}"
export M29_PROJECT_NAME="M29 Fictional Implementation ${RUN_ID}"
export M29_ATTACHMENT_NAME="M29 Known Attachment ${RUN_ID}.txt"

"${SOURCE_COMPOSE[@]}" run --rm \
  -e "M29_ORG_CODE=$M29_ORG_CODE" \
  -e "M29_PROJECT_NAME=$M29_PROJECT_NAME" \
  -e "M29_ATTACHMENT_NAME=$M29_ATTACHMENT_NAME" \
  -v "$WORK/evidence:/evidence" odoo odoo shell -d "$SOURCE_DB" --log-level=error <<'PY'
from pathlib import Path
import base64, hashlib, json, os
org = env["pm.qms.organization"].sudo().search([("code", "=", os.environ["M29_ORG_CODE"])], limit=1)
if not org:
    raise RuntimeError("fictional organization is missing")
project = env["pm.qms.implementation.project"].sudo().create({"name": os.environ["M29_PROJECT_NAME"], "organization_id": org.id, "company_id": org.company_id.id, "target_date": "2026-12-31"})
attachment = env["ir.attachment"].sudo().create({"name": os.environ["M29_ATTACHMENT_NAME"], "datas": base64.b64encode(Path("/evidence/attachment.txt").read_bytes()), "res_model": "pm.qms.organization", "res_id": org.id, "mimetype": "text/plain"})
env.cr.commit()
if not attachment.store_fname:
    raise RuntimeError("fixture attachment is not filestore-backed")
counts = {model: env[model].sudo().search_count([]) for model in ["pm.qms.organization", "pm.qms.implementation.project", "ir.attachment", "mail.message", "mail.followers", "mail.activity", "mail.mail"]}
if env["mail.mail"].sudo().search_count([("state", "=", "outgoing")]):
    raise RuntimeError("outgoing email exists")
Path("/evidence/source.json").write_text(json.dumps({"organization_code": org.code, "organization_id": org.id, "implementation_name": project.name, "implementation_id": project.id, "attachment_name": attachment.name, "attachment_sha256": hashlib.sha256(base64.b64decode(attachment.datas)).hexdigest(), "counts": counts}, sort_keys=True), encoding="utf-8")
PY
cp "$WORK/evidence/source.json" "$WORK/source.json"
SOURCE_ATTACHMENT_SHA="$(jq -r .attachment_sha256 "$WORK/source.json")"
SOURCE_COUNTS="$(jq -c .counts "$WORK/source.json")"
SOURCE_RECORD="$(jq -r .implementation_id "$WORK/source.json")"

# Establish the two release identities and compare every recovery asset against
# release A, which is intentionally older than the upgraded source at B.
TAG_A_SHA="$(git -C "$HISTORY_REPO" rev-parse "$TAG_A^{commit}")"
TAG_B_SHA="$(git -C "$HISTORY_REPO" rev-parse "$TAG_B^{commit}")"
SOURCE_TAG_MODULES_SHA="$(git -C "$HISTORY_REPO" show "$TAG_A:deployment/customer/modules.txt" | sha256sum | awk '{print $1}')"
SOURCE_TAG_COMPOSE_SHA="$(git -C "$HISTORY_REPO" show "$TAG_A:deployment/docker/customer/compose.yml.template" | sha256sum | awk '{print $1}')"
SOURCE_TAG_ODOO_SHA="$(git -C "$HISTORY_REPO" show "$TAG_A:deployment/docker/customer/odoo.conf.template" | sha256sum | awk '{print $1}')"
addon_tree_hash() { (cd "$1" && find addons -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}'); }
mkdir "$WORK/tag-a" "$WORK/tag-b"
git -C "$HISTORY_REPO" archive "$TAG_A" addons | tar -x -C "$WORK/tag-a"
git -C "$HISTORY_REPO" archive "$TAG_B" addons | tar -x -C "$WORK/tag-b"
TAG_A_ADDONS_SHA="$(addon_tree_hash "$WORK/tag-a")"
TAG_B_ADDONS_SHA="$(addon_tree_hash "$WORK/tag-b")"
BACKUP_RUNTIME_LOCK_SHA="$(sha256sum "$HISTORY_REPO/deployment/runtime/runtime-lock.json" | awk '{print $1}')"

SOURCE_RELEASE_BEFORE_UPGRADE="$(jq -r .product_version "$SOURCE_ROOT/config/deployment-manifest.json")"
[[ "$SOURCE_RELEASE_BEFORE_UPGRADE" == "$TAG_A" ]]
SOURCE_HEALTH="$(bash "$CUSTOMER_SCRIPT" health "$SLUG")"
grep -Eq 'customer_http=(200|302|303)' <<<"$SOURCE_HEALTH"
TRANSACTION_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BACKUP_OUTPUT="$(PMQMS_BACKUP_RECIPIENT_FILE="$WORK/recipient.age" PMQMS_AGE_BIN="$AGE_BIN" PMQMS_AGE_VERSION="$AGE_VERSION" \
  bash "$CUSTOMER_SCRIPT" backup "$SLUG" --recipient-file "$WORK/recipient.age" --off-host-dir "$WORK/off-host" --class intraday)"
ARCHIVE="$(printf '%s\n' "$BACKUP_OUTPUT" | sed -n 's/^backup=//p')"
[[ -s "$ARCHIVE" && -s "$WORK/off-host/$(basename "$ARCHIVE")" ]]
jq -e '.components | map(.name) | index("product-manifest.json")' "$ARCHIVE.manifest.json" >/dev/null
BACKUP_RECOVERY_POINT_UTC="$(jq -r .backup_created_utc "$ARCHIVE.manifest.json")"
SOURCE_AFTER_BACKUP="$(bash "$CUSTOMER_SCRIPT" health "$SLUG")"
grep -Eq 'customer_http=(200|302|303)' <<<"$SOURCE_AFTER_BACKUP"

# Move the source to release B, then retain and restore the older A backup.
bash "$CUSTOMER_SCRIPT" upgrade "$SLUG" --bundle "$WORK/bundle-b.tar.gz" --to "$TAG_B" >/dev/null
SOURCE_RELEASE_AFTER_UPGRADE="$(jq -r .product_version "$SOURCE_ROOT/config/deployment-manifest.json")"
SOURCE_SHA_AFTER_UPGRADE="$(jq -r .source_release_sha "$SOURCE_ROOT/config/deployment-manifest.json")"
[[ "$SOURCE_RELEASE_AFTER_UPGRADE" == "$TAG_B" && "$SOURCE_SHA_AFTER_UPGRADE" == "$TAG_B_SHA" ]]
grep -Fxq 'm30.8 historical release B' "$SOURCE_ROOT/runtime/addons/pm_qms_core/data/m30_8_history_marker.txt"
SOURCE_ADDONS_AFTER_UPGRADE_SHA="$(addon_tree_hash "$SOURCE_ROOT/runtime")"
[[ "$SOURCE_ADDONS_AFTER_UPGRADE_SHA" == "$TAG_B_ADDONS_SHA" ]]
bash "$CUSTOMER_SCRIPT" down "$SLUG" >/dev/null

# Recover from the distinct transferred copy, not from the source directory.
ARCHIVE="$WORK/off-host/$(basename "$ARCHIVE")"

# Build a valid-looking archive whose tag and SHA disagree. It must fail before
# recovery initialization and leave no recovery instance behind.
BAD_PAYLOAD="$WORK/bad-payload"
mkdir "$BAD_PAYLOAD"
python3 "$HIST_BACKUP_TOOL" unpack --archive "$ARCHIVE" --identity-file "$WORK/identity.age" --output "$BAD_PAYLOAD" >/dev/null
BAD_SHA="$(printf '0%.0s' {1..40})"
jq --arg sha "$BAD_SHA" \
  '.source_release_sha=$sha' "$BAD_PAYLOAD/deployment-manifest.json" > "$BAD_PAYLOAD/deployment-manifest.json.tmp"
mv "$BAD_PAYLOAD/deployment-manifest.json.tmp" "$BAD_PAYLOAD/deployment-manifest.json"
jq --arg sha "$BAD_SHA" \
  '.source_sha=$sha | .source_release_sha=$sha' "$BAD_PAYLOAD/product-manifest.json" > "$BAD_PAYLOAD/product-manifest.json.tmp"
mv "$BAD_PAYLOAD/product-manifest.json.tmp" "$BAD_PAYLOAD/product-manifest.json"
BAD_COMPONENT_ARGS=()
for component in db.dump filestore.tar.gz environment_id runtime-lock.json deployment-manifest.json product-manifest.json; do
  BAD_COMPONENT_ARGS+=(--component "$component=$BAD_PAYLOAD/$component")
done
BAD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 "$HIST_BACKUP_TOOL" pack --output "$WORK/off-host/mismatched.tar.age" --recipient-file "$WORK/recipient.age" \
  --source-instance "$SLUG" --source-database "$SOURCE_DB" --source-environment-id "$SOURCE_ENVIRONMENT_ID" \
  --product-version "$TAG_A" --source-release-sha "$BAD_SHA" --recovery-point-class intraday \
  --created-utc "$BAD_TIME" --quiesce-start-utc "$BAD_TIME" --database-snapshot-utc "$BAD_TIME" \
  --filestore-snapshot-utc "$BAD_TIME" --quiesce-end-utc "$BAD_TIME" "${BAD_COMPONENT_ARGS[@]}" >/dev/null
set +e
MISMATCHED_OUTPUT="$(PMQMS_AGE_BIN="$AGE_BIN" PMQMS_AGE_VERSION="$AGE_VERSION" \
  bash "$CUSTOMER_SCRIPT" restore-validate "$SLUG" "$WORK/off-host/mismatched.tar.age" \
  --identity-file "$WORK/identity.age" 2>&1)"
MISMATCHED_STATUS=$?
set -e
[[ "$MISMATCHED_STATUS" == 2 ]]
grep -Fq "release tag/source identity mismatch: $TAG_A" <<<"$MISMATCHED_OUTPUT"
[[ ! -e "$INSTANCE_ROOT/${SLUG}-recovery" ]]

# The real restore command must reject wrong identity and non-empty extraction.
! python3 "$REPO_ROOT/tools/backup/m29_backup.py" verify --archive "$ARCHIVE" --identity-file "$WORK/identity.age" \
  --expected-instance wrong --expected-database "$SOURCE_DB" >/dev/null 2>&1
mkdir "$WORK/nonempty"
printf x > "$WORK/nonempty/file"
! python3 "$REPO_ROOT/tools/backup/m29_backup.py" unpack --archive "$ARCHIVE" --identity-file "$WORK/identity.age" --output "$WORK/nonempty" >/dev/null 2>&1

jq --arg sha "0000000000000000000000000000000000000000000000000000000000000000" \
  '.attachment_sha256=$sha' "$WORK/source.json" > "$WORK/evidence/bad-verification.json"
chmod 644 "$WORK/evidence/bad-verification.json"
! M29_ORG_CODE="$M29_ORG_CODE" M29_PROJECT_NAME="$M29_PROJECT_NAME" M29_ATTACHMENT_NAME="$M29_ATTACHMENT_NAME" \
  PMQMS_AGE_BIN="$AGE_BIN" PMQMS_AGE_VERSION="$AGE_VERSION" \
  bash "$CUSTOMER_SCRIPT" restore-validate "$SLUG" "$ARCHIVE" --identity-file "$WORK/identity.age" \
  --verification-file "$WORK/evidence/bad-verification.json" >/dev/null 2>&1
[[ ! -e "$INSTANCE_ROOT/${SLUG}-recovery" ]]

cp "$WORK/source.json" "$WORK/evidence/verification.json"
chmod 644 "$WORK/evidence/verification.json"
RTO_START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RTO_START_EPOCH="$(date +%s)"
RESTORE_OUTPUT="$(M29_ORG_CODE="$M29_ORG_CODE" M29_PROJECT_NAME="$M29_PROJECT_NAME" M29_ATTACHMENT_NAME="$M29_ATTACHMENT_NAME" \
  PMQMS_AGE_BIN="$AGE_BIN" PMQMS_AGE_VERSION="$AGE_VERSION" \
  bash "$CUSTOMER_SCRIPT" restore-validate "$SLUG" "$ARCHIVE" --identity-file "$WORK/identity.age" \
  --verification-file "$WORK/evidence/verification.json" 2>&1)"
printf '%s\n' "$RESTORE_OUTPUT" > "$WORK/restore-output.txt"
grep -Fxq "restore_source_release_tag=$TAG_A" <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_source_release_sha=$TAG_A_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_release_assets_origin=approved-tag' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_addons_origin=approved-tag' <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_addons_sha256=$TAG_A_ADDONS_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_backup_product_manifest_origin=backup' <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_runtime_lock_sha256=$BACKUP_RUNTIME_LOCK_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_deployment_manifest_origin=backup' <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_modules_sha256=$SOURCE_TAG_MODULES_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_compose_template_sha256=$SOURCE_TAG_COMPOSE_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_odoo_template_sha256=$SOURCE_TAG_ODOO_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_release_identity=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_runtime_identity=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_license=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_customer_ready=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_validation=pass' <<<"$RESTORE_OUTPUT"
[[ -e "$SOURCE_ROOT/runtime/release" ]]
cp "$WORK/evidence/restored.json" "$WORK/restored.json"
RTO_END_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RTO_END_EPOCH="$(date +%s)"
RTO_SECONDS="$((RTO_END_EPOCH - RTO_START_EPOCH))"
RESTORED_COUNTS="$(jq -c .counts "$WORK/restored.json")"
RESTORED_ATTACHMENT_SHA="$(jq -r .attachment_sha256 "$WORK/restored.json")"
[[ "$SOURCE_ATTACHMENT_SHA" == "$RESTORED_ATTACHMENT_SHA" ]]
[[ "$SOURCE_COUNTS" == "$RESTORED_COUNTS" ]]
[[ "$(jq -r .organization_code "$WORK/restored.json")" == "$M29_ORG_CODE" ]]
[[ "$(jq -r .implementation_id "$WORK/restored.json")" == "$SOURCE_RECORD" ]]

# An older archive without the new optional product manifest remains valid.
LEGACY_PAYLOAD="$WORK/legacy-payload"
mkdir "$LEGACY_PAYLOAD"
python3 "$HIST_BACKUP_TOOL" unpack --archive "$ARCHIVE" --identity-file "$WORK/identity.age" \
  --output "$LEGACY_PAYLOAD" >/dev/null
rm -f "$LEGACY_PAYLOAD/product-manifest.json"
LEGACY_COMPONENT_ARGS=()
for component in db.dump filestore.tar.gz environment_id runtime-lock.json deployment-manifest.json; do
  LEGACY_COMPONENT_ARGS+=(--component "$component=$LEGACY_PAYLOAD/$component")
done
if [[ -f "$WORK/active.pmql" ]]; then
  LEGACY_COMPONENT_ARGS+=(--component "active.pmql=$WORK/active.pmql")
fi
LEGACY_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 "$HIST_BACKUP_TOOL" pack --output "$WORK/off-host/legacy.tar.age" --recipient-file "$WORK/recipient.age" \
  --source-instance "$SLUG" --source-database "$SOURCE_DB" --source-environment-id "$SOURCE_ENVIRONMENT_ID" \
  --product-version "$TAG_A" --source-release-sha "$TAG_A_SHA" --recovery-point-class intraday \
  --created-utc "$LEGACY_TIME" --quiesce-start-utc "$LEGACY_TIME" --database-snapshot-utc "$LEGACY_TIME" \
  --filestore-snapshot-utc "$LEGACY_TIME" --quiesce-end-utc "$LEGACY_TIME" "${LEGACY_COMPONENT_ARGS[@]}" >/dev/null

# Exercise the M30.7 legacy layout as well: current source B has no persisted
# release directory, so restore must still reconstruct backup A from its tag.
SOURCE_RELEASE_AFTER_RESTORE="$(jq -r .product_version "$SOURCE_ROOT/config/deployment-manifest.json")"
SOURCE_SHA_AFTER_RESTORE="$(jq -r .source_release_sha "$SOURCE_ROOT/config/deployment-manifest.json")"
printf '%s\n' '# legacy runtime module list is not release authority' > "$SOURCE_ROOT/runtime/modules.txt"
printf '%s\n' '# legacy runtime compose is not release authority' > "$SOURCE_ROOT/runtime/compose.yml"
rm -rf -- "$SOURCE_ROOT/runtime/release"
[[ ! -e "$SOURCE_ROOT/runtime/release" ]]
LEGACY_OUTPUT="$(PMQMS_AGE_BIN="$AGE_BIN" PMQMS_AGE_VERSION="$AGE_VERSION" \
  bash "$CUSTOMER_SCRIPT" restore-validate "$SLUG" "$WORK/off-host/legacy.tar.age" \
  --identity-file "$WORK/identity.age" --verification-file "$WORK/evidence/verification.json" 2>&1)"
grep -Fxq "restore_source_release_tag=$TAG_A" <<<"$LEGACY_OUTPUT"
grep -Fxq "restore_source_release_sha=$TAG_A_SHA" <<<"$LEGACY_OUTPUT"
grep -Fxq 'restore_release_assets_origin=approved-tag' <<<"$LEGACY_OUTPUT"
grep -Fxq 'restore_addons_origin=approved-tag' <<<"$LEGACY_OUTPUT"
grep -Fxq "restore_addons_sha256=$TAG_A_ADDONS_SHA" <<<"$LEGACY_OUTPUT"
grep -Fxq 'restore_backup_product_manifest_origin=deterministic-backup-identity' <<<"$LEGACY_OUTPUT"
grep -Fxq 'restore_deployment_manifest_origin=backup' <<<"$LEGACY_OUTPUT"
grep -Fxq 'restore_validation=pass' <<<"$LEGACY_OUTPUT"
[[ ! -e "$INSTANCE_ROOT/${SLUG}-recovery" ]]
SOURCE_RELEASE_FINAL="$(jq -r .product_version "$SOURCE_ROOT/config/deployment-manifest.json")"
SOURCE_SHA_FINAL="$(jq -r .source_release_sha "$SOURCE_ROOT/config/deployment-manifest.json")"
SOURCE_ADDONS_FINAL_SHA="$(addon_tree_hash "$SOURCE_ROOT/runtime")"
[[ "$SOURCE_RELEASE_AFTER_RESTORE" == "$TAG_B" && "$SOURCE_SHA_AFTER_RESTORE" == "$TAG_B_SHA" ]]
[[ "$SOURCE_RELEASE_FINAL" == "$TAG_B" && "$SOURCE_SHA_FINAL" == "$TAG_B_SHA" ]]
[[ "$SOURCE_ADDONS_AFTER_UPGRADE_SHA" == "$SOURCE_ADDONS_FINAL_SHA" ]]

RPO_SECONDS="$(( $(date -d "$BACKUP_RECOVERY_POINT_UTC" +%s) - $(date -d "$TRANSACTION_UTC" +%s) ))"
[[ "$RPO_SECONDS" -ge 0 && "$RPO_SECONDS" -le 21600 ]]
printf 'real_restore=PASS\n'
printf 'source_service_before_backup=running\n'
printf 'source_service_after_backup=running\n'
printf 'source_service_during_restore=stopped\n'
printf 'source_record_id=%s\n' "$SOURCE_RECORD"
printf 'source_counts=%s\n' "$SOURCE_COUNTS"
printf 'restored_counts=%s\n' "$RESTORED_COUNTS"
printf 'attachment_sha256=%s\n' "$RESTORED_ATTACHMENT_SHA"
printf 'transaction_utc=%s\n' "$TRANSACTION_UTC"
printf 'recovery_point_utc=%s\n' "$BACKUP_RECOVERY_POINT_UTC"
printf 'demonstrated_rpo_seconds=%s\n' "$RPO_SECONDS"
printf 'rpo_target_seconds=21600\n'
printf 'recurring_schedule_proven=NO\n'
printf 'rto_start_utc=%s\n' "$RTO_START_UTC"
printf 'rto_end_utc=%s\n' "$RTO_END_UTC"
printf 'rto_seconds=%s\n' "$RTO_SECONDS"
printf 'rto_target_seconds=28800\n'
