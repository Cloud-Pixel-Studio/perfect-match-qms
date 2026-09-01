import json

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from ..services.environment import read_environment_id, short_environment_id
from ..services.license_service import LicenseValidationError, effective_temporal_state, validate_document


LICENSE_STATE_SELECTION = [
    ("valid", "Valid"),
    ("expiring", "Expiring"),
    ("expired", "Expired"),
    ("not_yet_valid", "Not Yet Valid"),
    ("invalid_signature", "Invalid Signature"),
    ("wrong_environment", "Wrong Environment"),
    ("invalid_format", "Invalid Format"),
]


class PmQmsLicense(models.Model):
    _name = "pm.qms.license"
    _description = "Perfect Match QMS Commercial License"
    _order = "is_current desc, license_revision desc, id desc"
    _rec_name = "license_id"

    license_id = fields.Char(required=True, readonly=True, index=True)
    license_revision = fields.Integer(required=True, readonly=True)
    customer_name = fields.Char(required=True, readonly=True)
    edition = fields.Char(required=True, readonly=True)
    environment_id = fields.Char(string="Environment ID", required=True, readonly=True)
    environment_short = fields.Char(compute="_compute_environment_short", string="Environment", readonly=True)
    company_limit = fields.Integer(required=True, readonly=True)
    site_limit = fields.Integer(required=True, readonly=True)
    named_user_limit = fields.Integer(required=True, readonly=True)
    issued_at = fields.Datetime(readonly=True)
    not_before = fields.Datetime(readonly=True)
    expires_at = fields.Datetime(readonly=True)
    perpetual = fields.Boolean(readonly=True)
    key_id = fields.Char(readonly=True)
    signature = fields.Text(readonly=True)
    payload_json = fields.Text(string="Signed Payload", readonly=True)
    state = fields.Selection(
        LICENSE_STATE_SELECTION,
        required=True,
        readonly=True,
    )
    effective_state = fields.Selection(
        selection=LICENSE_STATE_SELECTION,
        compute="_compute_effective_state",
        string="Current Status",
        readonly=True,
    )
    is_current = fields.Boolean(default=True, readonly=True, index=True)
    fingerprint = fields.Char(readonly=True)
    public_key_fingerprint = fields.Char(readonly=True)
    company_usage = fields.Integer(compute="_compute_usage", string="Operational Companies", readonly=True)
    site_usage = fields.Integer(compute="_compute_usage", string="Active Sites", readonly=True)
    named_user_usage = fields.Integer(compute="_compute_usage", string="Named Users", readonly=True)
    activation_request_ids = fields.One2many("pm.qms.activation.request", "license_id", readonly=True)

    def _remove_unauthorized_activation_view_metadata(self, view_result):
        """Keep the web client from requesting the restricted relation metadata."""
        if self.env.user.has_group("pm_qms_license.group_pm_qms_license_admin"):
            return view_result

        result = dict(view_result)
        models = dict(result.get("models", {}))
        model_metadata = models.get(self._name)
        if isinstance(model_metadata, dict) and "fields" in model_metadata:
            model_metadata = dict(model_metadata)
            model_metadata["fields"] = {
                name: definition
                for name, definition in model_metadata["fields"].items()
                if name != "activation_request_ids"
            }
            models[self._name] = model_metadata
        elif model_metadata is not None:
            models[self._name] = tuple(
                name for name in model_metadata if name != "activation_request_ids"
            )
        models.pop("pm.qms.activation.request", None)
        result["models"] = models
        return result

    @api.model
    def get_view(self, view_id=None, view_type="form", **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        return self._remove_unauthorized_activation_view_metadata(result)

    @api.model
    def get_views(self, views, options=None):
        result = super().get_views(views, options=options)
        return self._remove_unauthorized_activation_view_metadata(result)

    _license_revision_check = models.Constraint(
        "CHECK(license_revision > 0)",
        "License revision must be positive.",
    )

    @api.depends("environment_id")
    def _compute_environment_short(self):
        for record in self:
            record.environment_short = short_environment_id(record.environment_id)

    def _compute_usage(self):
        service = self.env["pm.qms.entitlement.service"]
        for record in self:
            usage = service.usage()
            record.company_usage = usage["company"]["used"]
            record.site_usage = usage["site"]["used"]
            record.named_user_usage = usage["named_user"]["used"]

    @api.depends("state", "not_before", "expires_at", "perpetual")
    def _compute_effective_state(self):
        for record in self:
            record.effective_state = effective_temporal_state(
                record.state,
                record.not_before,
                record.expires_at,
                record.perpetual,
            )

    @api.model
    def current(self):
        return self.sudo().search([("is_current", "=", True)], order="id desc", limit=1)

    @api.model
    def current_status(self):
        current = self.current()
        if not current:
            return {"status": "missing", "license": False}
        return {"status": current.effective_state, "license": current}

    @api.model
    def _check_write_authority(self, vals):
        signed_fields = {
            "license_id", "license_revision", "customer_name", "edition", "environment_id",
            "company_limit", "site_limit", "named_user_limit", "issued_at", "not_before",
            "expires_at", "perpetual", "key_id", "signature", "payload_json", "state", "is_current",
        }
        if signed_fields.intersection(vals) and not (
            self.env.is_superuser() or self.env.user.has_group("pm_qms_license.group_pm_qms_license_admin")
        ):
            raise AccessError("Only authorized QMS licensing administration can replace a commercial license.")

    def write(self, vals):
        self._check_write_authority(vals)
        return super().write(vals)

    @api.model
    def import_document(self, document, expected_environment_id=None):
        expected_environment_id = expected_environment_id or read_environment_id()
        try:
            result = validate_document(document, expected_environment_id=expected_environment_id)
        except LicenseValidationError as exc:
            raise UserError(str(exc)) from exc
        payload = result["payload"]
        current = self.current()
        if current and current.license_id == payload["license_id"] and payload["license_revision"] <= current.license_revision:
            raise UserError("An older or identical license revision cannot replace the current license.")
        if current:
            current.write({"is_current": False})
        values = {
            "license_id": payload["license_id"],
            "license_revision": payload["license_revision"],
            "customer_name": payload["customer_name"],
            "edition": payload["edition"],
            "environment_id": payload["environment_id"],
            "company_limit": payload["company_limit"],
            "site_limit": payload["site_limit"],
            "named_user_limit": payload["named_user_limit"],
            "issued_at": result["issued_at"].replace(tzinfo=None) if result["issued_at"] else False,
            "not_before": result["not_before"].replace(tzinfo=None) if result["not_before"] else False,
            "expires_at": result["expires_at"].replace(tzinfo=None) if result["expires_at"] else False,
            "perpetual": payload["perpetual"],
            "key_id": payload["key_id"],
            "signature": result["signature"],
            "payload_json": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
            "state": result["state"],
            "is_current": True,
            "fingerprint": result["fingerprint"],
            "public_key_fingerprint": result["public_key_fingerprint"],
        }
        return self.sudo().create(values)

    def action_open_import_wizard(self):
        self.ensure_one()
        return self.env.ref("pm_qms_license.action_pm_qms_license_import").read()[0]

    def action_generate_activation_request(self):
        self.ensure_one()
        request = self.env["pm.qms.activation.request"].create({})
        return {
            "type": "ir.actions.act_window",
            "name": "Activation Request",
            "res_model": "pm.qms.activation.request",
            "view_mode": "form",
            "res_id": request.id,
            "target": "current",
        }

    def action_view_history(self):
        return self.env.ref("pm_qms_license.action_pm_qms_license_history").read()[0]
