from odoo.exceptions import UserError


PROFILE_CODE = "PM-QMS-QUALITY-ISO9001"
PROFILE_EDITION = "2015"


def post_init_hook(env):
    company = env.ref("base.main_company")
    pack = env["pm.qms.framework.pack"].search(
        [
            ("code", "=", "PM-QMS-QUALITY"),
            ("version", "=", "1.0"),
            ("company_id", "=", company.id),
        ],
        limit=1,
    )
    if not pack:
        raise UserError("The PM-QMS-QUALITY framework pack is required before ISO 9001 can be installed.")

    profiles = env["pm.qms.mapping.profile"].search(
        [("code", "=", PROFILE_CODE), ("company_id", "=", company.id)]
    )
    profile = profiles.filtered(lambda item: item.edition == PROFILE_EDITION)[:1]
    if not profile:
        if profiles:
            raise UserError(
                "An ISO 9001 mapping profile already uses this code with another edition; "
                "refusing to overwrite or invent a replacement."
            )
        profile = env["pm.qms.mapping.profile"].with_context(module=True).create(
            {
                "name": "ISO 9001 Current Published Edition Mapping",
                "code": PROFILE_CODE,
                "company_id": company.id,
                "pack_id": pack.id,
                "standard_name": "ISO 9001",
                "edition": PROFILE_EDITION,
                "publisher": "ISO",
                "notes": (
                    "External standard references are provided for implementation traceability. "
                    "This software does not include or replace the official publication. "
                    "Organizations remain responsible for authorized copies of applicable standards."
                ),
            }
        )
    if profile.state == "draft":
        profile.with_context(module=True).action_activate()
