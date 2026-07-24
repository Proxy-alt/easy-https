"""Config flow for Easy HTTPS integration."""

import ipaddress
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

_LOGGER = logging.getLogger(__name__)

DOMAIN = "easy_https"


class EasyHTTPSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Easy HTTPS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle initial setup step."""
        errors: Dict[str, str] = {}

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            password = user_input.get("root_password", "")
            ha_ips_raw = user_input.get("ha_ips", "")
            enable_step_ca = user_input.get("enable_step_ca", False)
            additional_domains_raw = user_input.get("additional_domains", "")

            # Validate password
            if len(password) < 8:
                errors["root_password"] = "invalid_password"

            # Validate IP addresses
            ip_list = [ip.strip() for ip in ha_ips_raw.split(",") if ip.strip()]
            for ip_str in ip_list:
                try:
                    ipaddress.ip_address(ip_str)
                except ValueError:
                    errors["ha_ips"] = "invalid_ip"
                    break

            if not errors:
                domains_list = [d.strip() for d in additional_domains_raw.split(",") if d.strip()]
                return self.async_create_entry(
                    title="Easy HTTPS",
                    data={
                        "root_password": password,
                        "ha_ips": ip_list,
                        "enable_step_ca": enable_step_ca,
                        "additional_domains": domains_list,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required("root_password"): str,
                vol.Required("ha_ips", default="192.168.1.100"): str,
                vol.Optional("enable_step_ca", default=False): bool,
                vol.Optional("additional_domains", default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return EasyHTTPSOptionsFlowHandler(config_entry)


class EasyHTTPSOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for updating configuration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage options."""
        errors: Dict[str, str] = {}
        current_data = {**self._config_entry.data, **self._config_entry.options}

        if user_input is not None:
            ha_ips_raw = user_input.get("ha_ips", "")
            enable_step_ca = user_input.get("enable_step_ca", False)
            additional_domains_raw = user_input.get("additional_domains", "")

            ip_list = [ip.strip() for ip in ha_ips_raw.split(",") if ip.strip()]
            for ip_str in ip_list:
                try:
                    ipaddress.ip_address(ip_str)
                except ValueError:
                    errors["ha_ips"] = "invalid_ip"
                    break

            if not errors:
                domains_list = [d.strip() for d in additional_domains_raw.split(",") if d.strip()]
                return self.async_create_entry(
                    title="",
                    data={
                        "ha_ips": ip_list,
                        "enable_step_ca": enable_step_ca,
                        "additional_domains": domains_list,
                    },
                )

        default_ips = ", ".join(current_data.get("ha_ips", []))
        default_domains = ", ".join(current_data.get("additional_domains", []))

        schema = vol.Schema(
            {
                vol.Required("ha_ips", default=default_ips): str,
                vol.Optional("enable_step_ca", default=current_data.get("enable_step_ca", False)): bool,
                vol.Optional("additional_domains", default=default_domains): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
