from odoo import SUPERUSER_ID, api

from odoo.addons.pm_qms_iso9001.hooks import seed_iso9001_2026_implementation_pack


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    seed_iso9001_2026_implementation_pack(env)
