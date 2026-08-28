{
    "name": "Perfect Match Quality Management Pack",
    "summary": "Proprietary Perfect Match quality controls and external mapping metadata",
    "description": """
Perfect Match Quality Management Pack provides the first commercial proprietary
quality-management control library, implementation activities, evidence
requirements, framework pack composition, and external reference mapping
metadata workflow. External mappings are reference metadata only and do not
include or replace official standard publications.
    """,
    "version": "19.0.3.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_core", "pm_qms_implementation"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/quality_guided_readiness_data.xml",
        "views/control_views.xml",
        "views/external_mapping_views.xml",
        "views/mapping_profile_views.xml",
        "wizard/mapping_import_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}
