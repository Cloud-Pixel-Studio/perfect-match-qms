#!/usr/bin/env bash
set -euo pipefail

# Integration proof uses the official upstream release in a disposable workspace.
AGE_VERSION="1.2.1"
AGE_SHA256="7df45a6cc87d4da11cc03a539a7470c15b1041ab2b396af088fe9990f7c79d50"
AGE_URL="https://github.com/FiloSottile/age/releases/download/v${AGE_VERSION}/age-v${AGE_VERSION}-linux-amd64.tar.gz"
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
umask 077

curl --fail --silent --show-error --location "$AGE_URL" -o "$WORK/age.tar.gz"
printf '%s  %s\n' "$AGE_SHA256" "$WORK/age.tar.gz" | sha256sum --check --status
tar -xzf "$WORK/age.tar.gz" -C "$WORK"
AGE_BIN="$(find "$WORK" -type f -name age -perm -u+x -print -quit)"
AGE_KEYGEN="$(find "$WORK" -type f -name age-keygen -perm -u+x -print -quit)"
[[ -x "$AGE_BIN" && -x "$AGE_KEYGEN" ]]

"$AGE_KEYGEN" > "$WORK/identity.age" 2>/dev/null
chmod 600 "$WORK/identity.age"
RECIPIENT="$(sed -n -e 's/^# public key: //p' -e 's/^Public key: //p' "$WORK/identity.age")"
[[ "$RECIPIENT" =~ ^age1[[:alnum:]]+$ ]]
printf '%s\n' "$RECIPIENT" > "$WORK/recipient.age"

printf 'fictional database\n' > "$WORK/db.dump"
mkdir -p "$WORK/filestore/fictional-db"
printf 'fictional attachment\n' > "$WORK/filestore/fictional-db/attachment.txt"
tar -czf "$WORK/filestore.tar.gz" -C "$WORK" filestore/fictional-db
printf 'fictional-environment-id\n' > "$WORK/environment_id"
printf '{\"schema_version\":1}\n' > "$WORK/runtime-lock.json"
printf '{\"instance_slug\":\"fictional-dr\"}\n' > "$WORK/deployment-manifest.json"
ARCHIVE="$WORK/fictional-dr-20260902T000000Z.tar.age"

export PMQMS_AGE_BIN="$AGE_BIN"
export PMQMS_AGE_VERSION="$AGE_VERSION"
python3 tools/backup/m29_backup.py pack \
  --output "$ARCHIVE" \
  --recipient-file "$WORK/recipient.age" \
  --source-instance fictional-dr \
  --source-database fictional-db \
  --source-environment-id fictional-environment-id \
  --product-version v1.0.0-test \
  --source-release-sha "$(printf 'a%.0s' {1..40})" \
  --recovery-point-class daily \
  --created-utc 2026-09-02T00:00:00Z \
  --component "db.dump=$WORK/db.dump" \
  --component "filestore.tar.gz=$WORK/filestore.tar.gz" \
  --component "environment_id=$WORK/environment_id" \
  --component "runtime-lock.json=$WORK/runtime-lock.json" \
  --component "deployment-manifest.json=$WORK/deployment-manifest.json"
python3 tools/backup/m29_backup.py verify --archive "$ARCHIVE" --identity-file "$WORK/identity.age" --expected-instance fictional-dr --expected-database fictional-db
python3 tools/backup/m29_backup.py unpack --archive "$ARCHIVE" --identity-file "$WORK/identity.age" --expected-instance fictional-dr --expected-database fictional-db --output "$WORK/unpacked"
cmp "$WORK/db.dump" "$WORK/unpacked/db.dump"
mkdir "$WORK/off-host"
python3 tools/backup/m29_backup.py transfer --archive "$ARCHIVE" --destination "$WORK/off-host"
python3 tools/backup/m29_backup.py transfer --archive "$ARCHIVE" --destination "$WORK/off-host" | grep -F '"idempotent": true' >/dev/null
mkdir "$WORK/retention"
touch "$WORK/retention/.pmqms-recovery-repository"
cp "$ARCHIVE" "$WORK/retention/"
cp "$ARCHIVE.manifest.json" "$WORK/retention/"
cp "$ARCHIVE.sha256" "$WORK/retention/"
python3 tools/backup/m29_backup.py retention --directory "$WORK/retention" --now 2026-09-02T00:00:00Z >/dev/null
echo "m29_real_age_integration=pass"
