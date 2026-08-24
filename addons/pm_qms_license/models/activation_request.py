import json

from odoo import api, fields, models

from ..services.environment import read_environment_id, short_environment_id


class PmQmsActivationRequest(models.Model):
    _name = "pm.qms.activation.request"
    _description = "Perfect Match QMS Offline Activation Request"
    _order = "requested_at desc, id desc"

    name = fields.Char(default="New Activation Request", readonly=True)
    requested_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    requested_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    environment_id = fields.Char(default=lambda self: read_environment_id() or "", readonly=True)
    environment_short = fields.Char(compute="_compute_environment_short", readonly=True)
    customer_name = fields.Char(readonly=True)
    company_count = fields.Integer(readonly=True)
    site_count = fields.Integer(readonly=True)
    named_user_count = fields.Integer(readonly=True)
    state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Submitted"), ("fulfilled", "Fulfilled")],
        default="draft",
        readonly=True,
    )
    request_json = fields.Text(string="Activation Request", readonly=True)
    license_id = fields.Many2one("pm.qms.license", readonly=True, ondelete="set null")

    @api.depends("environment_id")
    def _compute_environment_short(self):
        for request in self:
            request.environment_short = short_environment_id(request.environment_id)

    @api.model_create_multi
    def create(self, vals_list):
        service = self.env["pm.qms.entitlement.service"]
        usage = service.usage()
        company = self.env.company
        organizations = service._operational_organizations(company)
        prepared = []
        for vals in vals_list:
            values = dict(vals)
            environment_id = values.get("environment_id") or read_environment_id() or ""
            customer_name = values.get("customer_name") or (organizations[:1].name if organizations else company.name)
            values.update(
                {
                    "name": values.get("name") or f"Activation Request {environment_id[:8].upper()}",
                    "environment_id": environment_id,
                    "customer_name": customer_name,
                    "company_count": usage["company"]["used"],
                    "site_count": usage["site"]["used"],
                    "named_user_count": usage["named_user"]["used"],
                }
            )
            values["request_json"] = json.dumps(
                {
                    "schema_version": 1,
                    "request_type": "pmqms-offline-activation",
                    "environment_id": environment_id,
                    "customer_name": customer_name,
                    "company_count": usage["company"]["used"],
                    "site_count": usage["site"]["used"],
                    "named_user_count": usage["named_user"]["used"],
                    "requested_at": fields.Datetime.to_string(fields.Datetime.now()),
                },
                sort_keys=True,
                indent=2,
            )
            prepared.append(values)
        return super().create(prepared)
