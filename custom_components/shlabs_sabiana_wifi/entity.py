"""Shared entity helpers for SHLabs Sabiana Wifi."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ENTITY_PICTURE_URL, MANUFACTURER
from .coordinator import SabianaDataUpdateCoordinator

# Keys into the parsed lastData dict (from SabianaCloudWM.parse)
LAST_DATA_POWER_BYTE = "is_on"
LAST_DATA_MODE_BYTE = "mode"
LAST_DATA_ACTION_BYTE = "power_status"
LAST_DATA_FAN_STATUS_BYTE = "fan_setpoint"
LAST_DATA_NIGHT_MODE_BYTE = "night_mode"
LAST_DATA_CURRENT_TEMP_BYTE = "room_temp"
LAST_DATA_TARGET_TEMP_BYTE = "target_temp"
LAST_DATA_SECONDARY_TARGET_TEMP_BYTE = "target_temp"
LAST_DATA_WATER_TEMP_BYTE = "water_temp"
LAST_DATA_LIMIT_TEMP_BYTE = "water_temp"


def parse_temperature(data: dict[str, Any] | None, key: str) -> float | None:
    """Return a temperature value from the parsed lastData dict."""
    if not data:
        return None
    value = data.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class SabianaCoordinatorEntity(CoordinatorEntity[SabianaDataUpdateCoordinator]):
    """Base entity for Sabiana devices."""

    _attr_entity_picture = ENTITY_PICTURE_URL
    def __init__(self, coordinator: SabianaDataUpdateCoordinator, device_id: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        device = self.coordinator.data.devices[self._device_id]
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=MANUFACTURER,
            name=device.name,
            model="Cloud WM Fan Coil",
            sw_version=str(device.payload.get("deviceStateFw") or "unknown"),
        )

    @property
    def _device_payload(self) -> dict[str, Any]:
        """Return raw payload for this entity."""
        return self.coordinator.data.devices[self._device_id].payload

    @property
    def _last_data(self) -> dict[str, Any]:
        """Return normalized status data."""
        return self.coordinator.data.devices[self._device_id].lastData

