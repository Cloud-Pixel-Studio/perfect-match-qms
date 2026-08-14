{
    "name": "Perfect Match QMS NCR",
    "summary": "Nonconformity management for Perfect Match Digital QMS",
    "description": """
Perfect Match QMS NCR manages detected nonconformities and deviations with
containment, investigation, disposition, controlled closure, and operational
links to control implementations, documents, evidence, and risks.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_evidence", "pm_qms_risk"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/nonconformity_views.xml",
        "views/control_instance_views.xml",
        "views/risk_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "application": False,
}
