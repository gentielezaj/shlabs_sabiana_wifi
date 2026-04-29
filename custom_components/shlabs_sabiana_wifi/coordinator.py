"""Coordinator for SHLabs Sabiana Wifi."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SabianaApiClient, SabianaApiError, SabianaAuthError, SabianaDevice
from .const import DEFAULT_SCAN_INTERVAL
from .lastdate_decoder import SabianaCloudWM

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
            name="SHLabs Sabiana WiFi",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self._ws_client = None

    async def async_start_websocket(self) -> None:
        """Create and start the WebSocket client for real-time updates."""
        # Import here to avoid circular imports at module level
        from .websocket import SabianaWebSocketClient  # noqa: PLC0415

        self._ws_client = SabianaWebSocketClient(
            self.hass, self.client, self._handle_ws_device_update
        )
        self._ws_client.async_start()

    async def async_stop_websocket(self) -> None:
        """Stop the WebSocket client if running."""
        if self._ws_client is not None:
            await self._ws_client.async_stop()
            self._ws_client = None

    def _handle_ws_device_update(self, device_id: str, hex_data: str) -> None:
        """Handle a real-time device update pushed from the WebSocket.

        Parses the hex payload and calls async_set_updated_data so all
        subscribed entities refresh immediately without waiting for the
        next poll interval.
        """
        if self.data is None:
            return

        current_devices = self.data.devices
        if device_id not in current_devices:
            _LOGGER.debug(
                "Sabiana WebSocket: unknown device %s — ignoring update", device_id
            )
            return

        parsed = SabianaCloudWM.parse(hex_data)
        if "error" in parsed:
            _LOGGER.warning(
                "Sabiana WebSocket: failed to parse data for %s: %s",
                device_id,
                parsed["error"],
            )
            return

        # Build an updated device, keeping all other fields unchanged
        old_device = current_devices[device_id]
        updated_device = SabianaDevice(
            id=old_device.id,
            name=old_device.name,
            payload=old_device.payload,
            lastData=parsed,
        )

        new_devices = {**current_devices, device_id: updated_device}
        self.async_set_updated_data(SabianaCoordinatorData(devices=new_devices))

    async def _async_update_data(self) -> SabianaCoordinatorData:
        """Fetch latest data from the API."""
        try:
            devices = await self.client.async_get_devices()
        except (SabianaApiError, SabianaAuthError) as err:
            raise UpdateFailed(str(err)) from err

        return SabianaCoordinatorData(devices={device.id: device for device in devices})

