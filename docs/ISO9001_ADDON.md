# ISO 9001 Add-on

The technical add-on is `pm_qms_iso9001`. It depends on
`pm_qms_pack_quality`, which supplies the proprietary PM-QMS-QUALITY
methodology pack. The generic QMS foundation does not depend on ISO 9001.

The add-on provides one active profile: **ISO 9001**, edition **2015**,
publisher **ISO**, with stable code `PM-QMS-QUALITY-ISO9001`. The profile is
created or adopted idempotently during installation. No approved external
mappings are seeded; a customer may import reference identifiers through the
administrator workflow and approve them after human review.

Customer users see **Perfect Match QMS > Standards > ISO 9001 > Overview**.
The view is read-only and reports profile state, coverage counts, and reviewed
reference identifiers. It never displays copied standard requirements or
unapproved guidance.

The add-on deliberately does not implement ISO 14001, ISO 45001, AS9100,
AS9120, IATF 16949, standard-specific billing, or a standards comparison
dashboard. Future standards belong in separate add-ons.
