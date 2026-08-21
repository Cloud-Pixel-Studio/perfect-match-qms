{
    "name": "Perfect Match QMS",
    "summary": "Unified Perfect Match QMS application shell and executive dashboard",
    "description": """
Perfect Match QMS provides the customer-facing application shell, dashboard,
and unified navigation for the reusable Perfect Match Digital QMS product.
Technical addons remain modular underneath this product entry point.
""",
    "version": "19.0.1.1.0",
    "category": "Operations/Quality",
    "author": "Perfect Match",
    "depends": [
        "pm_qms_core",
        "pm_qms_documents",
        "pm_qms_people",
        "pm_qms_evidence",
        "pm_qms_risk",
        "pm_qms_ncr",
        "pm_qms_capa",
        "pm_qms_audit",
        "pm_qms_kpi",
        "pm_qms_management_review",
        "pm_qms_implementation",
        "pm_qms_pack_quality",
        "pm_qms_migration",
        "pm_qms_calibration",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/dashboard_views.xml",
        "views/implementation_project_views.xml",
        "views/menu_views.xml",
    ],
    "application": True,
    "installable": True,
    "license": "LGPL-3",
}
