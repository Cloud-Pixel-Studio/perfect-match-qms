# QMS Activity & History

Perfect Match QMS presents native Odoo record history as a focused customer
experience for authorized `pm.qms.*` records.

## Includes

- human-authored field changes with old and new values;
- Internal Notes;
- scheduled Activities and reminders;
- business events and supported attachments;
- existing notification behavior.

The customer label for the feature is **QMS Activity & History**. Real human
authors remain real human authors. The verified native system actor may be
presented as **Perfect Match QMS · System** in the customer shell without
changing stored message authors.

## Boundaries

The feature uses Odoo's native mail and tracking infrastructure. It is not a
replacement audit log and it does not provide a general-purpose customer chat
surface. Normal customer QMS users do not receive the general Send Message
entry point or manual follower-management controls by default. Internal Notes,
Activities, attachments, and required notifications remain available according
to the user's existing record permissions.

Technical Administrators retain native diagnostics. Published history is
protected from ordinary customer rewriting or deletion; corrections should be
recorded as a new Internal Note.

The frontend presentation is scoped to authorized Perfect Match QMS records.
Unrelated Odoo mail-enabled records retain their native behavior.

For the pinned Odoo 19 runtime, the native `mail.Chatter` template renders the
Send Message and Followers entry points without native `t-if` conditions. This
addon therefore adds a PM customer-history predicate only to those controls;
Odoo's native disabled and permission logic remains authoritative, and all
non-PM chatter behavior remains unchanged. This scope does not disable
`mail.activity`, record chatter, tracking, or required notifications.
