"""Easy HTTPS custom component for Home Assistant."""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Dict, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.components import persistent_notification
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError

from .const import DOMAIN, SERVICE_RENEW_CERTIFICATES
from .pki import PKIEngine
from .step_ca import StepCAManager
from .http_view import RootCADownloadView, RootCAPEMDownloadView

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.SWITCH]


@dataclass
class EasyHTTPSRuntimeData:
    """Runtime data container for Easy HTTPS."""

    ssl_dir: str
    fullchain_path: str
    privkey_path: str
    step_mgr: StepCAManager


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Easy HTTPS component integration."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Easy HTTPS from a config entry."""
    config_data = {**entry.data, **entry.options}
    root_password = config_data.get("root_password")
    ha_ips = config_data.get("ha_ips", [])
    enable_step_ca = config_data.get("enable_step_ca", False)
    additional_domains = config_data.get("additional_domains", [])

    if not root_password:
        raise ConfigEntryNotReady("Root CA password missing from configuration entry.")

    # Storage paths
    ssl_dir = hass.config.path("ssl", "easy_https")
    storage_dir = hass.config.path(".storage", "easy_https")

    os.makedirs(ssl_dir, exist_ok=True)
    os.makedirs(storage_dir, exist_ok=True)

    root_key_path = os.path.join(storage_dir, "root_ca_key.pem")
    root_cert_path = os.path.join(ssl_dir, "root_ca.pem")

    ha_inter_key_path = os.path.join(storage_dir, "ha_intermediate_key.pem")
    ha_inter_cert_path = os.path.join(storage_dir, "ha_intermediate.pem")

    sec_inter_key_path = os.path.join(storage_dir, "secondary_intermediate_key.pem")
    sec_inter_cert_path = os.path.join(storage_dir, "secondary_intermediate.pem")

    leaf_key_path = os.path.join(ssl_dir, "privkey.pem")
    leaf_cert_path = os.path.join(ssl_dir, "cert.pem")
    fullchain_path = os.path.join(ssl_dir, "fullchain.pem")

    def _generate_pki_chain():
        try:
            # 1. Root CA
            if not os.path.exists(root_key_path) or not os.path.exists(root_cert_path):
                _LOGGER.info("Generating Encrypted Root CA...")
                root_key_pem, root_cert_pem = PKIEngine.create_root_ca(root_password)
                with open(root_key_path, "wb") as f:
                    f.write(root_key_pem)
                with open(root_cert_path, "wb") as f:
                    f.write(root_cert_pem)
            else:
                with open(root_key_path, "rb") as f:
                    root_key_pem = f.read()
                with open(root_cert_path, "rb") as f:
                    root_cert_pem = f.read()

            # 2. Intermediate CA 1 (HA Intermediate)
            if not os.path.exists(ha_inter_key_path) or not os.path.exists(ha_inter_cert_path):
                _LOGGER.info("Generating HA Intermediate CA...")
                ha_inter_key_pem, ha_inter_cert_pem = PKIEngine.create_intermediate_ca(
                    name="Easy HTTPS HA Intermediate CA",
                    root_key_pem=root_key_pem,
                    root_key_password=root_password,
                    root_cert_pem=root_cert_pem,
                )
                with open(ha_inter_key_path, "wb") as f:
                    f.write(ha_inter_key_pem)
                with open(ha_inter_cert_path, "wb") as f:
                    f.write(ha_inter_cert_pem)
            else:
                with open(ha_inter_key_path, "rb") as f:
                    ha_inter_key_pem = f.read()
                with open(ha_inter_cert_path, "rb") as f:
                    ha_inter_cert_pem = f.read()

            # 3. Intermediate CA 2 (Secondary Intermediate for App/step-ca use)
            if not os.path.exists(sec_inter_key_path) or not os.path.exists(sec_inter_cert_path):
                _LOGGER.info("Generating Secondary Intermediate CA...")
                sec_inter_key_pem, sec_inter_cert_pem = PKIEngine.create_intermediate_ca(
                    name="Easy HTTPS Secondary Intermediate CA",
                    root_key_pem=root_key_pem,
                    root_key_password=root_password,
                    root_cert_pem=root_cert_pem,
                )
                with open(sec_inter_key_path, "wb") as f:
                    f.write(sec_inter_key_pem)
                with open(sec_inter_cert_path, "wb") as f:
                    f.write(sec_inter_cert_pem)

            # 4. HA Leaf Certificate
            _LOGGER.info("Generating Home Assistant Leaf Certificate for IPs: %s", ha_ips)
            leaf_key_pem, leaf_cert_pem, fullchain_pem = PKIEngine.create_leaf_certificate(
                intermediate_key_pem=ha_inter_key_pem,
                intermediate_cert_pem=ha_inter_cert_pem,
                ip_addresses=ha_ips,
                additional_domains=additional_domains,
            )

            with open(leaf_key_path, "wb") as f:
                f.write(leaf_key_pem)
            with open(leaf_cert_path, "wb") as f:
                f.write(leaf_cert_pem)
            with open(fullchain_path, "wb") as f:
                f.write(fullchain_pem)
        except Exception as err:
            _LOGGER.error("Failed PKI chain generation: %s", err)
            raise

    try:
        await hass.async_add_executor_job(_generate_pki_chain)
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to generate PKI certificates: {err}") from err

    # Register HTTP views for direct 1-click Root CA download
    hass.http.register_view(RootCADownloadView(root_cert_path))
    hass.http.register_view(RootCAPEMDownloadView(root_cert_path))

    # Send HA Persistent Notification
    primary_ip = ha_ips[0] if ha_ips else "YOUR_HA_IP"
    download_url = f"http://{primary_ip}:8123/api/easy_https/root_ca.crt"

    notification_msg = (
        f"🔒 **Easy HTTPS Setup Complete!**\n\n"
        f"1. **Trust Root Certificate**: [Click to Download Root CA]({download_url}) "
        f"and install it on your iOS, Android, or PC/Mac to trust Home Assistant HTTPS without warnings.\n\n"
        f"2. **Enable HTTPS in Home Assistant**: Add the following to your `configuration.yaml`:\n"
        f"```yaml\n"
        f"http:\n"
        f"  ssl_certificate: {fullchain_path}\n"
        f"  ssl_key: {leaf_key_path}\n"
        f"```\n\n"
        f"3. **Allowed Access Hosts/IPs**: Certificate is valid for `homeassistant`, `homeassistant.local`, `127.0.0.1`, and `{', '.join(ha_ips)}`."
    )

    persistent_notification.async_create(
        hass,
        notification_msg,
        title="Easy HTTPS Setup Complete",
        notification_id="easy_https_setup",
    )

    # step-ca setup
    step_ca_dir = os.path.join(storage_dir, "step_ca")
    step_mgr = StepCAManager(config_dir=step_ca_dir)

    if enable_step_ca:
        config_path = step_mgr.prepare_config(
            intermediate_cert_path=sec_inter_cert_path,
            intermediate_key_path=sec_inter_key_path,
            root_cert_path=root_cert_path,
        )
        await step_mgr.async_start(
            config_path,
            intermediate_cert_path=sec_inter_cert_path,
            intermediate_key_path=sec_inter_key_path,
        )

    runtime_data = EasyHTTPSRuntimeData(
        ssl_dir=ssl_dir,
        fullchain_path=fullchain_path,
        privkey_path=leaf_key_path,
        step_mgr=step_mgr,
    )
    entry.runtime_data = runtime_data
    hass.data[DOMAIN][entry.entry_id] = runtime_data

    # Register platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Idempotent service registration
    if not hass.services.has_service(DOMAIN, SERVICE_RENEW_CERTIFICATES):
        async def async_renew_certificates(call: ServiceCall) -> None:
            """Service to manually renew leaf certificates."""
            try:
                await hass.async_add_executor_job(_generate_pki_chain)
                _LOGGER.info("Easy HTTPS certificates successfully renewed.")
            except Exception as err:
                raise ServiceValidationError(f"Certificate renewal failed: {err}") from err

        hass.services.async_register(DOMAIN, SERVICE_RENEW_CERTIFICATES, async_renew_certificates)

    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime_data: EasyHTTPSRuntimeData = getattr(entry, "runtime_data", None) or hass.data[DOMAIN].get(entry.entry_id)
        if runtime_data and runtime_data.step_mgr:
            await runtime_data.step_mgr.async_stop()

        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Unregister service if last entry unloaded
        if not hass.data[DOMAIN] and hass.services.has_service(DOMAIN, SERVICE_RENEW_CERTIFICATES):
            hass.services.async_remove(DOMAIN, SERVICE_RENEW_CERTIFICATES)

    return unload_ok
