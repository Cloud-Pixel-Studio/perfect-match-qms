{
    "name": "Perfect Match QMS Documents",
    "summary": "Controlled document and revision management for Perfect Match Digital QMS",
    "description": """
Controlled document identity, revision history, approval workflow, and
attachment linkage for Perfect Match Digital QMS client implementations.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_core"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/document_views.xml",
        "views/document_revision_views.xml",
        "views/control_instance_views.xml",
        "views/menu_views.xml",
    ],
    "application": False,
    "installable": True,
}
