from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class PmQmsExternalMapping(models.Model):
    _inherit = "pm.qms.external.mapping"

    mapping_profile_id = fields.Many2one(
        "pm.qms.mapping.profile",
        string="Mapping Profile",
        ondelete="restrict",
        index=True,
    )
    mapping_type = fields.Selection(
        [
            ("direct", "Direct"),
            ("supporting", "Supporting"),
            ("partial", "Partial"),
        ],
        default="supporting",
        required=True,
    )
    review_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("reviewed", "Reviewed"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
    )
    reviewed_by_id = fields.Many2one("res.users", string="Reviewed By", copy=False)
    review_date = fields.Date(copy=False)
    imported_by_id = fields.Many2one("res.users", string="Imported By", copy=False)
    import_batch = fields.Char(copy=False)

    def _check_mapping_admin(self):
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
            raise AccessError("Only QMS Administrators can approve or change profile-based external mappings.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            profile = self.env["pm.qms.mapping.profile"].browse(vals.get("mapping_profile_id"))
            if profile:
                self._check_mapping_admin()
                vals.setdefault("standard_name", profile.standard_name)
                vals.setdefault("edition", profile.edition)
                vals.setdefault("imported_by_id", self.env.user.id)
        return super().create(vals_list)

    @api.constrains("mapping_profile_id", "control_id", "standard_name", "edition", "reference")
    def _check_profile_relationship(self):
        for mapping in self.filtered("mapping_profile_id"):
            profile = mapping.mapping_profile_id
            if mapping.control_id.company_id != profile.company_id:
                raise ValidationError("Mapping control must belong to the mapping profile company.")
            if mapping.standard_name != profile.standard_name or mapping.edition != profile.edition:
                raise ValidationError("Mapping standard and edition must match the mapping profile.")
            pack_controls = profile.pack_id.control_line_ids.filtered("active").mapped("control_id")
            if mapping.control_id not in pack_controls:
                raise ValidationError("Mapping control must belong to the related framework pack.")
            if not (mapping.reference or "").strip():
                raise ValidationError("External reference identifier is required.")

    def action_mark_reviewed(self):
        self._check_mapping_admin()
        self.with_context(pm_qms_mapping_workflow=True).write(
            {
                "review_status": "reviewed",
                "reviewed_by_id": self.env.user.id,
                "review_date": fields.Date.context_today(self),
            }
        )

    def action_approve(self):
        self._check_mapping_admin()
        self.with_context(pm_qms_mapping_workflow=True).write(
            {
                "review_status": "approved",
                "reviewed_by_id": self.env.user.id,
                "review_date": fields.Date.context_today(self),
            }
        )

    def action_reject(self):
        self._check_mapping_admin()
        self.with_context(pm_qms_mapping_workflow=True).write(
            {
                "review_status": "rejected",
                "reviewed_by_id": self.env.user.id,
                "review_date": fields.Date.context_today(self),
            }
        )

    def action_reset_to_draft(self):
        self._check_mapping_admin()
        self.with_context(pm_qms_mapping_workflow=True).write(
            {
                "review_status": "draft",
                "reviewed_by_id": False,
                "review_date": False,
            }
        )

    def write(self, vals):
        profile_mappings = self.filtered("mapping_profile_id")
        if profile_mappings and not self.env.context.get("pm_qms_mapping_workflow"):
            protected = {
                "mapping_profile_id",
                "control_id",
                "standard_name",
                "edition",
                "reference",
                "mapping_type",
                "review_status",
                "reviewed_by_id",
                "review_date",
            }
            if protected.intersection(vals):
                self._check_mapping_admin()
        if "review_status" in vals and not self.env.context.get("pm_qms_mapping_workflow"):
            self._check_mapping_admin()
        approved = profile_mappings.filtered(lambda mapping: mapping.review_status == "approved")
        definition_fields = {"mapping_profile_id", "control_id", "standard_name", "edition", "reference", "mapping_type"}
        if approved and definition_fields.intersection(vals):
            raise UserError("Create a new mapping profile or mapping record instead of changing an approved mapping.")
        return super().write(vals)

    def unlink(self):
        if any(mapping.review_status == "approved" for mapping in self):
            raise UserError("Approved external mappings cannot be deleted.")
        if any(mapping.mapping_profile_id for mapping in self):
            self._check_mapping_admin()
        return super().unlink()
