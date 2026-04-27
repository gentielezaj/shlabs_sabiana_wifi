"""Shared entity helpers for SHLabs Sabiana Wifi."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SabianaDataUpdateCoordinator

LAST_DATA_POWER_BYTE = 7
LAST_DATA_MODE_BYTE = 7
LAST_DATA_ACTION_BYTE = 8
LAST_DATA_CURRENT_TEMP_BYTE = 12
LAST_DATA_TARGET_TEMP_BYTE = 14
LAST_DATA_SECONDARY_TARGET_TEMP_BYTE = 16
LAST_DATA_WATER_TEMP_BYTE = 18
LAST_DATA_LIMIT_TEMP_BYTE = 19
LAST_DATA_FAN_STATUS_BYTE = 23
LAST_DATA_NIGHT_MODE_BYTE = 10


class SabianaCoordinatorEntity(CoordinatorEntity[SabianaDataUpdateCoordinator]):
    """Base entity for Sabiana devices."""

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
    def _last_data(self) -> str:
        """Return normalized status data."""
        return str(self._device_payload.get("lastData") or "").upper()


def byte_at(payload: str | None, byte_index: int) -> str | None:
    """Return a 1-based byte from a hex string."""
    if not payload:
        return None
    start = (byte_index - 1) * 2
    end = start + 2
    if len(payload) < end:
        return None
    return payload[start:end]


def parse_temperature(payload: str | None, byte_index: int) -> float | None:
    """Parse a temperature byte into Celsius."""
    value = byte_at(payload, byte_index)
    if value is None:
        return None

    try:
        return int(value, 16) / 10
    except ValueError:
        return None
