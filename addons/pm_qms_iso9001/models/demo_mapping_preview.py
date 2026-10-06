from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from .framework_pack import (
    ISO9001_2026_PACK_CODE,
    is_authorized_demo_2026_mapping_preview,
    is_authorized_demo_2026_preview,
)
from ..hooks import ISO9001_2026_PACK_PROFILE_CODE


class PmQmsExternalMappingDemoPreview(models.Model):
    _inherit = "pm.qms.external.mapping"

    demo_preview_usable = fields.Boolean(
        string="Usable in Isolated Demo Preview",
        default=False,
        copy=False,
        readonly=True,
        help=(
            "Demo-only display permission. This does not mean the mapping was reviewed or approved, "
            "and it never contributes to approved mapping coverage."
        ),
    )
    demo_preview_enabled_by_id = fields.Many2one(
        "res.users", string="Demo Preview Enabled By", readonly=True, copy=False
    )
    demo_preview_enabled_on = fields.Date(
        string="Demo Preview Enabled On", readonly=True, copy=False
    )

    def write(self, vals):
        guarded = {"demo_preview_usable", "demo_preview_enabled_by_id", "demo_preview_enabled_on"}
        if guarded.intersection(vals):
            if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
                raise AccessError("Only QMS Administrators can configure demo-only mapping visibility.")
            if not is_authorized_demo_2026_preview(self.env):
                raise AccessError("Demo-only mapping visibility is restricted to the licensed isolated Demo2026.")
            for mapping in self:
                profile = mapping.mapping_profile_id
                if not (
                    profile
                    and profile.code == ISO9001_2026_PACK_PROFILE_CODE
                    and profile.edition == "2026"
                    and profile.pack_id.code == ISO9001_2026_PACK_CODE
                    and profile.pack_id.state == "demo_preview"
                    and profile.state == "draft"
                    and mapping.review_status == "draft"
                ):
                    raise UserError("Only draft mappings in the isolated ISO 9001:2026 Demo Preview can be enabled.")
        return super().write(vals)


class PmQmsMappingProfileDemoPreview(models.Model):
    _inherit = "pm.qms.mapping.profile"

    demo_preview_usable_count = fields.Integer(compute="_compute_demo_preview_usable_count")
    demo_preview_pack_state = fields.Selection(related="pack_id.state")

    @api.depends("mapping_ids.demo_preview_usable")
    def _compute_demo_preview_usable_count(self):
        for profile in self:
            profile.demo_preview_usable_count = len(
                profile.mapping_ids.filtered("demo_preview_usable")
            )

    def action_enable_demo_preview_mappings(self):
        self.ensure_one()
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
            raise AccessError("Only QMS Administrators can enable demo-only mapping visibility.")
        if not is_authorized_demo_2026_preview(self.env):
            raise AccessError("This action is restricted to the licensed isolated Demo2026.")
        if not (
            self.code == ISO9001_2026_PACK_PROFILE_CODE
            and self.standard_name == "ISO 9001"
            and self.edition == "2026"
            and self.state == "draft"
            and self.pack_id.code == ISO9001_2026_PACK_CODE
            and self.pack_id.state == "demo_preview"
            and self.company_id == self.env.company
        ):
            raise UserError("Only the isolated Demo2026 draft mapping profile can use this action.")
        mappings = self.mapping_ids.filtered("active")
        if len(mappings) != 65 or any(mapping.review_status != "draft" for mapping in mappings):
            raise UserError("Expected exactly 65 active draft mappings; no changes were made.")
        if all(mappings.mapped("demo_preview_usable")):
            return True
        if any(mappings.mapped("demo_preview_usable")):
            raise UserError("The mapping set is partially enabled; reconcile it before retrying.")
        values = {
            "demo_preview_usable": True,
            "demo_preview_enabled_by_id": self.env.user.id,
            "demo_preview_enabled_on": fields.Date.context_today(self),
        }
        mappings.write(values)
        self._log_qms_event(
            event_type="workflow",
            previous_state="draft",
            new_state="draft",
            decision=(
                "Enabled 65 mappings for isolated Demo Preview exploration only; "
                "mappings remain unreviewed and unapproved"
            ),
        )
        return True


class PmQmsImplementationControlDemoPreview(models.Model):
    _inherit = "pm.qms.implementation.control"

    @api.depends(
        "control_id.external_mapping_ids.standard_name",
        "control_id.external_mapping_ids.edition",
        "control_id.external_mapping_ids.reference",
        "control_id.external_mapping_ids.active",
        "control_id.external_mapping_ids.review_status",
        "control_id.external_mapping_ids.demo_preview_usable",
    )
    def _compute_external_alignment_summary(self):
        for line in self:
            mappings = line.control_id.external_mapping_ids.filtered("active")
            approved = mappings.filtered(lambda mapping: mapping.review_status == "approved")
            demo_preview = mappings.filtered(
                lambda mapping: is_authorized_demo_2026_mapping_preview(self.env, mapping)
            )
            selected = approved | demo_preview
            parts = []
            for mapping in selected.sorted(
                lambda item: (item.standard_name or "", item.edition or "", item.reference or "")
            ):
                label = " ".join(part for part in [mapping.standard_name, mapping.edition] if part)
                reference = f"{label}: {mapping.reference}" if label else mapping.reference
                if mapping.demo_preview_usable:
                    reference = f"DEMO PREVIEW ONLY — NOT APPROVED — {reference}"
                parts.append(reference)
            line.external_alignment_summary = "\n".join(parts)
