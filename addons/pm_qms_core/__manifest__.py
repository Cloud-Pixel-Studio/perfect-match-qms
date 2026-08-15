{
    "name": "Perfect Match QMS Core Services",
    "summary": "Core proprietary QMS entities for Perfect Match Digital QMS",
    "description": """
Perfect Match QMS Core defines the foundational proprietary QMS objects for
Perfect Match Digital QMS: organizations, processes, controls, implementation
activities, evidence requirements, and reference-only external mappings.
It also defines client control instances that keep implementation status
separate from reusable framework controls.
    """,
    "version": "19.0.4.0.0",
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
        "views/control_instance_views.xml",
        "views/activity_views.xml",
        "views/evidence_views.xml",
        "views/external_mapping_views.xml",
        "views/event_views.xml",
        "views/menu_views.xml",
    ],
    "application": False,
    "installable": True,
}
