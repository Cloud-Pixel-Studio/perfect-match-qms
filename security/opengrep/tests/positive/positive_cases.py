from odoo import SUPERUSER_ID, http
from odoo.http import request

import os
import pickle
import random
import subprocess


class PublicController(http.Controller):
    @http.route("/pmqms/audit-positive", auth="public", csrf=False, type="json")
    def exposed(self, payload=None):
        request.env[request.params.get("model")].search([])
        request.env["pm.qms.document"].sudo().create({"name": "unsafe"})
        attachment = request.env["ir.attachment"].sudo().browse(int(request.params.get("id")))
        with open(request.params.get("path"), "wb") as handle:
            handle.write(payload or b"")
        return attachment.name


def risky(env, raw, query):
    env["pm.qms.risk"].sudo().search([])
    env["res.users"].with_user(SUPERUSER_ID).browse(1)
    env.cr.execute(f"SELECT id FROM res_users WHERE login = '{raw}'")
    env.cr.execute("SELECT id FROM res_users WHERE login = '%s'" % raw)
    env.cr.execute("SELECT id FROM res_users WHERE login = '{}'".format(raw))
    env.cr.execute("SELECT id FROM " + query)
    eval(raw)
    exec(raw)
    pickle.loads(raw)
    os.system(raw)
    subprocess.run(raw, shell=True)
    return random.choice(["a", "b"])
