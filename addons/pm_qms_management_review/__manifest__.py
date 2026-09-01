{
    "name": "Perfect Match QMS Management Review",
    "summary": "Management review snapshots, decisions, and actions for Perfect Match Digital QMS",
    "description": """
Perfect Match QMS Management Review consolidates operational QMS information
into controlled review records. It captures historical snapshots of objectives,
KPIs, customer and supplier performance, audits, risks, NCR, CAPA, previous
actions, decisions, and follow-up actions.
    """,
    "version": "19.0.1.0.3",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_audit", "pm_qms_kpi"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/management_review_views.xml",
        "views/management_review_input_views.xml",
        "views/management_review_decision_views.xml",
        "views/management_review_action_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "application": False,
}
