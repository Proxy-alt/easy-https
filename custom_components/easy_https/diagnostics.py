"""Diagnostics support for Easy HTTPS integration."""

from typing import Any, Dict
from cryptography import x509

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_ROOT_PASSWORD, DOMAIN

TO_REDACT = {CONF_ROOT_PASSWORD, "password", "secret", "private_key"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> Dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime_data = getattr(entry, "runtime_data", None) or hass.data[DOMAIN].get(entry.entry_id)

    ssl_dir = runtime_data.ssl_dir if runtime_data else None
    cert_info = {}

    if ssl_dir:
        cert_path = f"{ssl_dir}/cert.pem"
        if cert_path and hasattr(hass, "async_add_executor_job"):
            def _parse_cert():
                try:
                    with open(cert_path, "rb") as f:
                        cert = x509.load_pem_x509_certificate(f.read())
                    return {
                        "subject": str(cert.subject),
                        "issuer": str(cert.issuer),
                        "not_valid_after_utc": cert.not_valid_after_utc.isoformat(),
                        "not_valid_before_utc": cert.not_valid_before_utc.isoformat(),
                        "serial_number": cert.serial_number,
                    }
                except Exception as err:
                    return {"error": str(err)}

            cert_info = await hass.async_add_executor_job(_parse_cert)

    step_mgr = runtime_data.step_mgr if runtime_data else None
    step_ca_status = {
        "installed": step_mgr.is_installed() if step_mgr else False,
        "running": bool(step_mgr and step_mgr.is_running),
    }

    raw_config = {**entry.data, **entry.options}
    clean_config = async_redact_data(raw_config, TO_REDACT)

    return {
        "entry": {
            "title": entry.title,
            "domain": entry.domain,
            "version": entry.version,
            "config": clean_config,
        },
        "certificate_info": cert_info,
        "step_ca_status": step_ca_status,
    }
