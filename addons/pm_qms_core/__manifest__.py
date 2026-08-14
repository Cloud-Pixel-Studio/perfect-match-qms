{
    "name": "Perfect Match QMS Core",
    "summary": "Core proprietary QMS entities for Perfect Match Digital QMS",
    "description": """
Perfect Match QMS Core defines the foundational proprietary QMS objects for
Perfect Match Digital QMS: organizations, processes, controls, implementation
activities, evidence requirements, and reference-only external mappings.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["base", "mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/process_views.xml",
        "views/control_views.xml",
        "views/activity_views.xml",
        "views/evidence_views.xml",
        "views/external_mapping_views.xml",
        "views/menu_views.xml",
    ],
    "application": True,
    "installable": True,
}
