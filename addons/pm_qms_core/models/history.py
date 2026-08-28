from odoo import api, fields, models
from odoo.exceptions import AccessError


PM_QMS_MODEL_PREFIX = "pm.qms."
HISTORY_IMMUTABLE_FIELDS = frozenset(
    {
        "author_id",
        "body",
        "date",
        "message_type",
        "model",
        "res_id",
        "subtype_id",
    }
)


class ResPartner(models.Model):
    _inherit = "res.partner"

    pm_qms_system_actor = fields.Boolean(
        compute="_compute_pm_qms_system_actor",
        compute_sudo=True,
        help="Technical marker for the stable Odoo system actor on PM QMS UI.",
    )

    @api.depends()
    def _compute_pm_qms_system_actor(self):
        system_partner = self.env.ref("base.partner_root", raise_if_not_found=False)
        system_partner_id = system_partner.id if system_partner else False
        for partner in self:
            partner.pm_qms_system_actor = partner.id == system_partner_id


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _pm_qms_records(self):
        return self.filtered(
            lambda message: message.model
            and message.res_id
            and message.model.startswith(PM_QMS_MODEL_PREFIX)
        )

    def _pm_qms_history_protected(self):
        """Return PM messages whose business history is already published."""
        return self._pm_qms_records().filtered(
            lambda message: message.tracking_value_ids
            or message.subtype_id == self.env.ref("mail.mt_note")
        )

    def _check_pm_qms_history_write(self, vals):
        if self.env.is_system() or not vals:
            return
        protected = self._pm_qms_history_protected()
        if not protected:
            return
        changed_fields = set(vals) & HISTORY_IMMUTABLE_FIELDS
        if changed_fields:
            raise AccessError(
                "Published Perfect Match QMS history cannot be rewritten. "
                "Post a new Internal Note to record a correction."
            )

    def write(self, vals):
        self._check_pm_qms_history_write(vals)
        return super().write(vals)

    def unlink(self):
        if not self.env.is_system() and self._pm_qms_history_protected():
            raise AccessError(
                "Published Perfect Match QMS history cannot be deleted."
            )
        return super().unlink()

    def _get_store_partner_name_fields(self):
        return [*super()._get_store_partner_name_fields(), "pm_qms_system_actor"]


class MailTrackingValue(models.Model):
    _inherit = "mail.tracking.value"

    def _pm_qms_tracking_values(self):
        return self.filtered(
            lambda value: value.mail_message_id
            and value.mail_message_id.model
            and value.mail_message_id.res_id
            and value.mail_message_id.model.startswith(PM_QMS_MODEL_PREFIX)
        )

    def _check_pm_qms_history_write(self):
        if not self.env.is_system() and self._pm_qms_tracking_values():
            raise AccessError(
                "Perfect Match QMS field history cannot be rewritten."
            )

    def write(self, vals):
        self._check_pm_qms_history_write()
        return super().write(vals)

    def unlink(self):
        self._check_pm_qms_history_write()
