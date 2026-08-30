{
    "name": "Perfect Match QMS CAPA",
    "summary": "Corrective and preventive action management for Perfect Match Digital QMS",
    "description": """
Perfect Match QMS CAPA manages corrective and preventive action lifecycles,
root cause analysis, action plans, implementation, effectiveness review, and
structured source relationships to NCRs and risks.
    """,
    "version": "19.0.1.1.2",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_ncr"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/capa_views.xml",
        "views/capa_action_views.xml",
        "views/control_instance_views.xml",
        "views/nonconformity_views.xml",
        "views/risk_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "application": False,
}
