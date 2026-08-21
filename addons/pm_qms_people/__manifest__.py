{
    "name": "Perfect Match QMS People, Training and Competency",
    "summary": "QMS people, roles, competencies, training, qualifications, and document acknowledgments",
    "description": """
Perfect Match QMS People adds a reusable people and competency capability for
QMS operations without requiring a full HR implementation. It links QMS people
to contacts and optional Odoo users, manages QMS roles, competency requirements,
training records, qualifications, and revision-specific controlled-document
acknowledgments.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_documents", "pm_qms_evidence"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/person_views.xml",
        "views/role_views.xml",
        "views/competency_views.xml",
        "views/training_views.xml",
        "views/qualification_views.xml",
        "views/acknowledgment_views.xml",
        "views/document_revision_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [
        "demo/demo_data.xml",
    ],
    "application": False,
    "installable": True,
}
