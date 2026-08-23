# Mission 19 Security Baseline Matrix

## Discovery baseline

| Area | Baseline before Mission 19 | Mission 19 decision |
| --- | --- | --- |
| Identity | QMS access was inherited from `QMS User`, `QMS Manager`, and `QMS Administrator`; Demo seed assigned Manager and Administrator to every persona. | Add explicit product roles backed by `res.groups`; Demo personas receive one intended role. |
| ACLs | Several QMS User ACLs allowed create/write on operational records. | Keep the base user read-oriented for high-risk records and grant operational write through approved role groups. |
| Record rules | Company boundaries were mostly group rules. | Add global organization/site/process scope rules. Global rules are ANDed with the existing company boundaries, avoiding group-rule OR fail-open behavior. |
| Workflow authority | Workflow methods commonly checked `QMS Manager`; state writes were already guarded in major modules. | Preserve model actions and separation-of-duty checks; no universal approval group is introduced. |
| Aggregators | Dashboard and Action Center use normal ORM searches; Action Center source opening calls `check_access('read')`. | Keep searches under the requesting user and retain source access checks. No sudo is used to broaden QMS results. |
| User identity | `pm.qms.person.user_id` links a person to an Odoo user. | Users & Access exposes the linked QMS Person and access scope; it does not create a second identity authority. |

## Explicit answers

1. QMS Manager and Administrator remain compatibility groups. Product roles are separate named groups and do not imply `base.group_system`.
2. Existing module groups and model ACLs remain the source of technical permissions. New role ACLs add the minimum operational capabilities needed by the named personas.
3. Workflow methods remain the authority for approval, closure, effectiveness, audit independence, document release, and calibration/OOT decisions.
4. Company rules remain global isolation boundaries; organization, site, and process rules are global scope boundaries.
5. Organization, site, process, person, equipment, and process-linked operational records participate in scope enforcement.
6. Empty organization or selected site/process scope fails closed. A user must be explicitly assigned an organization and a site/process scope.
7. Dashboard, Action Center, Cost of Quality, and source navigation continue to use ordinary ORM access checks.
8. `sudo()` remains limited to configuration/event plumbing already present; it is not used to build user-facing aggregates.
9. Menu visibility is convenience only. ACLs, record rules, and workflow methods enforce access server-side.
10. The existing `pm.qms.role` model remains competency/responsibility metadata; `res.groups` remains security authority.
11. Users & Access is a product view with an allow-list of roles and scope fields, not a technical ACL designer.
12. Demo seed is idempotent and updates only `pmqms_demo`; `pmqms_oliva_pilot` is not part of the Mission 19 path.
