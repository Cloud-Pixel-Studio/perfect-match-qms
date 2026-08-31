# Perfect Match QMS ISO 9001 Add-on

This add-on owns the ISO 9001 profile boundary for Perfect Match QMS. It
depends on the standard-neutral `pm_qms_pack_quality` methodology pack and
does not make the generic QMS foundation depend on ISO 9001.

It creates or adopts the stable `PM-QMS-QUALITY-ISO9001` / `2015` profile,
exposes the customer read-only **Standards > ISO 9001** view, and leaves
reference mapping approval to an authorized human reviewer. The profile name
identifies the ISO 9001:2015 and Amendment 1:2024 scope without reproducing
external requirement text.

## Initial implementation foundation

The add-on owns two selectable versions of the PM-QMS-ISO9001-INITIAL
implementation pack. Version 1.0 is the historical initial implementation
pack and remains active and unchanged. Version 1.1 is the Amendment 1:2024
aligned pack; both contain 13 phases and 37 generic control lines. The v1.1
pack reuses 30 activity definitions and adds seven focused revised definitions
for M25.11. It reuses the same 37 generic evidence definitions. Existing
implementation projects are not migrated automatically.

The v1.0 blueprint and authored content remain historical product content.
The v1.1 blueprint, seven-activity overlay, and evidence crosswalk contain
Perfect Match-authored metadata only; no external requirement text is included.

The existing PM-QMS-QUALITY-ISO9001 / 2015 mapping profile remains a
separate external-reference boundary and continues to use the generic quality
pack.
