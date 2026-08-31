{
    "name": "Perfect Match QMS ISO 9001 Standard Add-on",
    "summary": "ISO 9001 profile metadata and customer navigation for Perfect Match QMS",
    "description": """
This add-on contains the ISO 9001 standard profile boundary for Perfect Match
QMS. The generic QMS foundation and the proprietary PM-QMS-QUALITY framework
pack remain usable without this add-on. Only reference identifiers and
Perfect Match-authored metadata belong here; official standard text is never
copied into the product.
    """,
    "version": "19.0.8.0.1",
    "category": "Operations/Quality",
    "author": "Perfect Match Investments LLC",
    "website": "https://cloudpixelstudio.agency",
    "license": "Other proprietary",
    "depends": ["pm_qms_pack_quality"],
    "data": [
        "data/initial_implementation_data.xml",
        "views/iso9001_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "application": False,
    "installable": True,
}
