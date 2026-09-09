#!/usr/bin/env bash
set -euo pipefail

# Disposable client -> trusted Nginx -> Odoo 19 certification.  Everything is
# created under a temporary Docker network and removed by the EXIT trap.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOCK_FILE="$REPO_ROOT/runtime/runtime-lock.json"
WORK="$(mktemp -d)"
NETWORK="pmqms-proxy-runtime-${RANDOM}-${RANDOM}"
POSTGRES="pmqms-proxy-postgres-${RANDOM}"
ODOO="pmqms-proxy-odoo-${RANDOM}"
NGINX="pmqms-proxy-nginx-${RANDOM}"
CLIENT="pmqms-proxy-client-${RANDOM}"
DIRECT="pmqms-proxy-direct-${RANDOM}"

ODOO_IMAGE="$(jq -er '.odoo.image' "$LOCK_FILE")"
POSTGRES_IMAGE="$(jq -er '.postgres.image' "$LOCK_FILE")"
ALPINE_IMAGE="$(jq -er '.alpine.image' "$LOCK_FILE")"
NGINX_IMAGE="${PMQMS_NGINX_IMAGE:-nginx:1.27-alpine}"
DB_NAME="pmqms_proxy_runtime"

cleanup() {
  set +e
  docker rm -f "$CLIENT" "$DIRECT" "$NGINX" "$ODOO" "$POSTGRES" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf -- "$WORK"
}
trap cleanup EXIT

fail_with_logs() {
  echo "disposable proxy runtime test: FAIL" >&2
  docker logs "$NGINX" 2>&1 | tail -80 >&2 || true
  docker logs "$ODOO" 2>&1 | tail -80 >&2 || true
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required command is unavailable: $1" >&2
    exit 2
  }
}

for command in docker jq; do require_command "$command"; done
docker info >/dev/null 2>&1 || { echo 'Docker daemon is unavailable' >&2; exit 2; }

mkdir -p "$WORK/probe-addons/pmqms_proxy_probe/controllers" "$WORK/nginx"
cat > "$WORK/probe-addons/pmqms_proxy_probe/__manifest__.py" <<'PY'
{
    "name": "Disposable Proxy Runtime Probe",
    "version": "19.0.1.0.0",
    "depends": ["base"],
    "installable": True,
    "application": False,
}
PY
cat > "$WORK/probe-addons/pmqms_proxy_probe/__init__.py" <<'PY'
from . import controllers
PY
cat > "$WORK/probe-addons/pmqms_proxy_probe/controllers/__init__.py" <<'PY'
from . import main
PY
cat > "$WORK/probe-addons/pmqms_proxy_probe/controllers/main.py" <<'PY'
import json

from odoo.http import Controller, Response, request, route


class ProxyRuntimeProbe(Controller):
    @route("/__pmqms_probe/remote_addr", auth="none", csrf=False, methods=["GET"])
    def remote_addr(self):
        return Response(
            json.dumps({
                "remote_addr": request.httprequest.remote_addr,
                "forwarded_for": request.httprequest.headers.get("X-Forwarded-For", ""),
            }),
            content_type="application/json",
        )
PY
cat > "$WORK/odoo.conf" <<EOF
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/probe-addons
data_dir = /var/lib/odoo
admin_passwd = $(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
db_host = postgres
db_port = 5432
db_user = odoo
db_name = $DB_NAME
dbfilter = ^$DB_NAME\$
list_db = False
proxy_mode = True
workers = 0
max_cron_threads = 0
EOF
cat > "$WORK/nginx/default.conf" <<'NGINX'
server {
    listen 80;
    location / {
        proxy_pass http://odoo:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto http;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Port 80;
        proxy_set_header Forwarded "";
    }
}
NGINX

docker network create "$NETWORK" >/dev/null
docker run -d --name "$POSTGRES" --network "$NETWORK" \
  -e POSTGRES_DB=postgres -e POSTGRES_USER=odoo \
  -e POSTGRES_HOST_AUTH_METHOD=trust "$POSTGRES_IMAGE" >/dev/null

for _ in {1..60}; do
  if docker exec "$POSTGRES" pg_isready -U odoo -d postgres >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$POSTGRES" pg_isready -U odoo -d postgres >/dev/null 2>&1 || fail_with_logs
docker exec "$POSTGRES" createdb -U odoo "$DB_NAME"

docker run -d --name "$ODOO" --network "$NETWORK" \
  -v "$WORK/probe-addons:/mnt/probe-addons:ro" \
  -v "$WORK/odoo.conf:/etc/odoo/odoo.conf:ro" \
  "$ODOO_IMAGE" odoo -c /etc/odoo/odoo.conf -d "$DB_NAME" \
  --init pmqms_proxy_probe --without-demo=all --stop-after-init >/dev/null
for _ in {1..90}; do
  status="$(docker inspect -f '{{.State.Status}}' "$ODOO" 2>/dev/null || true)"
  [[ "$status" == exited || "$status" == dead ]] && break
  sleep 1
done
[[ "$(docker inspect -f '{{.State.ExitCode}}' "$ODOO")" == 0 ]] || fail_with_logs

docker rm "$ODOO" >/dev/null
docker run -d --name "$ODOO" --network "$NETWORK" \
  -v "$WORK/probe-addons:/mnt/probe-addons:ro" \
  -v "$WORK/odoo.conf:/etc/odoo/odoo.conf:ro" \
  "$ODOO_IMAGE" odoo -c /etc/odoo/odoo.conf >/dev/null
docker run -d --name "$NGINX" --network "$NETWORK" \
  -v "$WORK/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" \
  "$NGINX_IMAGE" >/dev/null
docker run -d --name "$CLIENT" --network "$NETWORK" "$ALPINE_IMAGE" sleep 300
docker run -d --name "$DIRECT" --network "$NETWORK" "$ALPINE_IMAGE" sleep 300

http_get() {
  local target="$1" header="${2:-}"
  if [[ -n "$header" ]]; then
    docker exec "$CLIENT" wget -qO- --header="$header" "$target"
  else
    docker exec "$CLIENT" wget -qO- "$target"
  fi
}
wait_for_http() {
  for _ in {1..90}; do
    if http_get 'http://nginx/__pmqms_probe/remote_addr' >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  fail_with_logs
}
probe_remote() {
  local response
  response="$1"
  printf '%s\n' "$response" | sed -n 's/.*"remote_addr": *"\([^"]*\)".*/\1/p'
}

wait_for_http
CLIENT_IP="$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$CLIENT")"
DIRECT_IP="$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$DIRECT")"
NGINX_IP="$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$NGINX")"

normal="$(http_get 'http://nginx/__pmqms_probe/remote_addr')"
normal_ip="$(probe_remote "$normal")"
[[ "$normal_ip" == "$CLIENT_IP" ]] || fail_with_logs

spoofed="$(http_get 'http://nginx/__pmqms_probe/remote_addr' 'X-Forwarded-For: 198.51.100.77')"
spoofed_ip="$(probe_remote "$spoofed")"
[[ "$spoofed_ip" == "$CLIENT_IP" && "$spoofed_ip" != 198.51.100.77 ]] || fail_with_logs

malformed="$(http_get 'http://nginx/__pmqms_probe/remote_addr' 'X-Forwarded-For: not-an-ip')"
malformed_ip="$(probe_remote "$malformed")"
[[ "$malformed_ip" == "$CLIENT_IP" && "$malformed_ip" != not-an-ip ]] || fail_with_logs

missing="$(http_get 'http://nginx/__pmqms_probe/remote_addr')"
missing_ip="$(probe_remote "$missing")"
[[ "$missing_ip" == "$CLIENT_IP" ]] || fail_with_logs

direct="$(docker exec "$DIRECT" wget -qO- 'http://odoo:8069/__pmqms_probe/remote_addr')"
direct_ip="$(probe_remote "$direct")"
[[ "$direct_ip" == "$DIRECT_IP" && "$direct_ip" != "$CLIENT_IP" ]] || fail_with_logs

multihop="$(http_get 'http://nginx/__pmqms_probe/remote_addr' 'X-Forwarded-For: 198.51.100.77, 203.0.113.44')"
multihop_ip="$(probe_remote "$multihop")"
[[ "$multihop_ip" == "$CLIENT_IP" && "$multihop_ip" != 198.51.100.77 && "$multihop_ip" != 203.0.113.44 ]] || fail_with_logs

[[ "$normal_ip" != "$NGINX_IP" ]] || fail_with_logs
echo 'disposable proxy runtime test: PASS'
echo 'normal_proxy_ip=client_container'
echo 'spoofed_xff=rejected'
echo 'malformed_xff=replaced'
echo 'missing_xff=constructed'
echo 'direct_odoo_peer=distinct_direct_container'
echo 'unexpected_multihop=not_accepted_as_forwarded_identity'
