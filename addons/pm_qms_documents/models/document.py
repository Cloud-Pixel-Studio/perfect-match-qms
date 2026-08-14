from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsDocument(models.Model):
    _name = "pm.qms.document"
    _description = "Perfect Match QMS Controlled Document"
    _inherit = ["mail.thread", "mail.activity.mixin", "pm.qms.event.mixin"]
    _order = "code, name"

    name = fields.Char(string="Title", required=True, tracking=True)
    code = fields.Char(default="New", required=True, copy=False, tracking=True)
    company_id = fields.Many2one(
        "res.company",
        related="organization_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    organization_id = fields.Many2one("pm.qms.organization", required=True, ondelete="restrict", index=True)
    process_id = fields.Many2one("pm.qms.process", required=True, ondelete="restrict", index=True)
    document_type = fields.Selection(
        [
            ("policy", "Policy"),
            ("procedure", "Procedure"),
            ("work_instruction", "Work Instruction"),
            ("form", "Form"),
            ("record_template", "Record Template"),
            ("manual", "Manual"),
            ("other", "Other"),
        ],
        default="procedure",
        required=True,
        tracking=True,
    )
    owner_id = fields.Many2one("res.users", string="Document Owner", tracking=True)
    active = fields.Boolean(default=True)
    current_revision_id = fields.Many2one(
        "pm.qms.document.revision",
        copy=False,
        readonly=True,
        string="Current Revision Record",
    )
    current_revision = fields.Char(related="current_revision_id.revision", store=True, readonly=True)
    effective_date = fields.Date(related="current_revision_id.effective_date", store=True, readonly=True)
    review_date = fields.Date(related="current_revision_id.review_date", store=True, readonly=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("under_review", "Under Review"),
            ("approved", "Approved"),
            ("active", "Active"),
            ("obsolete", "Obsolete"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    revision_ids = fields.One2many("pm.qms.document.revision", "document_id", string="Revisions")
    related_control_ids = fields.Many2many(
        "pm.qms.control",
        "pm_qms_doc_control_rel",
        "document_id",
        "control_id",
        string="Related Framework Controls",
    )
    related_control_instance_ids = fields.Many2many(
        "pm.qms.control.instance",
        "pm_qms_doc_instance_rel",
        "document_id",
        "control_instance_id",
        string="Related Control Instances",
    )

    _code_company_uniq = models.Constraint(
        "UNIQUE(code, company_id)",
        "Document code must be unique per company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals.get("code") == "New":
                vals["code"] = self.env["ir.sequence"].next_by_code("pm.qms.document") or "PM-DOC-00000"
        return super().create(vals_list)

    @api.constrains("organization_id", "process_id")
    def _check_process_alignment(self):
        for record in self:
            if record.process_id.company_id != record.organization_id.company_id:
                raise ValidationError("Document process must belong to the same company as the organization.")
            if record.process_id.organization_id and record.process_id.organization_id != record.organization_id:
                raise ValidationError("Document process must belong to the selected organization.")

    @api.constrains("related_control_ids", "related_control_instance_ids")
    def _check_related_records_alignment(self):
        for record in self:
            company = record.company_id
            if any(control.company_id != company for control in record.related_control_ids):
                raise ValidationError("Related framework controls must belong to the same company as the document.")
            if any(instance.company_id != company for instance in record.related_control_instance_ids):
                raise ValidationError("Related control instances must belong to the same company as the document.")
            if any(instance.organization_id != record.organization_id for instance in record.related_control_instance_ids):
                raise ValidationError("Related control instances must belong to the same organization as the document.")

    def _check_manager_permission(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_manager"):
            raise AccessError("Only QMS Managers or Administrators can perform controlled document workflow actions.")

    def action_submit_for_review(self):
        self._check_manager_permission()
        previous = {document.id: document.state for document in self}
        self.with_context(pm_qms_document_workflow=True).write({"state": "under_review"})
        for document in self:
            document._log_qms_event(
                event_type="workflow",
                previous_state=previous[document.id],
                new_state="under_review",
                reviewer=self.env.user,
                decision="Document submitted for review",
            )
            document.revision_ids.filtered(lambda revision: revision.state == "draft").action_submit_for_review()

    def action_approve(self):
        self._check_manager_permission()
        previous = {document.id: document.state for document in self}
        self.with_context(pm_qms_document_workflow=True).write({"state": "approved"})
        for document in self:
            document._log_qms_event(
                event_type="approval",
                previous_state=previous[document.id],
                new_state="approved",
                approver=self.env.user,
                decision="Document approved",
            )
            document.revision_ids.filtered(lambda revision: revision.state == "under_review").action_approve()

    def action_reject(self):
        self._check_manager_permission()
        previous = {document.id: document.state for document in self}
        self.with_context(pm_qms_document_workflow=True).write({"state": "draft"})
        for document in self:
            document._log_qms_event(
                event_type="review",
                previous_state=previous[document.id],
                new_state="draft",
                reviewer=self.env.user,
                decision="Document review rejected",
            )
            document.revision_ids.filtered(lambda revision: revision.state == "under_review").action_reject()

    def action_activate(self):
        self._check_manager_permission()
        for document in self:
            revision = document.revision_ids.filtered(lambda item: item.state in ("approved", "active"))[:1]
            if not revision:
                raise UserError("A document needs an approved revision before activation.")
            revision.action_activate()

    def action_obsolete(self):
        self._check_manager_permission()
        previous = {document.id: document.state for document in self}
        self.with_context(pm_qms_document_workflow=True).write({"state": "obsolete", "active": False})
        for document in self:
            document._log_qms_event(
                event_type="closure",
                previous_state=previous[document.id],
                new_state="obsolete",
                approver=self.env.user,
                decision="Document made obsolete",
            )

    def action_create_new_revision(self):
        self._check_manager_permission()
        self.ensure_one()
        revision = self.env["pm.qms.document.revision"].create(
            {
                "document_id": self.id,
                "revision": self._next_revision_name(),
                "prepared_by": self.env.user.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": "Document Revision",
            "res_model": "pm.qms.document.revision",
            "res_id": revision.id,
            "view_mode": "form",
        }

    def _next_revision_name(self):
        self.ensure_one()
        revisions = self.revision_ids.mapped("revision")
        numeric = [int(value) for value in revisions if str(value).isdigit()]
        if numeric:
            return str(max(numeric) + 1).zfill(2)
        return "01" if not revisions else f"{len(revisions) + 1:02d}"

    def write(self, vals):
        if "state" in vals and not self.env.context.get("pm_qms_document_workflow"):
            raise AccessError("Use controlled document workflow actions to change document status.")
        return super().write(vals)
