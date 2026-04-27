"""Shared entity helpers for SHLabs Sabiana Wifi."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SabianaDataUpdateCoordinator


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
