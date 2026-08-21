{
    "name": "Perfect Match QMS Calibration",
    "summary": "Monitoring resource, calibration, verification, and out-of-tolerance control",
    "description": """
Perfect Match QMS Calibration controls monitoring and measuring resources,
calibration/verification records, out-of-tolerance impact assessments, and
related QMS links without becoming a CMMS, LIMS, inventory, or maintenance app.
""",
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match",
    "depends": [
        "pm_qms_people",
        "pm_qms_capa",
        "pm_qms_management_review",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/equipment_views.xml",
        "views/calibration_event_views.xml",
        "views/impact_assessment_views.xml",
        "views/provider_views.xml",
        "views/equipment_type_views.xml",
        "views/evidence_views.xml",
        "views/nonconformity_views.xml",
        "views/capa_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
