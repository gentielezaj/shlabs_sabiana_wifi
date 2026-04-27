"""Generate Sabiana command codes from simple inputs.

Examples:
    python functioncodes_calc.py heat 20 1
    python functioncodes_calc.py heat 20 3.5
    python functioncodes_calc.py heat 20 auto
    python functioncodes_calc.py cool 21.5 1
    python functioncodes_calc.py cool 21.5 4.5
    python functioncodes_calc.py cool 18.5 auto
    python functioncodes_calc.py fan 3.5
    python functioncodes_calc.py night on
    python functioncodes_calc.py off
"""

from __future__ import annotations

import argparse


TEMP_MIN = 10.0
TEMP_MAX = 30.0
FAN_MIN = 1.0
FAN_MAX = 10.0
STEP = 0.5

COMMAND_SUFFIX = "FF00FFFF0000"
FAN_SUFFIX = "030000FF00FFFF0000"
FAN_AUTO_CODE = "04030000FF00FFFF0000"
NIGHT_ON_CODE = "14030000FF00FFFF0002"
NIGHT_OFF_CODE = "14030000FF00FFFF0000"
OFF_CODE = "04040000FF00FFFF0000"


def _validate_half_step(value: float, *, minimum: float, maximum: float, label: str) -> float:
    if not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")

    doubled = value * 2
    if int(round(doubled)) != doubled:
        raise ValueError(f"{label} must use {STEP} increments")

    return value


def _encode_temperature(temperature: float) -> str:
    """Encode a temperature to the payload format."""
    _validate_half_step(temperature, minimum=TEMP_MIN, maximum=TEMP_MAX, label="Temperature")
    return f"{int(round(temperature * 10)):04X}"


def _encode_fan_prefix(level: float | str) -> str:
    """Encode a fan speed or auto mode to the leading command byte."""
    if isinstance(level, str) and level.lower() == "auto":
        return "04"

    numeric_level = float(level)
    _validate_half_step(numeric_level, minimum=FAN_MIN, maximum=FAN_MAX, label="Fan level")
    return f"{int(round(numeric_level * 10 + 10)):02X}"


def build_heat_code(temperature: float, fan_level: float | str = 1.0) -> str:
    """Return the heat command code for a target temperature and fan speed."""
    return f"{_encode_fan_prefix(fan_level)}01{_encode_temperature(temperature)}{COMMAND_SUFFIX}"


def build_cool_code(temperature: float, fan_level: float | str = 1.0) -> str:
    """Return the cool command code for a target temperature and fan speed."""
    return f"{_encode_fan_prefix(fan_level)}00{_encode_temperature(temperature)}{COMMAND_SUFFIX}"


def build_fan_code(level: float | str) -> str:
    """Return the fan command code for a fan speed."""
    if _encode_fan_prefix(level) == "04":
        return FAN_AUTO_CODE
    return f"{_encode_fan_prefix(level)}{FAN_SUFFIX}"


def build_night_mode_code(enabled: bool) -> str:
    """Return the night mode command code."""
    return NIGHT_ON_CODE if enabled else NIGHT_OFF_CODE


def build_off_code() -> str:
    """Return the off command code."""
    return OFF_CODE


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Sabiana command codes")
    subparsers = parser.add_subparsers(dest="command", required=True)

    heat_parser = subparsers.add_parser("heat", help="Generate a heat code")
    heat_parser.add_argument("temperature", type=float)
    heat_parser.add_argument("fan_level", nargs="?", default=1.0)

    cool_parser = subparsers.add_parser("cool", help="Generate a cool code")
    cool_parser.add_argument("temperature", type=float)
    cool_parser.add_argument("fan_level", nargs="?", default=1.0)

    fan_parser = subparsers.add_parser("fan", help="Generate a fan code")
    fan_parser.add_argument("level")

    night_parser = subparsers.add_parser("night", help="Generate a night mode code")
    night_parser.add_argument("state", choices=["on", "off"])

    subparsers.add_parser("off", help="Generate the off code")

    args = parser.parse_args()

    if args.command == "heat":
        print(build_heat_code(args.temperature, args.fan_level))
        return

    if args.command == "cool":
        print(build_cool_code(args.temperature, args.fan_level))
        return

    if args.command == "fan":
        print(build_fan_code(args.level))
        return

    if args.command == "night":
        print(build_night_mode_code(args.state == "on"))
        return

    print(build_off_code())


if __name__ == "__main__":
    main()
