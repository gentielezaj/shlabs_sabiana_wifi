"""The SHLabs Sabiana Wifi integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import SabianaApiClient
from .const import DOMAIN, PLATFORMS
from .coordinator import SabianaDataUpdateCoordinator

SabianaConfigEntry = ConfigEntry[SabianaDataUpdateCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the SHLabs Sabiana Wifi integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SabianaConfigEntry) -> bool:
    """Set up SHLabs Sabiana Wifi from a config entry."""
    client = SabianaApiClient(hass, entry)
    coordinator = SabianaDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await coordinator.async_start_websocket()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SabianaConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.async_stop_websocket()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
