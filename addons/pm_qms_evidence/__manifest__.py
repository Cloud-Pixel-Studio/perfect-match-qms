{
    "name": "Perfect Match QMS Evidence",
    "summary": "Actual evidence records and review workflow for QMS implementations",
    "description": """
Evidence records for client-specific Perfect Match QMS control instances,
including submission, review, acceptance, rejection, and evidence completion
foundation metrics.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_core", "pm_qms_documents"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/evidence_views.xml",
        "views/control_instance_views.xml",
        "views/document_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "application": False,
    "installable": True,
}
