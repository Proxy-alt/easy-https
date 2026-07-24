"""Tests for Easy HTTPS diagnostics."""

import tempfile
import os
import pytest
from unittest.mock import MagicMock
from homeassistant.config_entries import ConfigEntry

from custom_components.easy_https.diagnostics import async_get_config_entry_diagnostics
from custom_components.easy_https.pki import PKIEngine


@pytest.mark.asyncio
async def test_diagnostics_redaction():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root_key_pem, root_cert_pem = PKIEngine.create_root_ca("SuperSecret123!")
        cert_path = os.path.join(tmp_dir, "cert.pem")
        with open(cert_path, "wb") as f:
            f.write(root_cert_pem)

        entry = MagicMock(spec=ConfigEntry)
        entry.title = "Easy HTTPS"
        entry.domain = "easy_https"
        entry.version = 1
        entry.data = {
            "root_password": "SuperSecret123!",
            "ha_ips": ["192.168.1.100"],
        }
        entry.options = {}

        hass = MagicMock()
        async def mock_executor(func, *args):
            return func(*args)
        hass.async_add_executor_job = mock_executor
        hass.data = {
            "easy_https": {
                "entry_id": {
                    "ssl_dir": tmp_dir,
                    "step_mgr": MagicMock(is_installed=lambda: False, process=None, standalone_site=None),
                }
            }
        }
        entry.entry_id = "entry_id"

        diag = await async_get_config_entry_diagnostics(hass, entry)

        # Verify root_password is redacted
        assert diag["entry"]["config"]["root_password"] == "**REDACTED**"
        assert diag["entry"]["title"] == "Easy HTTPS"
        assert "certificate_info" in diag

        print("\n[SUCCESS] Diagnostics redaction test passed!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_diagnostics_redaction())
