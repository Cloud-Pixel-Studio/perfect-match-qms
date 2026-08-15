{
    "name": "Perfect Match QMS Migration Tools",
    "summary": "Controlled document and evidence migration helpers for QMS onboarding",
    "description": """
Safe import helpers for customer onboarding. The addon validates company,
organization, process, document, control-instance, and evidence-requirement
relationships before creating migration records.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_evidence", "pm_qms_implementation"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/document_import_wizard_views.xml",
        "wizard/evidence_import_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "application": False,
    "installable": True,
}
