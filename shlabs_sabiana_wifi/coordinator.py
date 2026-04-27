"""Coordinator for SHLabs Sabiana Wifi."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SabianaApiClient, SabianaApiError, SabianaAuthError, SabianaDevice
from .const import DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SabianaCoordinatorData:
    """Parsed device data for coordinator consumers."""

    devices: dict[str, SabianaDevice]


class SabianaDataUpdateCoordinator(DataUpdateCoordinator[SabianaCoordinatorData]):
    """Manage Sabiana Wifi polling."""

    def __init__(self, hass: HomeAssistant, client: SabianaApiClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Sabiana Wifi Integration",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> SabianaCoordinatorData:
        """Fetch latest data from the API."""
        try:
            devices = await self.client.async_get_devices()
        except (SabianaApiError, SabianaAuthError) as err:
            raise UpdateFailed(str(err)) from err

        return SabianaCoordinatorData(devices={device.id: device for device in devices})
