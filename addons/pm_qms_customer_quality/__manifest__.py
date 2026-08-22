{
    "name": "Perfect Match QMS Customer Quality",
    "summary": "Customer complaints, 8D, supplier issues, and SCAR orchestration",
    "description": """
Perfect Match QMS Customer Quality controls complaint intake, immediate
containment, quality alerts, root-cause analysis, 8D cases, supplier issues, and
SCAR response workflow while reusing the authoritative NCR, CAPA, Evidence,
Documents, People, Performance, Dashboard, and Management Review engines.
""",
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match",
    "depends": [
        "pm_qms_app",
        "pm_qms_capa",
        "pm_qms_kpi",
        "pm_qms_management_review",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/customer_complaint_views.xml",
        "views/quality_alert_views.xml",
        "views/root_cause_views.xml",
        "views/eight_d_views.xml",
        "views/supplier_issue_views.xml",
        "views/scar_views.xml",
        "views/nonconformity_views.xml",
        "views/capa_views.xml",
        "views/dashboard_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
