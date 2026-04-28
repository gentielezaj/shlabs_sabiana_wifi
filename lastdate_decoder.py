class SabianaCloudWM:
    @staticmethod
    def parse(hex_string):
        try:
            data = bytes.fromhex(hex_string.strip())
        except ValueError:
            return {"error": "Invalid hex string"}

        if len(data) < 40:
            return {"error": "String too short"}

        # Byte 7: Action & Night Mode
        action_byte = data[7]
        night_mode = bool(action_byte & 0x80)
        base_action = action_byte & 0x7F
        
        if base_action == 0x60:
            power_status, is_on = "OFF", False
        elif base_action in [0x61, 0x63]:
            power_status, is_on = "IDLE", True
        else:
            power_status, is_on = "RUNNING", True

        # Byte 4: Fan Setpoint
        fan_raw = data[4]
        fan_setpoint = "AUTO" if fan_raw < 20 else (fan_raw - 10) / 10.0

        # Extract Other Values
        mode = {0: "Cooling", 1: "Heating", 3: "Fan Only"}.get(data[5], "Unknown")
        room_temp = data[11] / 10.0
        target_temp = ((data[14] << 8) | data[15]) / 10.0
        water_temp = data[17] / 10.0
        actual_motor = (data[23] - 10) / 10.0

        return {
            "is_on": is_on,
            "power_status": power_status,
            "mode": mode,
            "night_mode": night_mode,
            "room_temp": room_temp,
            "target_temp": target_temp,
            "water_temp": water_temp,
            "fan_setpoint": fan_setpoint,
            "actual_motor_speed": actual_motor,
            "raw_action_hex": f"{action_byte:02X}"
        }