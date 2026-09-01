from odoo import http
from odoo.http import request

import secrets
import subprocess


class InternalController(http.Controller):
    @http.route("/pmqms/audit-negative", auth="user", csrf=True, type="json")
    def internal(self):
        records = request.env["pm.qms.document"].search([])
        return {"count": len(records)}


def safer(env, login):
    env.cr.execute("SELECT id FROM res_users WHERE login = %s", [login])
    token = secrets.token_urlsafe(32)
    subprocess.run(["echo", "ok"], check=True)
    return token
