import json
import os

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.addons.pm_qms_license.services.environment import read_environment_id

from ..hooks import (
    seed_iso9001_initial_implementation,
    seed_iso9001_transition_scenarios,
    seed_iso9001_2026_implementation_pack,
    ISO9001_2026_PACK_CODE,
)
from odoo.addons.pm_qms_pack_quality.hooks import is_demo_2026_only_install


DEMO_2026_PUBLIC_FINGERPRINT = "2b9b1f747ffa21e0aed00e461f661ca81536689a842566263ac96948e65d6ee7"


def is_authorized_demo_2026_preview(env):
    """Allow unreviewed pack exploration only in the licensed isolated Demo2."""
    if env.cr.dbname != "pmqms_demo2" or os.getenv("PMQMS_DEMO_INSTANCE") != "demo2":
        return False
    license_record = env["pm.qms.license"].current()
    if not license_record:
        return False
    try:
        scope = json.loads(license_record.payload_json).get("deployment_scope")
        environment_matches = license_record.environment_id == read_environment_id()
    except (AttributeError, TypeError, ValueError):
        return False
    return bool(
        license_record.effective_state in ("valid", "expiring")
        and environment_matches
        and license_record.key_id == "pmqms-demo-2026-v3"
        and license_record.public_key_fingerprint == DEMO_2026_PUBLIC_FINGERPRINT
        and scope == "demo-qa"
        and (license_record.company_limit, license_record.site_limit, license_record.named_user_limit)
        == (1, 3, 7)
    )


class PmQmsIso9001FrameworkPack(models.Model):
    _inherit = "pm.qms.framework.pack"

    state = fields.Selection(
        selection_add=[("demo_preview", "Demo Preview — Not Approved")],
        ondelete={"demo_preview": "set default"},
    )

    @api.model
    def seed_iso9001_initial_implementation(self):
        if is_demo_2026_only_install(self.env):
            seed_iso9001_2026_implementation_pack(self.env)
            return True
        seed_iso9001_initial_implementation(self.env)
        seed_iso9001_transition_scenarios(self.env)
        seed_iso9001_2026_implementation_pack(self.env)
        return True

    def action_activate(self):
        if any(pack.code == ISO9001_2026_PACK_CODE for pack in self):
            raise UserError(
                "The ISO 9001:2026 pack is a review draft and cannot be activated "
                "until competent practitioner review and a separate approved release."
            )
        return super().action_activate()

    def action_enable_demo_preview(self):
        self.ensure_one()
        if not self.env.user.has_group("pm_qms_core.group_pm_qms_administrator"):
            raise AccessError("Only a QMS Administrator can enable the isolated Demo Preview.")
        if self.code != ISO9001_2026_PACK_CODE or self.state != "draft":
            raise UserError("Only the draft ISO 9001:2026 pack can enter Demo Preview.")
        if not is_authorized_demo_2026_preview(self.env):
            raise UserError("Demo Preview requires the licensed, isolated Demo2 environment.")
        if self.company_id != self.env.company or self.sudo().search_count([]) != 1:
            raise UserError("Demo Preview requires one pack in the isolated Demo2 company.")
        profiles = self.env["pm.qms.mapping.profile"].search([("pack_id", "=", self.id)])
        if not (
            len(self.area_ids) == 7
            and len(self.control_line_ids) == 38
            and len(profiles) == 1
            and profiles.edition == "2026"
            and profiles.state == "draft"
            and len(profiles.mapping_ids) == 65
            and all(mapping.review_status == "draft" for mapping in profiles.mapping_ids)
        ):
            raise UserError("The unreviewed 2026 pack inventory is not in the expected draft state.")
        self.with_context(pm_qms_pack_workflow=True).write({"state": "demo_preview"})
        self._log_qms_event(
            event_type="workflow",
            previous_state="draft",
            new_state="demo_preview",
            decision="Isolated Demo Preview enabled; content and mappings remain unapproved",
        )
        return True
