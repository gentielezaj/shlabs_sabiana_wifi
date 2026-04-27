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
from .entity import (
    LAST_DATA_ACTION_BYTE,
    LAST_DATA_CURRENT_TEMP_BYTE,
    LAST_DATA_FAN_BYTE,
    LAST_DATA_MODE_BYTE,
    LAST_DATA_NIGHT_MODE_BYTE,
    LAST_DATA_POWER_BYTE,
    LAST_DATA_LIMIT_TEMP_BYTE,
    LAST_DATA_SECONDARY_TARGET_TEMP_BYTE,
    LAST_DATA_TARGET_TEMP_BYTE,
    LAST_DATA_WATER_TEMP_BYTE,
    SabianaCoordinatorEntity,
    byte_at,
    parse_temperature,
)

MODE_TO_HVAC = {
    MODE_COOL: HVACMode.COOL,
    MODE_HEAT: HVACMode.HEAT,
    MODE_FAN: HVACMode.FAN_ONLY,
}

HVAC_TO_MODE = {value: key for key, value in MODE_TO_HVAC.items()}

TEMPERATURE_COMMANDS = {
    MODE_HEAT: {
        key: f"1401{value:04X}FF00FFFF0000" for key, value in ((step, step * 5) for step in range(20, 61))
    },
    MODE_COOL: {
        key: f"1400{value:04X}FF00FFFF0000" for key, value in ((step, step * 5) for step in range(20, 61))
    },
}

FAN_COMMANDS = {
    step: f"{(step * 5 + 10):02X}030000FF00FFFF0000" for step in range(2, 21)
}


def _format_fan_mode(level: float) -> str:
    """Format a fan level without trailing .0."""
    if level.is_integer():
        return str(int(level))
    return str(level)


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
    _attr_fan_modes = [_format_fan_mode(level / 2) for level in range(2, 21)]

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
        return parse_temperature(self._last_data, LAST_DATA_CURRENT_TEMP_BYTE)

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return parse_temperature(self._last_data, LAST_DATA_TARGET_TEMP_BYTE)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        last_data = self._last_data
        if not last_data:
            return HVACMode.OFF

        power_byte = byte_at(last_data, LAST_DATA_POWER_BYTE)
        if power_byte == MODE_OFF:
            return HVACMode.OFF

        mode_byte = byte_at(last_data, LAST_DATA_MODE_BYTE)

        return MODE_TO_HVAC.get(mode_byte, HVACMode.OFF)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Return the running action."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF

        action_code = byte_at(self._last_data, LAST_DATA_ACTION_BYTE)
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
        fan_byte = byte_at(self._last_data, LAST_DATA_FAN_BYTE)
        if fan_byte is None:
            return None

        try:
            level = int(fan_byte, 16) / 10 - 1
        except ValueError:
            return None

        if 1 <= level <= 10:
            return _format_fan_mode(level)
        return None

    @property
    def is_aux_heat(self) -> bool:
        """Expose night mode from the last command byte."""
        return byte_at(self._last_data, LAST_DATA_NIGHT_MODE_BYTE) == "02"

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return extra attributes."""
        return {
            ATTR_RSSI: self._device_payload.get("deviceWiFiRSSI"),
            ATTR_FIRMWARE: self._device_payload.get("deviceStateFw"),
            "power_byte": byte_at(self._last_data, LAST_DATA_POWER_BYTE),
            "mode_byte": byte_at(self._last_data, LAST_DATA_MODE_BYTE),
            "action_byte": byte_at(self._last_data, LAST_DATA_ACTION_BYTE),
            "secondary_target_temperature": parse_temperature(self._last_data, LAST_DATA_SECONDARY_TARGET_TEMP_BYTE),
            "water_temperature": parse_temperature(self._last_data, LAST_DATA_WATER_TEMP_BYTE),
            "limit_temperature": parse_temperature(self._last_data, LAST_DATA_LIMIT_TEMP_BYTE),
            "night_mode": byte_at(self._last_data, LAST_DATA_NIGHT_MODE_BYTE) == "02",
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
        elif hvac_mode == HVACMode.FAN_ONLY:
            await self.coordinator.client.async_send_command(
                self._device_id,
                _build_fan_command(float(self.fan_mode or "1")),
            )
        else:
            await self.coordinator.client.async_send_command(
                self._device_id,
                _build_temperature_command(
                    mode=HVAC_TO_MODE[hvac_mode],
                    target_temperature=self.target_temperature or 20.0,
                ),
            )
        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set a new target temperature."""
        temperature = kwargs[ATTR_TEMPERATURE]
        current_mode = self.hvac_mode if self.hvac_mode in (HVACMode.COOL, HVACMode.HEAT) else HVACMode.COOL
        await self.coordinator.client.async_send_command(
            self._device_id,
            _build_temperature_command(
                mode=HVAC_TO_MODE[current_mode],
                target_temperature=temperature,
            ),
        )
        await self.coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set a new fan level."""
        await self.coordinator.client.async_send_command(
            self._device_id,
            _build_fan_command(float(fan_mode)),
        )
        await self.coordinator.async_request_refresh()


def _build_temperature_command(*, mode: str, target_temperature: float) -> str:
    """Build a heat or cool command using the documented codes."""
    normalized_temperature = _normalize_step_value(target_temperature)
    try:
        return TEMPERATURE_COMMANDS[mode][normalized_temperature]
    except KeyError as err:
        raise ValueError(f"Unsupported mode/temperature combination: {mode} {target_temperature}") from err


def _build_fan_command(level: float) -> str:
    """Build a fan command using the documented codes."""
    normalized_level = _normalize_step_value(level)
    try:
        return FAN_COMMANDS[normalized_level]
    except KeyError as err:
        raise ValueError(f"Unsupported fan level: {level}") from err


def _normalize_step_value(value: float) -> int:
    """Normalize a .5-step value into an integer lookup key."""
    return int(round(value * 2))
