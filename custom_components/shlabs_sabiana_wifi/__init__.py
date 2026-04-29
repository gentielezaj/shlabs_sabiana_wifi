"""The SHLabs Sabiana Wifi integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import SabianaApiClient
from .const import DOMAIN, PLATFORMS
from .coordinator import SabianaDataUpdateCoordinator

SabianaConfigEntry = ConfigEntry[SabianaDataUpdateCoordinator]

_IMAGES_PATH = Path(__file__).parent / "images"
_STATIC_URL = f"/{DOMAIN}/static"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register static assets for the integration."""
    hass.http.register_static_path(_STATIC_URL, str(_IMAGES_PATH), cache_headers=True)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SabianaConfigEntry) -> bool:
    """Set up SHLabs Sabiana Wifi from a config entry."""
    client = SabianaApiClient(hass, entry)
    coordinator = SabianaDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SabianaConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
