# Customer User Experience

## First entry

The customer lands in the Perfect Match QMS application and its Dashboard.
The login surface, favicon, application tile, page identity, and backend root
use the Perfect Match QMS identity. The shell keeps the main QMS workflows
close to the product root instead of exposing generic ERP navigation.

## Configuration path

Quality Managers use **Perfect Match QMS > Configuration** for Company Profile,
Sites, Processes, Users & Access, and Commercial License. They do not need
generic Odoo Settings, Apps, database management, or technical developer
menus for ordinary QMS administration.

## Role expectations

The Demo includes Quality Manager, Quality Supervisor, Document Controller,
Internal Auditor, Process Owner, Management User, and QMS Viewer personas.
Roles define capabilities; organization, Site, and Process scope define where
the user may work. Direct URLs and RPC requests are still evaluated by the
same Odoo security rules.

## Visual acceptance

Validate the shell at desktop and narrow widths for login, dashboard, root
navigation, Configuration, Action Center, Cost Analytics for permitted
management roles, source links, denied technical routes, and major existing
QMS menus. Cost Analytics is intentionally outside the QMS Viewer persona's
surface because it contains sensitive quality-cost amounts. Confirm no
horizontal overflow, broken assets, visible traceback, or browser-console
error is introduced by the shell assets.
