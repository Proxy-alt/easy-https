"""Sensor platform for Easy HTTPS integration."""

import datetime
import os
import logging
from typing import Optional, Dict, Any

from cryptography import x509

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_EXPIRATION_DATE,
    ATTR_DAYS_REMAINING,
    ATTR_ISSUER,
    ATTR_SUBJECT,
    ATTR_SANS,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Easy HTTPS sensors from config entry."""
    runtime_data = getattr(entry, "runtime_data", None) or hass.data[DOMAIN].get(entry.entry_id, {})
    ssl_dir = runtime_data.get("ssl_dir")

    if not ssl_dir:
        return

    cert_path = os.path.join(ssl_dir, "cert.pem")
    root_cert_path = os.path.join(ssl_dir, "root_ca.pem")

    entities = [
        EasyHTTPSCertExpirationSensor(
            entry=entry,
            cert_path=cert_path,
            name="HA Leaf Certificate Expiration",
            unique_id_suffix="ha_leaf_cert_expiration",
        ),
        EasyHTTPSCertExpirationSensor(
            entry=entry,
            cert_path=root_cert_path,
            name="Root CA Expiration",
            unique_id_suffix="root_ca_expiration",
        ),
    ]

    async_add_entities(entities, update_before_add=True)


class EasyHTTPSCertExpirationSensor(SensorEntity):
    """Sensor reporting certificate expiration days remaining."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "days"
    _attr_icon = "mdi:certificate"

    def __init__(
        self,
        entry: ConfigEntry,
        cert_path: str,
        name: str,
        unique_id_suffix: str,
    ) -> None:
        self.entry = entry
        self.cert_path = cert_path
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_id_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Easy HTTPS Certificate Authority",
            manufacturer="Easy HTTPS",
            model="Local Certificate Authority",
            sw_version="1.0.0",
        )
        self._attr_extra_state_attributes: Dict[str, Any] = {}

    async def async_update(self) -> None:
        """Fetch certificate state and update days remaining."""
        if not os.path.exists(self.cert_path):
            self._attr_available = False
            return

        def _read_cert():
            with open(self.cert_path, "rb") as f:
                return x509.load_pem_x509_certificate(f.read())

        try:
            cert = await self.hass.async_add_executor_job(_read_cert)
            now = datetime.datetime.now(datetime.timezone.utc)
            expiry = cert.not_valid_after_utc
            days_left = (expiry - now).days

            self._attr_native_value = max(0, days_left)
            self._attr_available = True

            sans = []
            try:
                san_ext = cert.extensions.get_extension_for_oid(x509.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                sans = [str(name.value) for name in san_ext.value]
            except Exception:
                pass

            self._attr_extra_state_attributes = {
                ATTR_EXPIRATION_DATE: expiry.isoformat(),
                ATTR_DAYS_REMAINING: days_left,
                ATTR_ISSUER: str(cert.issuer),
                ATTR_SUBJECT: str(cert.subject),
                ATTR_SANS: sans,
            }
        except Exception as err:
            _LOGGER.error("Failed to parse certificate at %s: %s", self.cert_path, err)
            self._attr_available = False
