{
    "name": "Perfect Match QMS Internal Audit",
    "summary": "Internal audit program, planning, evidence, findings, and NCR integration",
    "description": """
Perfect Match QMS Internal Audit provides reusable operational audit records
for programs, audits, audit scope, criteria, plan lines, audit evidence,
findings, and structured nonconformity handoff to NCR and CAPA workflows.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_capa"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/audit_program_views.xml",
        "views/audit_views.xml",
        "views/audit_evidence_views.xml",
        "views/audit_finding_views.xml",
        "views/control_instance_views.xml",
        "views/process_views.xml",
        "views/nonconformity_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "application": False,
}
