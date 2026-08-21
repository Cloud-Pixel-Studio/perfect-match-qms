from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsRoleDocumentRequirement(models.Model):
    _name = "pm.qms.role.document.requirement"
    _description = "Perfect Match QMS Role Document Acknowledgment Requirement"
    _order = "role_id, document_id"

    role_id = fields.Many2one("pm.qms.role", required=True, ondelete="cascade", index=True)
    document_id = fields.Many2one("pm.qms.document", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="role_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="document_id.organization_id", store=True, readonly=True, index=True)
    due_within_days = fields.Integer(default=14)
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _role_document_uniq = models.Constraint(
        "UNIQUE(role_id, document_id)",
        "A controlled document can be required only once per QMS role.",
    )

    @api.constrains("role_id", "document_id", "due_within_days")
    def _check_requirement(self):
        for requirement in self:
            if requirement.document_id.company_id != requirement.company_id:
                raise ValidationError("Document acknowledgment requirement must stay within one company.")
            if requirement.role_id.organization_id and requirement.role_id.organization_id != requirement.document_id.organization_id:
                raise ValidationError("Organization-specific role must match the controlled document organization.")
            if requirement.due_within_days < 0:
                raise ValidationError("Acknowledgment due window cannot be negative.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env["pm.qms.document.acknowledgment"].sync_for_document_requirements(records)
        return records

    def write(self, vals):
        result = super().write(vals)
        self.env["pm.qms.document.acknowledgment"].sync_for_document_requirements(self)
        return result


class PmQmsDocumentAcknowledgment(models.Model):
    _name = "pm.qms.document.acknowledgment"
    _description = "Perfect Match QMS Revision Acknowledgment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "due_date, person_id, id"

    person_id = fields.Many2one("pm.qms.person", required=True, ondelete="restrict", index=True)
    role_id = fields.Many2one("pm.qms.role", ondelete="set null", index=True)
    requirement_id = fields.Many2one("pm.qms.role.document.requirement", ondelete="set null")
    document_id = fields.Many2one(related="revision_id.document_id", store=True, readonly=True, index=True)
    revision_id = fields.Many2one("pm.qms.document.revision", required=True, ondelete="restrict", index=True)
    company_id = fields.Many2one(related="person_id.company_id", store=True, readonly=True, index=True)
    organization_id = fields.Many2one(related="person_id.organization_id", store=True, readonly=True, index=True)
    due_date = fields.Date()
    state = fields.Selection(
        [("pending", "Pending"), ("acknowledged", "Acknowledged"), ("waived", "Waived")],
        default="pending",
        required=True,
        tracking=True,
    )
    acknowledged_by = fields.Many2one("res.users", readonly=True)
    acknowledged_at = fields.Datetime(readonly=True)
    acknowledgment_note = fields.Text()
    is_overdue = fields.Boolean(compute="_compute_is_overdue", store=True)

    _person_revision_requirement_uniq = models.Constraint(
        "UNIQUE(person_id, revision_id, requirement_id)",
        "A document revision acknowledgment requirement can exist only once per person.",
    )

    @api.depends("due_date", "state")
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for acknowledgment in self:
            acknowledgment.is_overdue = bool(
                acknowledgment.state == "pending" and acknowledgment.due_date and acknowledgment.due_date < today
            )

    @api.constrains("person_id", "revision_id", "role_id")
    def _check_acknowledgment(self):
        for acknowledgment in self:
            if acknowledgment.revision_id.company_id != acknowledgment.company_id:
                raise ValidationError("Acknowledgment revision must belong to the person's company.")
            if acknowledgment.revision_id.organization_id != acknowledgment.organization_id:
                raise ValidationError("Acknowledgment revision must belong to the person's organization.")
            if acknowledgment.role_id and acknowledgment.role_id.company_id != acknowledgment.company_id:
                raise ValidationError("Acknowledgment role must belong to the person's company.")

    def _check_person_or_manager(self):
        if self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            return
        linked_person = self.env["pm.qms.person"].search(
            [("user_id", "=", self.env.user.id), ("company_id", "in", self.env.companies.ids)],
            limit=1,
        )
        if any(ack.person_id != linked_person for ack in self):
            raise AccessError("You can acknowledge only documents assigned to your linked QMS person.")

    def action_acknowledge(self):
        self._check_person_or_manager()
        for acknowledgment in self:
            if acknowledgment.state != "pending":
                raise UserError("Only pending document acknowledgments can be acknowledged.")
        self.with_context(pm_qms_acknowledge_action=True).write(
            {
                "state": "acknowledged",
                "acknowledged_by": self.env.user.id,
                "acknowledged_at": fields.Datetime.now(),
            }
        )

    def action_waive(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can waive document acknowledgments.")
        self.with_context(pm_qms_acknowledge_action=True).write({"state": "waived"})

    def write(self, vals):
        protected = {"state", "acknowledged_by", "acknowledged_at"}
        if protected.intersection(vals) and not self.env.context.get("pm_qms_acknowledge_action"):
            raise AccessError("Use acknowledgment workflow actions to change acknowledgment state.")
        return super().write(vals)

    @api.model
    def sync_for_people(self, people):
        people = people.exists()
        Requirement = self.env["pm.qms.role.document.requirement"]
        for person in people:
            requirements = Requirement.search(
                [
                    ("role_id", "in", person.active_role_ids.ids),
                    ("active", "=", True),
                    ("document_id.current_revision_id", "!=", False),
                ]
            )
            for requirement in requirements:
                revision = requirement.document_id.current_revision_id
                due_date = (revision.effective_date or fields.Date.context_today(self)) + timedelta(
                    days=requirement.due_within_days
                )
                domain = [
                    ("person_id", "=", person.id),
                    ("revision_id", "=", revision.id),
                    ("requirement_id", "=", requirement.id),
                ]
                if not self.search_count(domain):
                    self.create(
                        {
                            "person_id": person.id,
                            "role_id": requirement.role_id.id,
                            "requirement_id": requirement.id,
                            "revision_id": revision.id,
                            "due_date": due_date,
                        }
                    )
        return True

    @api.model
    def sync_for_document_requirements(self, requirements):
        people = self.env["pm.qms.person"].search([("role_assignment_ids.role_id", "in", requirements.mapped("role_id").ids)])
        return self.sync_for_people(people)

    @api.model
    def sync_for_revisions(self, revisions):
        requirements = self.env["pm.qms.role.document.requirement"].search(
            [("document_id", "in", revisions.mapped("document_id").ids), ("active", "=", True)]
        )
        return self.sync_for_document_requirements(requirements)

    @api.model
    def cron_create_overdue_activities(self):
        records = self.search([("state", "=", "pending"), ("is_overdue", "=", True)])
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not activity_type:
            return True
        model = self.env["ir.model"]._get(self._name)
        for record in records:
            summary = f"Acknowledge {record.document_id.code} Rev {record.revision_id.revision}"
            existing = self.env["mail.activity"].search_count(
                [
                    ("res_model_id", "=", model.id),
                    ("res_id", "=", record.id),
                    ("activity_type_id", "=", activity_type.id),
                    ("summary", "=", summary),
                ]
            )
            if not existing:
                record.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=summary,
                    note="Controlled document acknowledgment is overdue.",
                    date_deadline=record.due_date,
                )
        return True
