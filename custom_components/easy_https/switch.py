"""Switch platform for Easy HTTPS step-ca server control."""

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .step_ca import StepCAManager

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Easy HTTPS switch from config entry."""
    runtime_data = getattr(entry, "runtime_data", None) or hass.data[DOMAIN].get(entry.entry_id, {})
    step_mgr: StepCAManager = runtime_data.get("step_mgr")

    if step_mgr:
        async_add_entities([EasyHTTPSStepCASwitch(entry, step_mgr)], update_before_add=True)


class EasyHTTPSStepCASwitch(SwitchEntity):
    """Switch entity to enable or disable step-ca background server."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_name = "step-ca Server"
    _attr_icon = "mdi:server-security"

    def __init__(self, entry: ConfigEntry, step_mgr: StepCAManager) -> None:
        self.entry = entry
        self.step_mgr = step_mgr
        self._attr_unique_id = f"{entry.entry_id}_step_ca_switch"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Easy HTTPS Certificate Authority",
            manufacturer="Easy HTTPS",
            model="Local Certificate Authority",
            sw_version="1.0.0",
        )

    @property
    def is_on(self) -> bool:
        """Return True if step-ca server is currently running."""
        return bool(self.step_mgr.process or self.step_mgr.standalone_site)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn step-ca server on."""
        ssl_dir = self.hass.config.path("ssl", "easy_https")
        storage_dir = self.hass.config.path(".storage", "easy_https")
        sec_inter_cert_path = f"{storage_dir}/secondary_intermediate.pem"
        sec_inter_key_path = f"{storage_dir}/secondary_intermediate_key.pem"
        root_cert_path = f"{ssl_dir}/root_ca.pem"

        config_path = self.step_mgr.prepare_config(
            intermediate_cert_path=sec_inter_cert_path,
            intermediate_key_path=sec_inter_key_path,
            root_cert_path=root_cert_path,
        )
        await self.step_mgr.async_start(
            config_path,
            intermediate_cert_path=sec_inter_cert_path,
            intermediate_key_path=sec_inter_key_path,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn step-ca server off."""
        await self.step_mgr.async_stop()
        self.async_write_ha_state()
