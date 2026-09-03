# M30.5 Control Instance Authorization

M30.5 keeps control-instance creation fail-closed while allowing a Quality
Manager with `All Processes` enabled to use a process materialized by the
supported implementation generator in the same authorized organization.

The effective-process computation uses a fresh organization-scoped ORM search
for the all-processes case. Explicit process scope remains limited to selected
processes plus the existing selected-site expansion. Company and organization
boundaries, framework library separation, and the existing Mission 19 record
rules remain active.

The regression suite covers clean-customer generation, immediate read-after-
create, selected-process denial, empty scope, out-of-scope organizations,
cross-company processes, framework targets, and two idempotent framework syncs.
