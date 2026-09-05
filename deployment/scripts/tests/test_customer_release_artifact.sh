#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$SCRIPT_DIR/customer-instance.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TEST_ROOT="$(mktemp -d)"
export PMQMS_CUSTOMER_INSTANCE_ROOT="$TEST_ROOT/instances"
export TMPDIR="$TEST_ROOT/tmp"
mkdir -p "$PMQMS_CUSTOMER_INSTANCE_ROOT" "$TMPDIR"
VALID="$TEST_ROOT/valid.tar.gz"
VALID_DIR="$TEST_ROOT/valid"
VALID_SLUG="m30-7-valid"
TEST_RELEASE="v99.99.99-rc0"

fail() { echo "FAIL: $*" >&2; exit 1; }
expect_fail() {
  local label="$1"; shift
  if "$@" >"$TEST_ROOT/$label.out" 2>&1; then
    fail "$label unexpectedly succeeded"
  fi
}
cleanup() {
  git -C "$REPO_ROOT" tag -d "$TEST_RELEASE" >/dev/null 2>&1 || true
  chmod -R u+w "$TEST_ROOT" 2>/dev/null || true
  rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT

repack_variant() {
  local name="$1" dir="$TEST_ROOT/$1" output="$TEST_ROOT/$1.tar.gz"
  (cd "$dir" && { find addons deployment -type f -print0; printf 'manifest.json\0'; } | sort -z | xargs -0 sha256sum > checksums.sha256)
  tar -C "$dir" -czf "$output" .
  write_outer_checksum "$output"
  printf '%s\n' "$output"
}
repack_without_checksum_update() {
  local name="$1" dir="$TEST_ROOT/$1" output="$TEST_ROOT/$1.tar.gz"
  tar -C "$dir" -czf "$output" .
  write_outer_checksum "$output"
  printf '%s\n' "$output"
}
write_outer_checksum() {
  local output="$1"
  printf '%s  %s\n' "$(sha256sum "$output" | awk '{print $1}')" "$(basename "$output")" > "$output.sha256"
}
variant_from_valid() {
  local name="$1" dir="$TEST_ROOT/$1"
  rm -rf "$dir"
  mkdir -p "$dir"
  tar -xzf "$VALID" -C "$dir"
}
set_manifest() {
  local name="$1" filter="$2" dir="$TEST_ROOT/$1"
  jq "$filter" "$dir/manifest.json" > "$dir/manifest.json.tmp"
  mv "$dir/manifest.json.tmp" "$dir/manifest.json"
}
provision_variant_should_fail() {
  local label="$1" variant="$2" slug="$3"
  expect_fail "$label" "$SCRIPT" provision "$slug" --bundle "$TEST_ROOT/$variant.tar.gz" --type test --port 19108
  [[ ! -e "$PMQMS_CUSTOMER_INSTANCE_ROOT/$slug" ]] || fail "$label left a persistent instance"
}

provision_variant_should_fail_with_reason() {
  local label="$1" variant="$2" slug="$3" reason="$4"
  provision_variant_should_fail "$label" "$variant" "$slug"
  grep -Fq "$reason" "$TEST_ROOT/$label.out" || fail "$label did not report $reason"
}

provision_path_should_fail_with_reason() {
  local label="$1" bundle="$2" slug="$3" reason="$4"
  expect_fail "$label" "$SCRIPT" provision "$slug" --bundle "$bundle" --type test --port 19112
  [[ ! -e "$PMQMS_CUSTOMER_INSTANCE_ROOT/$slug" ]] || fail "$label left a persistent instance"
  grep -Fq "$reason" "$TEST_ROOT/$label.out" || fail "$label did not report $reason"
}

expect_fail bundle-no-release "$SCRIPT" bundle --output "$TEST_ROOT/missing-release.tar.gz"
expect_fail init-no-release "$SCRIPT" init m30-7-no-release --type test --port 19109
expect_fail unknown-release-tag "$SCRIPT" bundle --release v99.98.97-rc0 --output "$TEST_ROOT/unknown.tar.gz"

git -C "$REPO_ROOT" tag "$TEST_RELEASE" HEAD
"$SCRIPT" bundle --release "$TEST_RELEASE" --output "$VALID" >"$TEST_ROOT/valid.out"
[[ -s "$VALID" && -s "$VALID.sha256" ]] || fail "valid tagged bundle was not built"
tar -xOzf "$VALID" ./manifest.json | jq -e --arg release "$TEST_RELEASE" '.product_version == $release and .release_tag == $release and (.source_sha | test("^[0-9a-f]{40}$")) and .contains_demo_data == false and .contains_private_signing_key == false' >/dev/null || fail "valid bundle manifest is not self-identifying"

variant_from_valid product-mismatch
set_manifest product-mismatch '.product_version = "v1.0.0-rc10"'
repack_variant product-mismatch >/dev/null
provision_variant_should_fail product-version-mismatch product-mismatch m30-7-product-mismatch

variant_from_valid source-invalid
set_manifest source-invalid '.source_sha = "INVALID"'
repack_variant source-invalid >/dev/null
provision_variant_should_fail source-sha-invalid source-invalid m30-7-source-invalid

variant_from_valid source-missing
set_manifest source-missing 'del(.source_sha)'
repack_variant source-missing >/dev/null
provision_variant_should_fail source-sha-missing source-missing m30-7-source-missing

variant_from_valid source-tag-mismatch
set_manifest source-tag-mismatch '.source_sha = ("a" * 40)'
repack_variant source-tag-mismatch >/dev/null
provision_variant_should_fail_with_reason source-sha-release-mismatch source-tag-mismatch m30-7-source-tag-mismatch SOURCE_SHA_DOES_NOT_MATCH_RELEASE_TAG

variant_from_valid runtime-mismatch
set_manifest runtime-mismatch '.runtime_lock_sha256 = ("0" * 64)'
repack_variant runtime-mismatch >/dev/null
provision_variant_should_fail runtime-lock-mismatch runtime-mismatch m30-7-runtime-mismatch

variant_from_valid internal-tamper
printf 'tampered fixture content\n' >> "$(find "$TEST_ROOT/internal-tamper/addons" -type f -print -quit)"
repack_without_checksum_update internal-tamper >/dev/null
provision_variant_should_fail internal-checksum-tamper internal-tamper m30-7-internal-tamper

variant_from_valid manifest-internal-tamper
set_manifest manifest-internal-tamper '.product_version = "v99.99.99-rc1"'
repack_without_checksum_update manifest-internal-tamper >/dev/null
provision_variant_should_fail_with_reason manifest-checksum-tamper manifest-internal-tamper m30-7-manifest-tamper 'bundle internal checksum mismatch'

variant_from_valid payload-tamper
PAYLOAD_FILE="$(find "$TEST_ROOT/payload-tamper/addons" -type f -name '*.py' -print -quit)"
[[ -n "$PAYLOAD_FILE" ]] || fail "payload-tamper fixture has no Python source file"
printf '\n# M30.7 payload tamper fixture\n' >> "$PAYLOAD_FILE"
repack_variant payload-tamper >/dev/null
provision_variant_should_fail_with_reason payload-release-mismatch payload-tamper m30-7-payload-tamper PAYLOAD_DOES_NOT_MATCH_RELEASE_TAG

variant_from_valid extra-governed-file
mkdir -p "$TEST_ROOT/extra-governed-file/addons/m30_7_extra"
printf 'fixture_extra = True\n' > "$TEST_ROOT/extra-governed-file/addons/m30_7_extra/extra.py"
repack_variant extra-governed-file >/dev/null
provision_variant_should_fail_with_reason extra-governed-file extra-governed-file m30-7-extra-governed-file PAYLOAD_DOES_NOT_MATCH_RELEASE_TAG

variant_from_valid demo-contamination
set_manifest demo-contamination '.contains_demo_data = true'
repack_variant demo-contamination >/dev/null
provision_variant_should_fail demo-contamination demo-contamination m30-7-demo-contamination

variant_from_valid private-key-contamination
set_manifest private-key-contamination '.contains_private_signing_key = true'
repack_variant private-key-contamination >/dev/null
provision_variant_should_fail private-key-contamination private-key-contamination m30-7-private-key-contamination

variant_from_valid unauthorized-environment
set_manifest unauthorized-environment '.environment_types = ["customer"]'
repack_variant unauthorized-environment >/dev/null
provision_variant_should_fail unauthorized-environment unauthorized-environment m30-7-unauthorized-environment

"$SCRIPT" provision "$VALID_SLUG" --bundle "$VALID" --type test --port 19107 >"$TEST_ROOT/provision.out"
ROOT="$PMQMS_CUSTOMER_INSTANCE_ROOT/$VALID_SLUG"
grep -Fxq "PRODUCT_VERSION=$TEST_RELEASE" "$ROOT/config/instance.env" || fail "product version was not derived from bundle"
TAG_SHA="$(git -C "$REPO_ROOT" rev-parse "refs/tags/$TEST_RELEASE^{commit}")"
grep -Fxq "SOURCE_RELEASE_SHA=$TAG_SHA" "$ROOT/config/instance.env" || fail "source release SHA was not derived from bundle"
jq -e --arg source "$TAG_SHA" '.source_sha == $source' "$ROOT/config/product-manifest.json" >/dev/null || fail "product manifest source SHA does not match release tag"
jq -e --arg release "$TEST_RELEASE" --arg source "$TAG_SHA" '.product_version == $release and .source_release_sha == $source' "$ROOT/config/deployment-manifest.json" >/dev/null || fail "deployment identity was not persisted"
jq -e --arg release "$TEST_RELEASE" --arg source "$TAG_SHA" '.product_version == $release and .source_sha == $source' "$ROOT/config/product-manifest.json" >/dev/null || fail "product identity was not persisted"

PORTABLE_A="$TEST_ROOT/portable-a"
PORTABLE_B="$TEST_ROOT/portable-b"
mkdir -p "$PORTABLE_A" "$PORTABLE_B"
"$SCRIPT" bundle --release "$TEST_RELEASE" --output "$PORTABLE_A/portable.tar.gz" >"$TEST_ROOT/portable-build.out"
cp "$PORTABLE_A/portable.tar.gz" "$PORTABLE_A/portable.tar.gz.sha256" "$PORTABLE_B/"
"$SCRIPT" provision m30-7-portable --bundle "$PORTABLE_B/portable.tar.gz" --type test --port 19113 >"$TEST_ROOT/portable-provision.out"
[[ -f "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-7-portable/config/instance.env" ]] || fail "moved bundle did not provision"
printf 'tampered moved bundle\n' >> "$PORTABLE_B/portable.tar.gz"
provision_path_should_fail_with_reason altered-moved-bundle "$PORTABLE_B/portable.tar.gz" m30-7-portable-tampered "bundle outer checksum mismatch"

cp "$VALID" "$TEST_ROOT/multiple-sidecar.tar.gz"
VALID_SIDE_LINE="$(< "$VALID.sha256")"
printf '%s\n%s\n' "$VALID_SIDE_LINE" "$VALID_SIDE_LINE" > "$TEST_ROOT/multiple-sidecar.tar.gz.sha256"
provision_path_should_fail_with_reason multiple-sidecar "$TEST_ROOT/multiple-sidecar.tar.gz" m30-7-multiple-sidecar "bundle checksum sidecar is invalid"

cp "$VALID" "$TEST_ROOT/redirected-sidecar.tar.gz"
VALID_DIGEST="$(sha256sum "$VALID" | awk '{print $1}')"
printf '%s  /tmp/not-the-bundle.tar.gz\n' "$VALID_DIGEST" > "$TEST_ROOT/redirected-sidecar.tar.gz.sha256"
provision_path_should_fail_with_reason redirected-sidecar "$TEST_ROOT/redirected-sidecar.tar.gz" m30-7-redirected-sidecar "bundle checksum sidecar filename is invalid"

printf 'malformed bundle\n' > "$TEST_ROOT/malformed.tar.gz"
write_outer_checksum "$TEST_ROOT/malformed.tar.gz"
expect_fail malformed-bundle "$SCRIPT" provision m30-7-malformed --bundle "$TEST_ROOT/malformed.tar.gz" --type test --port 19110
[[ ! -e "$PMQMS_CUSTOMER_INSTANCE_ROOT/m30-7-malformed" ]] || fail "malformed bundle left a persistent instance"

source "$SCRIPT"
runtime_verify_lock() { :; }
health() { return 0; }
compose() {
  case "$*" in
    *"ps -q odoo"*) echo odoo-id ;;
    *"ps -q postgres"*) echo postgres-id ;;
    *"odoo shell"*)
      cat >/dev/null
      printf '%s\n' \
        'customer_ready_application=pass' \
        'CUSTOMER_READY_PROBE_FIRST_USER=pass' \
        'CUSTOMER_READY_PROBE_LICENSE=pass' \
        'CUSTOMER_READY_QMS_SCOPE=pass' \
        'CUSTOMER_READY_QMS_ORGANIZATION=pass' \
        'CUSTOMER_READY_QMS_SITES=pass' \
        'CUSTOMER_READY_QMS_PROCESSES=pass'
      ;;
    *) return 0 ;;
  esac
}
docker() {
  case "$1" in
    inspect|image) echo image-id ;;
    *) return 0 ;;
  esac
}
ready_output="$(customer_ready "$VALID_SLUG" 2>&1)" || fail "exact customer-ready identity failed"
grep -Fxq 'CUSTOMER_READY_RELEASE_IDENTITY=pass' <<<"$ready_output" || fail "customer-ready did not prove release identity"
grep -Fxq 'CUSTOMER_READY_RUNTIME_IDENTITY=pass' <<<"$ready_output" || fail "customer-ready did not prove runtime identity"
grep -Fxq 'CUSTOMER_READY=YES' <<<"$ready_output" || fail "exact customer-ready identity was not accepted"

cp "$ROOT/config/instance.env" "$TEST_ROOT/instance.env.backup"
sed -i 's/^PRODUCT_VERSION=.*/PRODUCT_VERSION=v1.0.0-rc10/' "$ROOT/config/instance.env"
if customer_ready "$VALID_SLUG" >"$TEST_ROOT/release-mismatch.out" 2>&1; then
  fail "customer-ready accepted a release identity mismatch"
fi
grep -Fxq 'CUSTOMER_READY=NO' "$TEST_ROOT/release-mismatch.out" || fail "customer-ready mismatch did not report NO"
mv "$TEST_ROOT/instance.env.backup" "$ROOT/config/instance.env"

echo "customer release artifact tests: 25 PASS (A-O plus payload provenance and portable checksum binding)"
