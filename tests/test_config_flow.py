"""Tests for Easy HTTPS config flow and options flow."""

import pytest
from unittest.mock import MagicMock
from homeassistant import config_entries, data_entry_flow
from custom_components.easy_https.config_flow import EasyHTTPSConfigFlow, EasyHTTPSOptionsFlowHandler


@pytest.mark.asyncio
async def test_config_flow_user_step_success():
    flow = EasyHTTPSConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])

    # Show initial form
    result = await flow.async_step_user()
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    # Submit valid user input
    user_input = {
        "root_password": "SuperSecretPassword123!",
        "ha_ips": "192.168.1.100, 10.0.0.5",
        "enable_step_ca": True,
        "additional_domains": "myha.local",
    }
    result2 = await flow.async_step_user(user_input)
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Easy HTTPS"
    assert result2["data"]["root_password"] == "SuperSecretPassword123!"
    assert result2["data"]["ha_ips"] == ["192.168.1.100", "10.0.0.5"]
    assert result2["data"]["enable_step_ca"] is True


@pytest.mark.asyncio
async def test_config_flow_user_step_validation_errors():
    flow = EasyHTTPSConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])

    # Password too short
    result = await flow.async_step_user({
        "root_password": "short",
        "ha_ips": "192.168.1.100",
    })
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]["root_password"] == "invalid_password"

    # Invalid IP address
    result2 = await flow.async_step_user({
        "root_password": "ValidPassword123!",
        "ha_ips": "not-an-ip-address",
    })
    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"]["ha_ips"] == "invalid_ip"


@pytest.mark.asyncio
async def test_options_flow():
    entry = MagicMock(spec=config_entries.ConfigEntry)
    entry.data = {
        "root_password": "ValidPassword123!",
        "ha_ips": ["192.168.1.100"],
        "enable_step_ca": False,
    }
    entry.options = {}

    options_flow = EasyHTTPSOptionsFlowHandler(entry)
    options_flow.hass = MagicMock()

    result = await options_flow.async_step_init()
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result2 = await options_flow.async_step_init({
        "ha_ips": "192.168.1.200",
        "enable_step_ca": True,
        "additional_domains": "newdomain.local",
    })
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"]["ha_ips"] == ["192.168.1.200"]
    assert result2["data"]["enable_step_ca"] is True


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_config_flow_user_step_success())
    asyncio.run(test_config_flow_user_step_validation_errors())
    asyncio.run(test_options_flow())
    print("\n[SUCCESS] Config flow tests passed!")
