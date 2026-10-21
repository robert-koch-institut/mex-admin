import reflex as rx
from reflex.components.radix import themes
from reflex.plugins.sitemap import SitemapPlugin

config = rx.Config(
    app_name="mex",
    disable_plugins=[SitemapPlugin],
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=themes.theme(
                accent_color="blue",
                has_background=False,
                appearance="light",
            ),
        ),
    ],
    frontend_compression_formats=[],
    frontend_port=8030,
    backend_port=8031,
    telemetry_enabled=False,
)
