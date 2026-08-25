# Branding Architecture

Mission 24 uses the approved Perfect Match assets already in `pm_qms_app`.
No new identity or color system is invented.

## Approved sources

- Product icon: `addons/pm_qms_app/static/description/icon.svg`
- Approved company mark: `addons/pm_qms_app/static/description/perfect_match_logo_master.png`
- Login and backend styling: `addons/pm_qms_app/static/src/scss/brand.scss`
- Supported identity templates: `addons/pm_qms_app/views/shell_templates.xml`

## Token layer

`brand.scss` exposes reusable CSS custom properties for primary navy, navy
navigation background, magenta active state, yellow focus, green accent,
surfaces, borders, text, and muted text. Semantic success, warning, and danger
colors remain owned by Odoo and the relevant QMS views.

The customer shell uses navy and magenta states with high-contrast text. Hover,
active, dropdown, and focus-visible states are explicit. Technical Odoo screens
are not globally recolored.

## Scope

- Login includes the approved Perfect Match company mark and product identity.
- The backend brand includes the approved product icon in the application brand.
- Customer navigation uses Perfect Match colors rather than default Odoo purple
  as the dominant treatment.
- Odoo and third-party legal notices and attribution remain intact.
- Technical Administrator surfaces remain maintainable and are not cosmetically
  hidden by broad webclient patches.

## User menu and communication

Account, preference, logout, accessibility, and security functions remain
available where supplied by Odoo. They are not treated as QMS authorization.
The generic `My Odoo.com Account` entry is suppressed for non-technical QMS
users through the supported `user_menuitems` registry and remains available to
system administrators.
The generic Discuss root is restricted for customer QMS roles while mail
infrastructure, chatter, activities, notifications, and `mail.thread` remain.
