#!/usr/bin/env bash
set -euo pipefail

# Disposable integration rehearsal for the supported unlicensed bootstrap
# boundary. It never addresses Demo, DEV, or a customer instance.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
CUSTOMER_SCRIPT="$REPO_ROOT/deployment/scripts/customer-instance.sh"
RUNTIME_LOCK="$REPO_ROOT/deployment/runtime/runtime-lock.json"
WORK="$(mktemp -d)"
INSTANCE_ROOT="$WORK/instances"
export PMQMS_CUSTOMER_INSTANCE_ROOT="$INSTANCE_ROOT"
export TMPDIR="$WORK/tmp"
mkdir -p "$INSTANCE_ROOT" "$TMPDIR"
umask 077

RUN_ID="${GITHUB_RUN_ID:-local}-$$"
RUN_SUFFIX="$(printf '%s' "$RUN_ID" | tr -cd '[:alnum:]' | cut -c1-24)"
SLUG="m312-bootstrap-${RUN_SUFFIX}"
PORT="$((18000 + ($$ % 900)))"
TAG=""
TAG_CREATED=0

fail() { echo "FAIL: $*" >&2; exit 1; }

cleanup() {
  local rc=$?
  trap - EXIT
  if [[ -f "$INSTANCE_ROOT/$SLUG/config/instance.env" ]]; then
    bash "$CUSTOMER_SCRIPT" destroy "$SLUG" --confirm-ephemeral >/dev/null 2>&1 || rc=1
  fi
  local -a containers=()
  mapfile -t containers < <(docker ps -aq --filter "label=com.docker.compose.project=pmqms-customer-${SLUG}")
  if ((${#containers[@]})); then
    docker rm -f "${containers[@]}" >/dev/null 2>&1 || rc=1
  fi
  docker volume rm "pmqms_${SLUG}_odoo_data" "pmqms_${SLUG}_postgres" >/dev/null 2>&1 || true
  if [[ -n "${ALPINE_IMAGE:-}" && -d "$WORK" ]]; then
    docker run --rm --user root -v "$WORK:/cleanup" "$ALPINE_IMAGE" \
      sh -c 'rm -rf /cleanup/* /cleanup/.[!.]* /cleanup/..?*' >/dev/null 2>&1 || rc=1
  fi
  rm -rf -- "$WORK" || rc=1
  if [[ "$TAG_CREATED" == 1 ]]; then
    git -C "$REPO_ROOT" tag -d "$TAG" >/dev/null 2>&1 || rc=1
  fi
  exit "$rc"
}
trap cleanup EXIT

for command in docker git jq openssl curl sha256sum; do
  command -v "$command" >/dev/null || fail "required command missing: $command"
done

ODOO_IMAGE="$(jq -er '.odoo.image' "$RUNTIME_LOCK")"
ALPINE_IMAGE="$(jq -er '.alpine.image' "$RUNTIME_LOCK")"
while IFS= read -r image; do
  docker pull "$image" >/dev/null
done < <(jq -er '.odoo.image, .postgres.image, .alpine.image' "$RUNTIME_LOCK")

for patch in {90..99}; do
  candidate="v99.99.${patch}-rc0"
  if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "refs/tags/$candidate" >/dev/null; then
    TAG="$candidate"
    break
  fi
done
[[ -n "$TAG" ]] || fail "no disposable release tag is available"
git -C "$REPO_ROOT" tag "$TAG"
TAG_CREATED=1

bash "$CUSTOMER_SCRIPT" bundle --release "$TAG" --output "$WORK/customer-bundle.tar.gz" >/dev/null
bash "$CUSTOMER_SCRIPT" provision "$SLUG" --bundle "$WORK/customer-bundle.tar.gz" --type test --port "$PORT" >/dev/null
ROOT="$INSTANCE_ROOT/$SLUG"
[[ ! -e "$ROOT/license/active.pmql" ]] || fail "license unexpectedly exists before bootstrap"

# Install-time validation uses the real production module set. The initial
# bootstrap must work before any commercial capacity exists.
if ! bash "$CUSTOMER_SCRIPT" bootstrap "$SLUG" >"$WORK/bootstrap.log" 2>&1; then
  tail -80 "$WORK/bootstrap.log" >&2
  fail "bootstrap without license failed"
fi
grep -Eq 'customer_http=(200|302|303)' "$WORK/bootstrap.log" || fail "bootstrap health was not proven"
[[ ! -e "$ROOT/license/active.pmql" ]] || fail "bootstrap created a license"

LICENSE_STATUS="$(bash "$CUSTOMER_SCRIPT" license-status "$SLUG")"
grep -Fqx 'license_status=missing' <<<"$LICENSE_STATUS" || fail "post-bootstrap license status is not missing"

ACTIVATION_OUTPUT="$(bash "$CUSTOMER_SCRIPT" activation-request "$SLUG")"
grep -Fq 'activation-request.json' <<<"$ACTIVATION_OUTPUT" || fail "activation request was not reported"
[[ -s "$ROOT/activation/activation-request.json" ]] || fail "activation request was not created"

# The operator guard must reject commercial bootstrap before activation.
set +e
BOOTSTRAP_CUSTOMER_OUTPUT="$(bash "$CUSTOMER_SCRIPT" bootstrap-customer "$SLUG" \
  --company-name "M31 Disposable Components" --company-code M31-DISPOSABLE \
  --user-login "quality.manager.${RUN_SUFFIX}@example.invalid" \
  --user-name "M31 Disposable Quality Manager" 2>&1)"
BOOTSTRAP_CUSTOMER_STATUS=$?
set -e
[[ "$BOOTSTRAP_CUSTOMER_STATUS" -ne 0 ]] || fail "bootstrap-customer bypassed missing license"
grep -Fq 'import a signed license before customer bootstrap' <<<"$BOOTSTRAP_CUSTOMER_OUTPUT" ||
  fail "bootstrap-customer missing-license error changed unexpectedly"

# Create a fictional signed license and install its public key only into this
# disposable runtime. The repository key registry and tracked files are not
# changed.
openssl genpkey -algorithm Ed25519 -out "$WORK/license-key.pem" >/dev/null 2>&1
openssl pkey -in "$WORK/license-key.pem" -pubout -outform DER 2>/dev/null |
  tail -c 32 | base64 -w0 > "$WORK/public-key.b64"
PUBLIC_KEY="$(<"$WORK/public-key.b64")"
jq -n --arg key "$PUBLIC_KEY" '{keys:{"m312-ci-test":$key}}' > "$WORK/public_keys.json"
docker run --rm --user root -v "$WORK/public_keys.json:/input/public_keys.json:ro" \
  -v "$ROOT/runtime/addons/pm_qms_license/data:/data" "$ALPINE_IMAGE" \
  sh -eu -c 'cp /input/public_keys.json /data/public_keys.json && chmod 644 /data/public_keys.json'

ENVIRONMENT_ID="$(tr -d '\n' < "$ROOT/config/environment_id")"
docker run --rm --user root -v "$REPO_ROOT:/repo:ro" -v "$WORK:/work" "$ODOO_IMAGE" \
  python3 /repo/deployment/scripts/issue-license.py \
  --private-key /work/license-key.pem --output /work/active.pmql \
  --environment-id "$ENVIRONMENT_ID" --customer-name "M31 Disposable Components" \
  --key-id m312-ci-test --license-id "M31-CI-${RUN_SUFFIX}" \
  --company-limit 1 --site-limit 2 --named-user-limit 2 >/dev/null
bash "$CUSTOMER_SCRIPT" import-license "$SLUG" "$WORK/active.pmql" >/dev/null
LICENSE_STATUS="$(bash "$CUSTOMER_SCRIPT" license-status "$SLUG")"
grep -Eq '^license_status=(valid|expiring) ' <<<"$LICENSE_STATUS" || fail "test license is not active"

printf '%s' "$RUN_SUFFIX" > "$WORK/quality-manager-password"
chmod 600 "$WORK/quality-manager-password"
bash "$CUSTOMER_SCRIPT" bootstrap-customer "$SLUG" \
  --company-name "M31 Disposable Components" --company-code M31-DISPOSABLE \
  --user-login "quality.manager.${RUN_SUFFIX}@example.invalid" \
  --user-name "M31 Disposable Quality Manager" \
  --user-email "quality.manager.${RUN_SUFFIX}@example.invalid" \
  --user-password-file "$WORK/quality-manager-password" >/dev/null
bash "$CUSTOMER_SCRIPT" create-site "$SLUG" \
  --code M31-HQ --name "M31 Disposable Headquarters" --type headquarters >/dev/null
bash "$CUSTOMER_SCRIPT" customer-ready "$SLUG" >"$WORK/customer-ready.log"
grep -Fqx 'CUSTOMER_READY=YES' "$WORK/customer-ready.log" || fail "licensed customer was not ready"

echo "unlicensed customer bootstrap and activation rehearsal: PASS"
