from odoo.addons.web.controllers.webmanifest import WebManifest as OdooWebManifest


class WebManifest(OdooWebManifest):
    """Keep the customer application identity on supported web endpoints."""

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        manifest.update(
            {
                "name": "Perfect Match QMS",
                "short_name": "Perfect Match QMS",
                "background_color": "#10233f",
                "theme_color": "#10233f",
                "icons": [
                    {
                        "src": "/pm_qms_app/static/description/icon.svg",
                        "sizes": "any",
                        "type": "image/svg+xml",
                    }
                ],
            }
        )
        return manifest

    def _icon_path(self):
        return "pm_qms_app/static/description/icon.svg"
