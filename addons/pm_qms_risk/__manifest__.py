{
    "name": "Perfect Match QMS Risk",
    "summary": "Risk and opportunity management for Perfect Match Digital QMS",
    "description": """
Perfect Match QMS Risk manages client operational risks and opportunities,
including scoring, response tracking, controlled workflow history, and links to
control implementations and controlled documents.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_documents"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/risk_views.xml",
        "views/control_instance_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "application": False,
}
