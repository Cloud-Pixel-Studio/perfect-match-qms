# M28 Authorization and Isolation Matrix

This matrix is the review contract for M28. `M28` runtime tests use fictional
DEV records only. `A` is a user scoped to organization A; `B` is a same-company
sibling organization. Technical administrator and licensing administrator
rows preserve their existing role boundaries.

| Model or surface | Persona | Operation | Expected | Observed evidence | Test method |
| --- | --- | --- | --- | --- | --- |
| `pm.qms.management.review.input` | Quality Manager A | search, read, name_search, read_group | A visible; B absent/denied | PASS | `TestM28Reproduction.test_same_company_child_record_isolated_for_all_record_access` |
| `pm.qms.management.review.input` | Quality Manager A | create | A parent allowed; B parent denied | PASS | same test, ORM create |
| `pm.qms.management.review.input` | Quality Manager A | write, unlink | B denied | PASS | same test, direct record operations |
| `pm.qms.capa.*` child records | scoped QMS user | read, create, write, unlink | organization scope required | Rule coverage present; representative runtime pending | `test_m28_child_scope_rules_cover_required_record_families` |
| `pm.qms.management.review.{decision,action}` | scoped QMS user | read, create, write, unlink | organization scope required | Rule coverage present; representative runtime pending | rule inventory plus parent-derived organization field |
| `pm.qms.audit.{scope,criterion,plan.line,evidence,finding}` | scoped QMS user | read, create, write, unlink | organization and optional process scope | Rule coverage present; representative runtime pending | rule inventory and process domain |
| `pm.qms.calibration.{measurement.line,impact.assessment,affected.reference}` | scoped QMS user | read, create, write, unlink | organization scope required | Rule coverage present; representative runtime pending | rule inventory and equipment-derived organization |
| `pm.qms.person.role.assignment` and competency records | scoped QMS user | read, create, write, unlink | person organization scope required | Rule coverage present; representative runtime pending | rule inventory and person-derived organization |
| training and qualification records | scoped QMS user | read, create, write, unlink, autocomplete | organization scope required | Rule coverage present; representative runtime pending | rule inventory and related-person scope |
| `pm.qms.event` | scoped QMS user | read, create, write, unlink | company and organization scope required | Rule coverage present | `test_m28_child_scope_rules_cover_required_record_families` |
| `mail.message` linked to a QMS child | Quality Manager A | native read | A message readable; B message denied | PASS | `test_native_mail_and_attachment_routes_follow_child_scope` |
| `ir.attachment` linked to a QMS child | Quality Manager A | native read | A attachment readable; B attachment denied | PASS | same test, native ORM access |
| `mail.activity` linked to a QMS child | Quality Manager A | search, read, write, unlink | assignment does not bypass QMS document scope | PASS | same test plus `pm_qms_app.models.mail_activity` |
| `mail.activity` linked to a non-QMS model | any existing persona | native mail activity behavior | unchanged | Preserved by `pm.qms.*`-only branch | code scope review |
| current commercial license | any customer persona | status/readiness | effective temporal state is authoritative | PASS | `test_license_temporal_boundaries_*` |
| operational organization, site, named user | customer activation workflow | create/reactivate | valid or expiring term and capacity required | PASS for expired hooks | `test_expired_license_blocks_all_new_capacity_hooks` |
| framework administration | QMS customer persona | read/write/create | existing administrator boundary preserved | PASS in M27; no M28 group change | M27 security regression reused |
| customer-style instance A vs B | operator | database, filestore, network, identity, secrets, license | unique per instance; no cross-use | Deployment template contract; disposable config inspection | customer deployment compose/config review |
| license A in environment B | operator/runtime | activation/use | wrong environment unusable | Existing license validation contract; no M28 bypass | license validation tests |

## Operation semantics

For scoped QMS models, `search`, `name_search`, and `read_group` must not
surface sibling-organization records. Direct `read`, `write`, `unlink`, and
workflow actions must reject them. `create` must validate the resulting
organization and process scope, including a parent record supplied by an
autocomplete or RPC request. A model without an explicit M28 child rule keeps
its existing rule and is not represented as newly certified by this matrix.

## Mail and endpoint boundary

Odoo's native `mail.message` and `ir.attachment` checks resolve access through
the related document. M28 extends only QMS-linked `mail.activity` records so
an assigned activity cannot become a side channel. No arbitrary HTTP controller
is certified by this ORM matrix; any such endpoint requires its own authenticated
route test.
