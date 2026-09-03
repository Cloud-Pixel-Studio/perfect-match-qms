{
    "name": "Perfect Match QMS Commercial Licensing",
    "summary": "Offline signed licenses and commercial entitlement capacity",
    "description": """
Perfect Match QMS Commercial Licensing provides local, signed offline license
verification and server-side capacity enforcement for operational companies,
sites, and named QMS users. It is intentionally separate from permissions and
scope, and it does not require continuous Internet access.
    """,
    "version": "19.0.1.0.3",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_core", "pm_qms_people"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/license_views.xml",
        "views/activation_request_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
}
