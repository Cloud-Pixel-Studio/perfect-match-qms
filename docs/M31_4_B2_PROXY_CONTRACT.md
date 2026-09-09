# M31.4-B2.1 Proxy and Client-IP Contract

This document defines the deployment-neutral contract for a customer QMS
instance. It is valid for a Linux VM, bare-metal host, VPS, public or private
cloud VM, or customer datacenter. The hypervisor and hosting provider do not
change the application contract.

Supported hosting examples include VMware, Proxmox, Hyper-V, public cloud VMs,
private cloud VMs, VPS deployments, Linux bare metal, and customer datacenters.

## Supported topology

The supported single-proxy topology is:

```text
Customer LAN or Internet
        -> TLS reverse proxy or approved load balancer
        -> private application network
        -> Perfect Match QMS / Odoo:8069
        -> PostgreSQL local or private-remote
```

The customer Odoo service binds to a loopback or private interface. PostgreSQL
is never public. TLS terminates at the approved reverse proxy or upstream load
balancer. The application uses `proxy_mode = True` and Odoo trusts one trusted proxy hop
in the documented Nginx topology.

The example Nginx configuration is a trust boundary. It sets
`X-Forwarded-For` and `X-Real-IP` from the address Nginx observes on the proxy
connection, clears `Forwarded`, and does not append a client-provided
`X-Forwarded-For` chain. Host, HTTPS scheme, and port are set explicitly.

## Client-IP behavior

Odoo 19 obtains the request address from `request.httprequest.remote_addr`.
Session/device traces use that value. With `proxy_mode` enabled, Odoo's
`odoo.http.Application.__call__` applies Werkzeug `ProxyFix` for one `X-Forwarded-For`,
one `X-Forwarded-Proto`, and one `X-Forwarded-Host` value. Odoo does not use
`X-Real-IP` or the RFC `Forwarded` header for this resolution.

| Case | Boundary behavior | Expected application-recorded IP |
| --- | --- | --- |
| Normal request through one trusted proxy | Proxy replaces inbound forwarding headers | Verified client address observed by proxy |
| Client-supplied spoofed X-Forwarded-For | Incoming chain is discarded | Spoofed value is not recorded |
| Missing forwarding header | No proxy-derived address is available | Immediate socket peer |
| Malformed forwarding value | Proxy must replace it; Odoo itself does not validate IP syntax | Proxy-observed address; direct malformed headers are not trusted |
| Direct Odoo access | Bypasses the proxy boundary | Internal/container/bridge peer may appear |
| Unexpected additional proxy hop | One-hop trust selects only the configured trusted hop | Not certified until every hop is controlled and the count is explicit |

Direct Odoo access is an operational diagnostic path, not a production access
path. A 172.x Docker bridge address in that mode is expected platform behavior,
not a product defect. Device and session IPs should be reliable after traffic
uses the sanitized proxy path; no product-side rewriting is required.

## Multi-proxy and provider requirements

For a load balancer or enterprise proxy in front of Nginx, every forwarding
boundary must discard untrusted inbound values and construct the next trusted
chain. The operator must document the exact proxy count and the private source
network of each trusted hop. Odoo's one-hop setting must not be reused for a
multi-hop path without review. An upstream provider-specific adapter may
implement that boundary without changing this application contract.

## Domain and TLS contract

An installation may be bootstrapped on a controlled private address, but a
normal customer handoff requires an approved FQDN. Public, private, and
split-horizon DNS are supported conceptually. The FQDN must resolve to the
approved proxy, the certificate hostname must match it, and the validated
application base URL must use the canonical HTTPS hostname. Hostname changes
require an explicit configuration validation and certificate/DNS review.

## Exposure and firewall contract

Only the proxy's 80/443 endpoints may be exposed to the customer network or
Internet. Odoo HTTP/longpolling, PostgreSQL, management sockets, Docker APIs,
and secret stores remain private. A firewall must block direct external access
to Odoo and PostgreSQL. Health checks must not weaken authentication or expose
database management endpoints.

## Database and operational boundaries

Local PostgreSQL is supported by the current customer Compose shape. Private
remote and compatible managed PostgreSQL are possible deployment modes, but
require separate certification for TLS, authentication/`pg_hba` equivalent,
latency, connection limits/pooling, required extensions, backup ownership,
restore workflow, filestore synchronization, DNS, and failover behavior.

Backup destinations may be local, private-remote, or supported object storage;
the same backup, encryption, freshness, and restore-validation contract applies.
SMTP and storage health are diagnostics, not permission to expose their
credentials.

## Future administration boundary

The browser may display release/version, deployment mode, environment identity,
base URL, DNS/TLS/proxy health, database connectivity, backup freshness and
restore validation, storage health, and SMTP health. It must not receive host,
root, Docker, private-key, or plaintext database credentials.

A future bounded Perfect Match Management Agent is recommended as a hybrid
boundary for allowlisted diagnostics, connectivity checks, backup operations,
restore validation, update readiness, and approved service actions. It must be
a least-privileged service with strict schemas, timeouts, audit logs, rate
limits, fail-closed behavior, no arbitrary shell, no unrestricted Docker socket,
and no plaintext secret readback. External/manual infrastructure management
remains supported for provider-specific DNS, certificates, firewalls, and
managed databases. The agent is not implemented by M31.4-B2.1.

## Validation status

The repository-level contract is statically validated by
`deployment/scripts/tests/test_customer_proxy_contract.sh`. A disposable
client-to-Nginx-to-Odoo runtime test remains required when Docker and Nginx are
available. No production, Demo, customer, or CleanVM runtime was changed by
this corrective.
