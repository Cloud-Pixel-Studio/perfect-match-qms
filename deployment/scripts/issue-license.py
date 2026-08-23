#!/usr/bin/env python3
"""Issue a signed offline Perfect Match license using an external private key."""

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from odoo.addons.pm_qms_license.services.license_service import issue_license  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-key", required=True, help="External PEM Ed25519 private key path")
    parser.add_argument("--output", required=True, help="Output .pmql path")
    parser.add_argument("--environment-id", required=True)
    parser.add_argument("--customer-name", required=True)
    parser.add_argument("--edition", default="professional")
    parser.add_argument("--license-id", default=None)
    parser.add_argument("--revision", type=int, default=1)
    parser.add_argument("--company-limit", type=int, default=1)
    parser.add_argument("--site-limit", type=int, default=3)
    parser.add_argument("--named-user-limit", type=int, default=1)
    parser.add_argument("--key-id", default="pmqms-demo-2026")
    parser.add_argument("--expires-at", default=None, help="ISO-8601 UTC timestamp; omit for perpetual license")
    return parser.parse_args()


def main():
    args = parse_args()
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": 1,
        "license_id": args.license_id or f"PMQMS-{uuid.uuid4().hex[:12].upper()}",
        "license_revision": args.revision,
        "customer_name": args.customer_name,
        "edition": args.edition,
        "environment_id": args.environment_id,
        "company_limit": args.company_limit,
        "site_limit": args.site_limit,
        "named_user_limit": args.named_user_limit,
        "issued_at": now,
        "not_before": now,
        "expires_at": args.expires_at,
        "perpetual": args.expires_at is None,
        "key_id": args.key_id,
        "metadata": {"issuer": "Perfect Match Investments LLC", "purpose": "offline entitlement"},
    }
    document = issue_license(payload, args.private_key, args.output)
    print(json.dumps({"license_id": payload["license_id"], "revision": payload["license_revision"], "output": str(Path(args.output).resolve())}, sort_keys=True))
    return document


if __name__ == "__main__":
    main()
