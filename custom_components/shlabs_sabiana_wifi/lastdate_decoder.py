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
        
        # 1. NIGHT MODE: Bit 7 (0x80) is the Night Mode toggle
        night_mode = bool(action_byte & 0x80)
        
        # 2. POWER STATUS: Strip the Night Mode bit for state comparison
        base_action = action_byte & 0x7F
        
        # Fix: Specifically check raw action_byte for OFF codes (0x40, 0x60)
        # to prevent collisions with active Night Mode states like 0xE0.
        if action_byte in [0x40, 0x60]:
            power_status, is_on = "OFF", False
        elif base_action in [0x61, 0x63]:
            power_status, is_on = "IDLE", True
        else:
            power_status, is_on = "RUNNING", True

        # Byte 4: Fan Setpoint (Values < 20 are interpreted as AUTO)
        fan_raw = data[4]
        fan_setpoint = "AUTO" if fan_raw < 20 else (fan_raw - 10) / 10.0

        # Mode Mapping (Byte 5)
        mode = {0: "Cooling", 1: "Heating", 3: "Fan Only"}.get(data[5], "Unknown")

        # Temperature Logic
        room_temp = data[11] / 10.0
        
        # Target Temperature: 16-bit Big Endian at Indices 14 and 15
        target_temp = ((data[14] << 8) | data[15]) / 10.0
        
        # Water Temperature: Verified at Index 17
        water_temp = data[17] / 10.0
        
        # Actual Motor Speed: Index 23
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