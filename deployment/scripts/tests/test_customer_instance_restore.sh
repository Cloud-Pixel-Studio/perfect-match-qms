#!/usr/bin/env bash
set -euo pipefail

# Disposable Linux-only recovery rehearsal. All state is temporary and
# fictional; Demo, DEV, and customer instances are never addressed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CUSTOMER_SCRIPT="$REPO_ROOT/deployment/scripts/customer-instance.sh"
RUNTIME_LOCK="$REPO_ROOT/deployment/runtime/runtime-lock.json"
AGE_VERSION="1.2.1"
AGE_SHA256="7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50"
TEST_RELEASE="v99.99.99-rc0"
AGE_URL="https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
RUN_NUMBER="${GITHUB_RUN_ID:-$$}"
RUN_ID="${RUN_NUMBER}-$$"
SLUG="m291-dr-test-${RUN_ID}"
PORT="$((18000 + (RUN_NUMBER % 900) + (${GITHUB_RUN_ATTEMPT:-1} % 50)))"
WORK="$(mktemp -d)"
INSTANCE_ROOT="$WORK/instances"
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
  git -C "$REPO_ROOT" tag -d "$TEST_RELEASE" >/dev/null 2>&1 || true
  exit "$rc"
}
trap cleanup EXIT

for command in docker jq openssl curl sha256sum; do command -v "$command" >/dev/null; done
mkdir -p "$INSTANCE_ROOT" "$WORK/bundle" "$WORK/off-host"

git -C "$REPO_ROOT" tag "$TEST_RELEASE" HEAD
"$CUSTOMER_SCRIPT" bundle --release "$TEST_RELEASE" --output "$WORK/bundle.tar.gz" >/dev/null
ODOO_IMAGE="$(jq -er '.odoo.image' "$RUNTIME_LOCK")"
ALPINE_IMAGE="$(jq -er '.alpine.image' "$RUNTIME_LOCK")"
while IFS= read -r image; do docker pull "$image" >/dev/null; done < <(jq -er '.odoo.image, .postgres.image, .alpine.image' "$RUNTIME_LOCK")

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

# Generate an ephemeral test authority. Neither key is copied to the bundle.
openssl genpkey -algorithm Ed25519 -out "$WORK/license-key.pem" >/dev/null 2>&1
chmod 600 "$WORK/license-key.pem"
openssl pkey -in "$WORK/license-key.pem" -pubout -outform DER 2>/dev/null | tail -c 32 | base64 -w0 > "$WORK/public-key.b64"
PUBLIC_KEY="$(<"$WORK/public-key.b64")"
jq -n --arg key "$PUBLIC_KEY" '{keys:{"m29-ci-test":$key}}' > "$WORK/public_keys.json"

bash "$CUSTOMER_SCRIPT" provision "$SLUG" --bundle "$WORK/bundle.tar.gz" --type test --port "$PORT" >/dev/null
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
docker run --rm --user root -v "$REPO_ROOT:/repo:ro" -v "$WORK:/work" "$ODOO_IMAGE" \
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

# Exercise the exact M30.7 legacy layout: runtime/release did not exist, and
# the legacy runtime files are deliberately different from the approved tag.
TEST_RELEASE_SHA="$(git -C "$REPO_ROOT" rev-parse "$TEST_RELEASE^{commit}")"
SOURCE_TAG_MODULES_SHA="$(git -C "$REPO_ROOT" show "$TEST_RELEASE:deployment/customer/modules.txt" | sha256sum | awk '{print $1}')"
SOURCE_TAG_COMPOSE_SHA="$(git -C "$REPO_ROOT" show "$TEST_RELEASE:deployment/docker/customer/compose.yml.template" | sha256sum | awk '{print $1}')"
SOURCE_TAG_ODOO_SHA="$(git -C "$REPO_ROOT" show "$TEST_RELEASE:deployment/docker/customer/odoo.conf.template" | sha256sum | awk '{print $1}')"
printf '%s\n' '# legacy runtime module list is not release authority' > "$SOURCE_ROOT/runtime/modules.txt"
printf '%s\n' '# legacy runtime compose is not release authority' >> "$SOURCE_ROOT/runtime/compose.yml"
rm -rf -- "$SOURCE_ROOT/runtime/release"
[[ ! -e "$SOURCE_ROOT/runtime/release" ]]

SOURCE_HEALTH="$(bash "$CUSTOMER_SCRIPT" health "$SLUG")"
grep -Eq 'customer_http=(200|302|303)' <<<"$SOURCE_HEALTH"
TRANSACTION_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
BACKUP_OUTPUT="$(PMQMS_BACKUP_RECIPIENT_FILE="$WORK/recipient.age" PMQMS_AGE_BIN="$AGE_BIN" PMQMS_AGE_VERSION="$AGE_VERSION" \
  bash "$CUSTOMER_SCRIPT" backup "$SLUG" --recipient-file "$WORK/recipient.age" --off-host-dir "$WORK/off-host" --class intraday)"
ARCHIVE="$(printf '%s\n' "$BACKUP_OUTPUT" | sed -n 's/^backup=//p')"
[[ -s "$ARCHIVE" && -s "$WORK/off-host/$(basename "$ARCHIVE")" ]]
BACKUP_RECOVERY_POINT_UTC="$(jq -r .backup_created_utc "$ARCHIVE.manifest.json")"
SOURCE_AFTER_BACKUP="$(bash "$CUSTOMER_SCRIPT" health "$SLUG")"
grep -Eq 'customer_http=(200|302|303)' <<<"$SOURCE_AFTER_BACKUP"
bash "$CUSTOMER_SCRIPT" down "$SLUG" >/dev/null

# Recover from the distinct transferred copy, not from the source directory.
ARCHIVE="$WORK/off-host/$(basename "$ARCHIVE")"

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
grep -Fxq "restore_source_release_tag=$TEST_RELEASE" <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_source_release_sha=$TEST_RELEASE_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_release_assets_origin=approved-tag' <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_modules_sha256=$SOURCE_TAG_MODULES_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_compose_template_sha256=$SOURCE_TAG_COMPOSE_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq "restore_odoo_template_sha256=$SOURCE_TAG_ODOO_SHA" <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_release_identity=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_runtime_identity=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_license=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_customer_ready=PASS' <<<"$RESTORE_OUTPUT"
grep -Fxq 'restore_validation=pass' <<<"$RESTORE_OUTPUT"
[[ ! -e "$SOURCE_ROOT/runtime/release" ]]
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
