"""HTTP View to easily download and install Root CA certificate."""

import os
import logging
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class RootCADownloadView(HomeAssistantView):
    """View to serve Root CA certificate for easy mobile and desktop installation."""

    url = "/api/easy_https/root_ca.crt"
    name = "api:easy_https:root_ca"
    requires_auth = False  # Publicly accessible on local network so devices can download during setup

    def __init__(self, root_cert_path: str):
        self.root_cert_path = root_cert_path

    async def get(self, request: web.Request) -> web.Response:
        """Handle Root CA certificate download request."""
        if not os.path.exists(self.root_cert_path):
            return web.Response(status=404, text="Root CA certificate not found.")

        with open(self.root_cert_path, "rb") as f:
            cert_bytes = f.read()

        # application/x-x509-ca-cert triggers auto-install prompt on iOS, Android, macOS, and Windows
        return web.Response(
            body=cert_bytes,
            content_type="application/x-x509-ca-cert",
            headers={
                "Content-Disposition": 'attachment; filename="Easy_HTTPS_Root_CA.crt"',
                "Cache-Control": "no-cache",
            },
        )


class RootCAPEMDownloadView(HomeAssistantView):
    """View to serve Root CA PEM format."""

    url = "/api/easy_https/root_ca.pem"
    name = "api:easy_https:root_ca_pem"
    requires_auth = False

    def __init__(self, root_cert_path: str):
        self.root_cert_path = root_cert_path

    async def get(self, request: web.Request) -> web.Response:
        """Handle Root CA PEM download request."""
        if not os.path.exists(self.root_cert_path):
            return web.Response(status=404, text="Root CA certificate not found.")

        with open(self.root_cert_path, "rb") as f:
            cert_bytes = f.read()

        return web.Response(
            body=cert_bytes,
            content_type="application/x-pem-file",
            headers={
                "Content-Disposition": 'attachment; filename="Easy_HTTPS_Root_CA.pem"',
                "Cache-Control": "no-cache",
            },
        )
