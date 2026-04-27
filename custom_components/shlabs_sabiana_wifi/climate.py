"""Climate platform for SHLabs Sabiana Wifi."""

from __future__ import annotations

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ACTION_IDLE_VALUES,
    ACTION_RUNNING,
    ATTR_FIRMWARE,
    ATTR_RSSI,
    MAX_TEMP,
    MIN_TEMP,
    MODE_COOL,
    MODE_FAN,
    MODE_HEAT,
    MODE_OFF,
    OFF_COMMAND,
    TARGET_TEMPERATURE_STEP,
)
from .entity import SabianaCoordinatorEntity

MODE_TO_HVAC = {
    MODE_COOL: HVACMode.COOL,
    MODE_HEAT: HVACMode.HEAT,
    MODE_FAN: HVACMode.FAN_ONLY,
}

HVAC_TO_MODE = {value: key for key, value in MODE_TO_HVAC.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sabiana climate entities."""
    coordinator = entry.runtime_data
    async_add_entities(SabianaClimateEntity(coordinator, device_id) for device_id in coordinator.data.devices)


class SabianaClimateEntity(SabianaCoordinatorEntity, ClimateEntity):
    """Representation of a Sabiana fan coil."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TARGET_TEMPERATURE_STEP
    _attr_hvac_modes = [HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.OFF]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    _attr_fan_modes = [str(level) for level in range(1, 11)]

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._device_id

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self._device_id in self.coordinator.data.devices

    @property
    def current_temperature(self) -> float | None:
        """Return current temperature."""
        return _parse_temperature(self._device_payload.get("lastData"), 12)

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return _parse_temperature(self._device_payload.get("lastData"), 14)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        last_data = self._last_data
        if not last_data:
            return HVACMode.OFF

        mode_byte = _byte_at(last_data, 7)
        if mode_byte == MODE_OFF:
            return HVACMode.OFF

        return MODE_TO_HVAC.get(mode_byte, HVACMode.OFF)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the running action."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        action_code = _byte_at(self._last_data, 8)
        if action_code == ACTION_RUNNING:
            if self.hvac_mode == HVACMode.COOL:
                return HVACAction.COOLING
            if self.hvac_mode == HVACMode.HEAT:
                return HVACAction.HEATING
            return HVACAction.FAN
        if action_code in ACTION_IDLE_VALUES:
            return HVACAction.IDLE
        return None

    @property
    def fan_mode(self) -> str | None:
        """Return current fan mode."""
        fan_byte = _byte_at(self._last_data, 1)
        if fan_byte is None:
            return None

        try:
            level = int(int(fan_byte, 16) / 10) - 1
        except ValueError:
            return None

        if 1 <= level <= 10:
            return str(level)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return extra attributes."""
        return {
            ATTR_RSSI: self._device_payload.get("deviceWiFiRSSI"),
            ATTR_FIRMWARE: self._device_payload.get("deviceStateFw"),
        }

    @property
    def min_temp(self) -> float:
        """Return minimum settable temperature."""
        return MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return maximum settable temperature."""
        return MAX_TEMP

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.client.async_send_command(self._device_id, OFF_COMMAND)
        else:
            await self.coordinator.client.async_send_command(
                self._device_id,
                _build_command(
                    mode=HVAC_TO_MODE[hvac_mode],
                    target_temperature=self.target_temperature or 20.0,
                    fan_level=int(self.fan_mode or "1"),
                    night_mode=_byte_at(self._last_data, 9) == "02",
                ),
            )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set a new target temperature."""
        temperature = kwargs[ATTR_TEMPERATURE]
        current_mode = self.hvac_mode if self.hvac_mode != HVACMode.OFF else HVACMode.COOL
        await self.coordinator.client.async_send_command(
            self._device_id,
            _build_command(
                mode=HVAC_TO_MODE[current_mode],
                target_temperature=temperature,
                fan_level=int(self.fan_mode or "1"),
                night_mode=_byte_at(self._last_data, 9) == "02",
            ),
        )
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set a new fan level."""
        current_mode = self.hvac_mode if self.hvac_mode != HVACMode.OFF else HVACMode.FAN_ONLY
        await self.coordinator.client.async_send_command(
            self._device_id,
            _build_command(
                mode=HVAC_TO_MODE[current_mode],
                target_temperature=self.target_temperature or 20.0,
                fan_level=int(float(fan_mode)),
                night_mode=_byte_at(self._last_data, 9) == "02",
            ),
        )
        await self.coordinator.async_request_refresh()

    @property
    def _device_payload(self) -> dict:
        """Return raw payload for this entity."""
        return self.coordinator.data.devices[self._device_id].payload

    @property
    def _last_data(self) -> str:
        """Return normalized status data."""
        return str(self._device_payload.get("lastData") or "").upper()


def _parse_temperature(last_data: str | None, byte_index: int) -> float | None:
    """Parse a temperature from the payload string."""
    value = _byte_at(last_data, byte_index)
    if value is None:
        return None

    try:
        return int(value, 16) / 10
    except ValueError:
        return None


def _byte_at(payload: str | None, byte_index: int) -> str | None:
    """Return a 1-based byte from a hex string."""
    if not payload:
        return None
    start = (byte_index - 1) * 2
    end = start + 2
    if len(payload) < end:
        return None
    return payload[start:end]


def _encode_temperature(value: float) -> str:
    """Encode a target temperature into the command payload."""
    encoded = int(round(value * 10))
    return f"{encoded:04X}"


def _encode_fan_level(level: int) -> str:
    """Encode a fan level using the documented formula."""
    encoded = int((level + 1) * 10)
    return f"{encoded:02X}"


def _build_command(*, mode: str, target_temperature: float, fan_level: int, night_mode: bool) -> str:
    """Build the 10-byte hex command string."""
    temp_hex = _encode_temperature(target_temperature)
    night_hex = "02" if night_mode else "00"
    return f"{_encode_fan_level(fan_level)}{mode}{temp_hex}FF00FFFF00{night_hex}"
