# Commercial Entitlements

Commercial entitlements answer what capacity a customer has purchased. They
are independent from user authority and scope.

| Entitlement | Standard base | Counted usage |
| --- | ---: | --- |
| Operational company environment | 1 | Active operational `pm.qms.organization` records |
| Sites | 3 | Active Sites under the operational organization |
| Named QMS users | 1 | Active internal non-share users with a QMS role |

Framework/library organizations are excluded from company capacity. A second
operational customer company is not a supported way to consume `company_limit`
inside one normal environment; provision another isolated environment instead.

Archived Sites and archived users release capacity. A user with several QMS
roles consumes one seat. Technical, support, share-only, and approved exempt
accounts are excluded, but changing an exemption or account classification is
restricted to the licensing administrator or technical superuser and records a
reason. Normal QMS managers cannot exempt themselves.

When capacity is full, server-side create/reactivate/role activation fails with
a customer-safe message. Existing records, attachments, exports, backups, and
read access are not held hostage by license state. Mission 20 does not attempt
to apply a global expiry write lock; capacity enforcement is the defined
boundary for this release.

License revisions are monotonic per license ID. Importing a newer signed
revision updates limits; older or equal revisions are rejected. Replacement is
atomic and the previous license remains in history for authorized users.

Mission 23 does not add standard-feature licensing. The current capacity
entitlements remain environment, operational company, Sites, and named QMS
users. A future commercial decision may entitle an installed standard add-on,
but that decision must be represented in the signed license contract and
enforced separately from user roles; no such entitlement exists in this
release.
