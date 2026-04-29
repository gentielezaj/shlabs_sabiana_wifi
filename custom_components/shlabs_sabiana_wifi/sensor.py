"""Sensor platform for SHLabs Sabiana Wifi diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import (
    LAST_DATA_ACTION_BYTE,
    LAST_DATA_CURRENT_TEMP_BYTE,
    LAST_DATA_FAN_STATUS_BYTE,
    LAST_DATA_LIMIT_TEMP_BYTE,
    LAST_DATA_MODE_BYTE,
    LAST_DATA_NIGHT_MODE_BYTE,
    LAST_DATA_POWER_BYTE,
    LAST_DATA_SECONDARY_TARGET_TEMP_BYTE,
    LAST_DATA_TARGET_TEMP_BYTE,
    LAST_DATA_WATER_TEMP_BYTE,
    SabianaCoordinatorEntity,
    parse_temperature,
)


@dataclass(frozen=True, slots=True)
class SabianaDiagnosticDescription:
    """Describe a diagnostic sensor."""

    key: str
    name: str
    value_fn: Callable[[dict[str, Any] | None], str | float | bool | None]
    diagnostic: bool = True
    device_class: SensorDeviceClass | None = None
    native_unit_of_measurement: str | None = None
    suggested_unit_of_measurement: str | None = None


STATUS_SENSORS: tuple[SabianaDiagnosticDescription, ...] = (
    SabianaDiagnosticDescription(
        "current_temperature_label",
        "Current temperature",
        lambda payload: parse_temperature(payload, LAST_DATA_CURRENT_TEMP_BYTE),
        diagnostic=False,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SabianaDiagnosticDescription(
        "target_temperature_label",
        "Target temperature",
        lambda payload: parse_temperature(payload, LAST_DATA_TARGET_TEMP_BYTE),
        diagnostic=False,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SabianaDiagnosticDescription(
        "water_temperature_label",
        "Water temperature",
        lambda payload: parse_temperature(payload, LAST_DATA_WATER_TEMP_BYTE),
        diagnostic=False,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
)


DIAGNOSTIC_SENSORS: tuple[SabianaDiagnosticDescription, ...] = (
    SabianaDiagnosticDescription("last_data", "Last data", lambda payload: payload or None),
    SabianaDiagnosticDescription("power_byte", "Power byte", lambda payload: payload.get(LAST_DATA_POWER_BYTE) if payload else None),
    SabianaDiagnosticDescription("mode_byte", "Mode byte", lambda payload: payload.get(LAST_DATA_MODE_BYTE) if payload else None),
    SabianaDiagnosticDescription("action_byte", "Action byte", lambda payload: payload.get(LAST_DATA_ACTION_BYTE) if payload else None),
    SabianaDiagnosticDescription("fan_status_byte", "Fan status byte", lambda payload: payload.get(LAST_DATA_FAN_STATUS_BYTE) if payload else None),
    SabianaDiagnosticDescription("fan_level", "Fan level", lambda payload: _parse_fan_level(payload)),
    SabianaDiagnosticDescription("current_temperature", "Current temperature", lambda payload: parse_temperature(payload, LAST_DATA_CURRENT_TEMP_BYTE)),
    SabianaDiagnosticDescription("target_temperature", "Target temperature", lambda payload: parse_temperature(payload, LAST_DATA_TARGET_TEMP_BYTE)),
    SabianaDiagnosticDescription("secondary_target_temperature", "Secondary target temperature", lambda payload: parse_temperature(payload, LAST_DATA_SECONDARY_TARGET_TEMP_BYTE)),
    SabianaDiagnosticDescription("water_temperature", "Water temperature", lambda payload: parse_temperature(payload, LAST_DATA_WATER_TEMP_BYTE)),
    SabianaDiagnosticDescription("limit_temperature", "Limit temperature", lambda payload: parse_temperature(payload, LAST_DATA_LIMIT_TEMP_BYTE)),
    SabianaDiagnosticDescription("night_mode", "Night mode", lambda payload: "on" if payload and payload.get(LAST_DATA_NIGHT_MODE_BYTE) else "off"),
)


PARSED_RESPONSE_SENSORS: tuple[SabianaDiagnosticDescription, ...] = (
    SabianaDiagnosticDescription("parsed_is_on", "Parsed is_on", lambda payload: "on" if payload and payload.get("is_on") else "off"),
    SabianaDiagnosticDescription("parsed_power_status", "Parsed power_status", lambda payload: payload.get("power_status") if payload else None),
    SabianaDiagnosticDescription("parsed_mode", "Parsed mode", lambda payload: payload.get("mode") if payload else None),
    SabianaDiagnosticDescription("parsed_night_mode", "Parsed night_mode", lambda payload: "on" if payload and payload.get("night_mode") else "off"),
    SabianaDiagnosticDescription(
        "parsed_room_temp",
        "Parsed room_temp",
        lambda payload: parse_temperature(payload, "room_temp"),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SabianaDiagnosticDescription(
        "parsed_target_temp",
        "Parsed target_temp",
        lambda payload: parse_temperature(payload, "target_temp"),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SabianaDiagnosticDescription(
        "parsed_water_temp",
        "Parsed water_temp",
        lambda payload: parse_temperature(payload, "water_temp"),
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    SabianaDiagnosticDescription("parsed_fan_setpoint", "Parsed fan_setpoint", lambda payload: payload.get("fan_setpoint") if payload else None),
    SabianaDiagnosticDescription("parsed_actual_motor_speed", "Parsed actual_motor_speed", lambda payload: _parse_number(payload, "actual_motor_speed")),
    SabianaDiagnosticDescription("parsed_raw_action_hex", "Parsed raw_action_hex", lambda payload: payload.get("raw_action_hex") if payload else None),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sabiana diagnostic sensors."""
    coordinator = entry.runtime_data
    entities = [
        SabianaDiagnosticSensor(coordinator, device_id, description)
        for device_id in coordinator.data.devices
        for description in (*STATUS_SENSORS, *DIAGNOSTIC_SENSORS, *PARSED_RESPONSE_SENSORS)
    ]
    async_add_entities(entities)


class SabianaDiagnosticSensor(SabianaCoordinatorEntity, SensorEntity):
    """Readonly diagnostic sensor for decoded device state."""

    _attr_has_entity_name = True
    def __init__(
        self,
        coordinator,
        device_id: str,
        description: SabianaDiagnosticDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_entity_category = EntityCategory.DIAGNOSTIC if description.diagnostic else None

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self._device_id}_{self.entity_description.key}"

    @property
    def native_value(self) -> str | float | bool | None:
        """Return the decoded sensor value."""
        return self.entity_description.value_fn(self._last_data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose raw lastData for debugging."""
        return {"last_data": self._last_data}


def _parse_fan_level(payload: dict | None) -> float | None:
    """Decode fan level from the parsed lastData dict."""
    if not payload:
        return None
    value = payload.get(LAST_DATA_FAN_STATUS_BYTE)
    if value is None:
        return None
    if value == "AUTO":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_number(payload: dict[str, Any] | None, key: str) -> float | None:
    """Return a numeric value from the parsed lastData dict."""
    if not payload:
        return None
    value = payload.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
