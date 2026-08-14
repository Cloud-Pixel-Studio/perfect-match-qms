from odoo import fields, models
from odoo.exceptions import AccessError


class PmQmsEvent(models.Model):
    _name = "pm.qms.event"
    _description = "Perfect Match QMS Operational Event"
    _order = "event_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(required=True)
    event_date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    user_id = fields.Many2one("res.users", required=True, readonly=True)
    company_id = fields.Many2one("res.company", readonly=True, index=True)
    organization_id = fields.Many2one("pm.qms.organization", readonly=True, index=True)
    res_model = fields.Char(required=True, readonly=True, index=True)
    res_id = fields.Integer(required=True, readonly=True, index=True)
    record_name = fields.Char(readonly=True)
    event_type = fields.Selection(
        [
            ("workflow", "Workflow Transition"),
            ("review", "Review"),
            ("approval", "Approval"),
            ("closure", "Closure"),
            ("effectiveness", "Effectiveness Decision"),
            ("attachment", "Attachment Control"),
            ("system", "System Event"),
        ],
        default="workflow",
        required=True,
        readonly=True,
    )
    previous_state = fields.Char(readonly=True)
    new_state = fields.Char(readonly=True)
    reviewer_id = fields.Many2one("res.users", readonly=True)
    approver_id = fields.Many2one("res.users", readonly=True)
    decision = fields.Char(readonly=True)
    notes = fields.Text(readonly=True)

    def write(self, vals):
        raise AccessError("QMS operational events are append-only.")

    def unlink(self):
        raise AccessError("QMS operational events cannot be deleted.")


class PmQmsEventMixin(models.AbstractModel):
    _name = "pm.qms.event.mixin"
    _description = "Perfect Match QMS Event Logging Mixin"

    def _qms_event_company(self):
        self.ensure_one()
        if "company_id" in self._fields:
            return self.company_id
        return self.env.company

    def _qms_event_organization(self):
        self.ensure_one()
        if "organization_id" in self._fields:
            return self.organization_id
        return self.env["pm.qms.organization"]

    def _log_qms_event(
        self,
        event_type="workflow",
        previous_state=None,
        new_state=None,
        reviewer=None,
        approver=None,
        decision=None,
        notes=None,
    ):
        Event = self.env["pm.qms.event"].sudo()
        for record in self:
            company = record._qms_event_company()
            organization = record._qms_event_organization()
            label = decision or event_type.replace("_", " ").title()
            Event.create(
                {
                    "name": f"{label}: {record.display_name}",
                    "event_date": fields.Datetime.now(),
                    "user_id": self.env.user.id,
                    "company_id": company.id if company else False,
                    "organization_id": organization.id if organization else False,
                    "res_model": record._name,
                    "res_id": record.id,
                    "record_name": record.display_name,
                    "event_type": event_type,
                    "previous_state": previous_state,
                    "new_state": new_state,
                    "reviewer_id": reviewer.id if reviewer else False,
                    "approver_id": approver.id if approver else False,
                    "decision": decision,
                    "notes": notes,
                }
            )

    def _sync_qms_attachment_links(self, field_name="attachment_ids"):
        for record in self:
            if field_name not in record._fields:
                continue
            for attachment in record[field_name]:
                if not attachment.res_model or (attachment.res_model == record._name and attachment.res_id in (0, record.id)):
                    attachment.write({"res_model": record._name, "res_id": record.id})
