{
    "name": "Perfect Match QMS KPI",
    "summary": "Objectives, KPI measurements, and customer/supplier performance for Perfect Match Digital QMS",
    "description": """
Perfect Match QMS KPI manages client objectives, KPI definitions, historical
measurements, customer performance, customer satisfaction, supplier performance,
and supplier evaluations. It reuses Odoo partners for customer and supplier
master data and preserves historical target snapshots for performance results.
    """,
    "version": "19.0.1.0.0",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_ncr"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "views/objective_views.xml",
        "views/kpi_views.xml",
        "views/kpi_measurement_views.xml",
        "views/customer_performance_views.xml",
        "views/customer_satisfaction_views.xml",
        "views/supplier_performance_views.xml",
        "views/supplier_evaluation_views.xml",
        "views/control_instance_views.xml",
        "views/process_views.xml",
        "views/menu_views.xml",
    ],
    "demo": ["demo/demo_data.xml"],
    "installable": True,
    "application": False,
}
