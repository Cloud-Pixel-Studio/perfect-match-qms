from odoo import Command


# Optional ERP apps may be present in a Demo or an existing Odoo database, but
# they are not dependencies of the customer QMS bundle. Restrict their root
# menus when their XML IDs exist without forcing those apps into the bundle.
OPTIONAL_PLATFORM_MENU_XMLIDS = (
    "project_todo.menu_todo_todos",
)


def restrict_optional_platform_menus(env):
    technical_admin = env.ref("base.group_system")
    for xmlid in OPTIONAL_PLATFORM_MENU_XMLIDS:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.write({"group_ids": [Command.set([technical_admin.id])]})


def post_init_hook(env):
    restrict_optional_platform_menus(env)
