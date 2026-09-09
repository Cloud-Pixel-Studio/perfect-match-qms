#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE="$REPO_ROOT/nginx/customer.conf.example"
DOC="$REPO_ROOT/../docs/M31_4_B2_PROXY_CONTRACT.md"

grep -Fq 'proxy_set_header X-Forwarded-For $remote_addr;' "$TEMPLATE"
grep -Fq 'proxy_set_header X-Real-IP $remote_addr;' "$TEMPLATE"
grep -Fq 'proxy_set_header X-Forwarded-Host $host;' "$TEMPLATE"
grep -Fq 'proxy_set_header X-Forwarded-Proto https;' "$TEMPLATE"
grep -Fq 'proxy_set_header X-Forwarded-Port 443;' "$TEMPLATE"
grep -Fq 'proxy_set_header Forwarded "";' "$TEMPLATE"

if grep -Fq '$proxy_add_x_forwarded_for' "$TEMPLATE"; then
  echo 'proxy template preserves an untrusted X-Forwarded-For chain' >&2
  exit 1
fi

grep -Fqi 'one trusted proxy hop' "$DOC"
grep -Fqi 'spoofed X-Forwarded-For' "$DOC"
grep -Fqi 'malformed forwarding value' "$DOC"
grep -Fqi 'multi-hop' "$DOC"
grep -Fqi 'PostgreSQL' "$DOC"
grep -Fqi 'VMware' "$DOC"
grep -Fqi 'Management Agent' "$DOC"

echo 'customer proxy contract validation: PASS'
