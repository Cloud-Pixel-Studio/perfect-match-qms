{
    "name": "Perfect Match QMS Action Center",
    "summary": "Unified read-only action center across Perfect Match QMS sources",
    "description": """
Perfect Match QMS Action Center presents due, overdue, and open work from
authoritative QMS source records without becoming an action system of record.
""",
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match",
    "depends": [
        "pm_qms_core",
        "pm_qms_people",
        "pm_qms_risk",
        "pm_qms_ncr",
        "pm_qms_capa",
        "pm_qms_audit",
        "pm_qms_management_review",
        "pm_qms_calibration",
        "pm_qms_customer_quality",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/action_center_views.xml",
        "views/dashboard_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "license": "LGPL-3",
}
