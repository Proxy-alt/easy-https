"""Button platform for Easy HTTPS integration."""

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SERVICE_RENEW_CERTIFICATES

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Easy HTTPS button from config entry."""
    async_add_entities([EasyHTTPSRenewButton(entry)], update_before_add=True)


class EasyHTTPSRenewButton(ButtonEntity):
    """Button entity to trigger certificate renewal."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "Renew Certificates"
    _attr_icon = "mdi:certificate-sync"

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_renew_certificates"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Easy HTTPS Certificate Authority",
            manufacturer="Easy HTTPS",
            model="Local Certificate Authority",
            sw_version="1.0.0",
        )

    async def async_press(self) -> None:
        """Handle button press to renew certificates."""
        _LOGGER.info("Renew Certificates button pressed.")
        await self.hass.services.async_call(
            DOMAIN,
            SERVICE_RENEW_CERTIFICATES,
            blocking=True,
        )
