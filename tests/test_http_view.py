"""Tests for RootCADownloadView in Easy HTTPS component."""

import tempfile
import os
import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from custom_components.easy_https.http_view import RootCADownloadView, RootCAPEMDownloadView


@pytest.mark.asyncio
async def test_root_ca_download_view():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cert_path = os.path.join(tmp_dir, "root_ca.crt")
        dummy_content = b"-----BEGIN CERTIFICATE-----\nTEST_CERT\n-----END CERTIFICATE-----"
        with open(cert_path, "wb") as f:
            f.write(dummy_content)

        app = web.Application()
        view = RootCADownloadView(cert_path)
        app.router.add_get(view.url, view.get)

        client = TestClient(TestServer(app))
        await client.start_server()

        resp = await client.get("/api/easy_https/root_ca.crt")
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "application/x-x509-ca-cert"
        body = await resp.read()
        assert body == dummy_content

        await client.close()
        print("\n[SUCCESS] Root CA download view test passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_root_ca_download_view())
