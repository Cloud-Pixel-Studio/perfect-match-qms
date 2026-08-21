from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PmQmsQualificationType(models.Model):
    _name = "pm.qms.qualification.type"
    _description = "Perfect Match QMS Qualification Type"
    _order = "code, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Text()
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    expiring_soon_days = fields.Integer(default=60)
    active = fields.Boolean(default=True)

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Qualification type code must be unique per company.",
    )

    @api.constrains("expiring_soon_days")
    def _check_expiring_soon_days(self):
        for qualification_type in self:
            if qualification_type.expiring_soon_days < 0:
                raise ValidationError("Expiring-soon window cannot be negative.")


class PmQmsQualificationRecord(models.Model):
    _name = "pm.qms.qualification.record"
    _description = "Perfect Match QMS Qualification Record"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "expiration_date, person_id, id"

    person_id = fields.Many2one("pm.qms.person", required=True, ondelete="restrict", index=True)
    qualification_type_id = fields.Many2one("pm.qms.qualification.type", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="person_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="person_id.organization_id", store=True, readonly=True, index=True)
    identifier = fields.Char(string="Certificate / Identifier")
    issuer = fields.Char()
    issue_date = fields.Date()
    expiration_date = fields.Date()
    attachment_id = fields.Many2one("ir.attachment", string="Qualification Evidence")
    status = fields.Selection(
        [("valid", "Valid"), ("expiring", "Expiring Soon"), ("expired", "Expired"), ("no_expiration", "No Expiration")],
        compute="_compute_status",
        store=True,
    )
    notes = fields.Text()

    @api.depends("expiration_date", "qualification_type_id.expiring_soon_days")
    def _compute_status(self):
        today = fields.Date.context_today(self)
        for record in self:
            if not record.expiration_date:
                record.status = "no_expiration"
            elif record.expiration_date < today:
                record.status = "expired"
            elif (record.expiration_date - today).days <= record.qualification_type_id.expiring_soon_days:
                record.status = "expiring"
            else:
                record.status = "valid"

    @api.constrains("person_id", "qualification_type_id", "issue_date", "expiration_date")
    def _check_record(self):
        for record in self:
            if record.qualification_type_id.company_id != record.company_id:
                raise ValidationError("Qualification type must belong to the person's company.")
            if record.issue_date and record.expiration_date and record.expiration_date < record.issue_date:
                raise ValidationError("Qualification expiration cannot be before issue date.")

    @api.model
    def cron_create_expiration_activities(self):
        records = self.search([("status", "in", ("expiring", "expired"))])
        records._ensure_expiration_activities()
        return True

    def _ensure_expiration_activities(self):
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return
        model = self.env["ir.model"]._get(self._name)
        for record in self:
            summary = f"Review qualification: {record.qualification_type_id.name}"
            existing = self.env["mail.activity"].search_count(
                [
                    ("res_model_id", "=", model.id),
                    ("res_id", "=", record.id),
                    ("activity_type_id", "=", activity_type.id),
                    ("summary", "=", summary),
                ]
            )
            if existing:
                continue
            record.activity_schedule(
                activity_type_id=activity_type.id,
                summary=summary,
                note="Qualification is expired or approaching expiration.",
                date_deadline=record.expiration_date or fields.Date.context_today(record),
            )
