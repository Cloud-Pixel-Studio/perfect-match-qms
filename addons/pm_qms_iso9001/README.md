# Perfect Match QMS ISO 9001 Add-on

This add-on owns the ISO 9001 profile boundary for Perfect Match QMS. It
depends on the standard-neutral `pm_qms_pack_quality` methodology pack and
does not make the generic QMS foundation depend on ISO 9001.

It creates or adopts the stable `PM-QMS-QUALITY-ISO9001` / `2015` profile,
exposes the customer read-only **Standards > ISO 9001** view, and leaves
reference mapping approval to an authorized human reviewer. No requirement
text or copied standard guidance is included, and no approved mappings are
seeded.

## Initial implementation foundation

The add-on also owns the versioned PM-QMS-ISO9001-INITIAL / 1.0
implementation pack. Its 13 framework areas and reused generic control lines are
loaded idempotently from content/initial_implementation_v1.json. The tracked
blueprint contains reviewed Perfect Match metadata only; deep guided content is
planned for later Mission 25 authoring checkpoints.

The existing PM-QMS-QUALITY-ISO9001 / 2015 mapping profile remains a
separate external-reference boundary and continues to use the generic quality
pack.
