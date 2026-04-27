"""Switch platform for SHLabs Sabiana Wifi."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import NIGHT_MODE_OFF_COMMAND, NIGHT_MODE_ON_COMMAND
from .entity import LAST_DATA_NIGHT_MODE_BYTE, SabianaCoordinatorEntity, byte_at


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sabiana night mode switches."""
    coordinator = entry.runtime_data
    async_add_entities(SabianaNightModeSwitch(coordinator, device_id) for device_id in coordinator.data.devices)


class SabianaNightModeSwitch(SabianaCoordinatorEntity, SwitchEntity):
    """Representation of the Sabiana night mode toggle."""

    _attr_has_entity_name = True
    _attr_name = "Night mode"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._device_id}_night_mode"

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self._device_id in self.coordinator.data.devices

    @property
    def is_on(self) -> bool:
        """Return whether night mode is enabled."""
        return byte_at(self._last_data, LAST_DATA_NIGHT_MODE_BYTE) == "02"

    async def async_turn_on(self, **kwargs) -> None:
        """Enable night mode."""
        await self.coordinator.client.async_send_command(self._device_id, NIGHT_MODE_ON_COMMAND)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable night mode."""
        await self.coordinator.client.async_send_command(self._device_id, NIGHT_MODE_OFF_COMMAND)
        await self.coordinator.async_request_refresh()
