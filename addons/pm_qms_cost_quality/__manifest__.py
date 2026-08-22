{
    "name": "Perfect Match QMS Cost of Quality",
    "summary": "Cost of Quality events, COPQ classification, analytics, and review inputs",
    "description": """
Perfect Match QMS Cost of Quality captures non-accounting quality cost events
with controlled categories, source traceability, and management review snapshots.
""",
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match",
    "depends": [
        "pm_qms_core",
        "pm_qms_ncr",
        "pm_qms_capa",
        "pm_qms_audit",
        "pm_qms_management_review",
        "pm_qms_calibration",
        "pm_qms_customer_quality",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "data/sequence_data.xml",
        "data/cost_type_data.xml",
        "views/cost_quality_views.xml",
        "views/dashboard_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "license": "LGPL-3",
}
