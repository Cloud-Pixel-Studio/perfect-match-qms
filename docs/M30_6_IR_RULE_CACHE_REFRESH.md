# M30.6 ir.rule Cache Refresh

M30.5 correctly refreshes `qms_effective_process_ids` after the implementation
generator creates a customer operational process. Odoo 19 also caches the
`ir.rule._compute_domain` result with `tools.ormcache` in the registry's
`default` cache. That cache is keyed by user, model, mode and allowed
companies; it does not depend on the computed process-scope field.

M30.6 calls the supported `env.registry.clear_cache("default")` API immediately
after a new operational process is successfully materialized, following the
existing user-field invalidation. The call is skipped when an existing process
is reused or a concurrent create resolves to an existing process. This keeps
the correction at the authorization-input change and avoids changing ACLs,
record-rule domains, company isolation, organization isolation or `sudo()`
behavior.

The regression covers both the deliberate stale-domain ordering and the normal
Quality Manager wizard generation from zero operational processes. The fixture
is fictional and transaction-scoped; it does not modify CleanVM or customer
data.
