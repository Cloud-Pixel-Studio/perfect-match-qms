# Perfect Match QMS v1.0.0-rc6

## Organization, Site And Secure Access Release Candidate

RC6 is the release candidate for the standalone Perfect Match Digital QMS
product surface.

### Included

- Standalone organization and company profile foundation.
- Site model and the three fictional Apex Demo sites.
- Process/site and equipment/site relationships with cross-company guards.
- Role, site scope, workflow authority, record security, and segregation
  controls from Mission 19.
- Action Center and Cost of Quality customer-facing routes.
- DEV as engineering validation and Demo as the only public validation
  environment.
- Final retirement of the Oliva Torras pilot runtime after a validated local
  backup. Historical documentation and Plane traceability remain preserved.

### Boundaries

- Odoo remains the application platform and Plane remains the work-management
  system of record through supported APIs.
- Commercial licensing, subscription limits, and entitlement enforcement are
  not implemented in RC6.
- RC6 does not start Mission 20.
- No certification, external compliance, or customer production approval claim
  is made.
- No backup, database dump, filestore, secret, or private credential is part of
  GitHub or the release assets.

### Validation

The release gate covers static checks, standalone dependency review, clean
install/update, focused and full Odoo tests, DEV health, Demo health and
validation, authenticated Demo visual checks, and the absence of the retired
Oliva runtime resources.
