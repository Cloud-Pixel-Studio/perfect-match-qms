{
    "name": "Perfect Match QMS Implementation",
    "summary": "Framework packs, project generation, implementation controls, and readiness",
    "description": """
Perfect Match QMS Implementation provides the generic deployment engine for
versioned proprietary framework packs. It generates implementation projects,
deduplicates shared controls, creates Odoo execution tasks, and preserves
historical implementation readiness assessments.
    """,
    "version": "19.0.6.0.3",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_core", "pm_qms_evidence", "project"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/activity_views.xml",
        "views/framework_pack_views.xml",
        "views/implementation_project_views.xml",
        "views/implementation_control_views.xml",
        "views/readiness_assessment_views.xml",
        "views/readiness_center_views.xml",
        "views/project_task_views.xml",
        "wizard/project_generator_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "application": False,
}
