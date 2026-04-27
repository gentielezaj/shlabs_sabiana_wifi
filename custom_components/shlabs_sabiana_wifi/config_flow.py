"""Config flow for SHLabs Sabiana Wifi."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .api import SabianaApiClient, SabianaApiError, SabianaAuthError
from .const import CONF_BASE_URL, DEFAULT_BASE_URL, DEFAULT_NAME, DOMAIN


class SabianaCloudWmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SHLabs Sabiana Wifi."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_BASE_URL]}::{user_input[CONF_USERNAME]}".lower())
            self._abort_if_unique_id_configured()

            entry = type("FlowConfigEntry", (), {"data": user_input})()
            client = SabianaApiClient(self.hass, entry)

            try:
                await client.async_login()
            except SabianaAuthError:
                errors["base"] = "invalid_auth"
            except SabianaApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=DEFAULT_NAME, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
