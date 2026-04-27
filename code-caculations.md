Your documentation for the Sabiana Cloud WM hex logic is ready. This is structured for use in a technical repository or as a reference for your Home Assistant integration.

# Sabiana Cloud WM: Protocol Specification & Calculation Logic

This document outlines the hexadecimal communication protocol for Sabiana Cloud WM fan coil units, covering both command construction (writing) and status parsing (reading).

---

## 1. Command Architecture (Write Logic)
Commands sent to the `POST /devices/cmds` endpoint consist of a 10-byte (20-character) hex string.

### Frame Structure
| Byte | Description | Logic / Formula |
| :--- | :--- | :--- |
| **0** | Fan Speed | `(Level * 10) + 10` → Hex. (Manual 1.0–10.0) |
| **1** | Operation Mode | `01` = Heat, `00` = Cool, `03` = Fan, `04` = Off |
| **2-3** | Temperature | `Setpoint * 10` → 16-bit Hex (Big Endian) |
| **4-9** | Static Suffix | Always `FF00FFFF0000` |

### Special Fan States
- **Manual Range:** 1.0 to 10.0 (in 0.5 increments).
- **Auto Fan:** Use `04` for Byte 0.

### Temperature Increment Logic
Temperature setpoints follow a 0.5°C step. 
- **Example 22.5°C:** $22.5 \times 10 = 225 \rightarrow$ `00E1`
- **Example 30.0°C:** $30.0 \times 10 = 300 \rightarrow$ `012C`

---

## 2. Status Parsing (Read Logic)
The status returned in the `lastData` field of the `checkUserAuth` response is a 40-byte (80-character) hex string.

### Critical Indices for Integration
| Index | Property | Calculation |
| :--- | :--- | :--- |
| **Byte 4** | Power State | `04` = Standby (Off), `05` = Active (On) |
| **Byte 5** | Mode | `00`=Cool, `01`=Heat, `03`=Fan |
| **Byte 11** | Room Temp | `HexDec / 10` |
| **Byte 13** | Target Temp | `HexDec / 10` |
| **Byte 17** | Water Temp | `HexDec / 10` (Coil Probe) |
| **Byte 23** | Fan Speed | `(HexDec - 10) / 10` |
| **Byte 35** | Night Mode | `02` = On, `00` = Off |

---

## 3. Implementation Reference

### C# Helper (Systems Architect Style)
```csharp
public class SabianaProtocol
{
    private const string SUFFIX = "FF00FFFF0000";

    public string BuildCommand(double fanLevel, double temp, byte mode = 0x01)
    {
        // Enforce 0.5 increments and bounds
        fanLevel = Math.Clamp(Math.Round(fanLevel * 2) / 2, 1.0, 10.0);
        temp = Math.Clamp(Math.Round(temp * 2) / 2, 10.0, 30.0);

        byte fanByte = (byte)((fanLevel * 10) + 10);
        ushort tempVal = (ushort)(temp * 10);

        return $"{fanByte:X2}{mode:X2}{tempVal:X4}{SUFFIX}";
    }
}
```

### Python/Home Assistant Helper
```python
def parse_sabiana_status(hex_string):
    raw = bytes.fromhex(hex_string)
    return {
        "is_on": raw[4] == 5,
        "current_temp": raw[11] / 10.0,
        "target_temp": raw[13] / 10.0,
        "water_temp": raw[17] / 10.0,
        "fan_level": (raw[23] - 10) / 10.0,
        "night_mode": raw[35] == 2
    }
```

---

## 4. Reference Table: Fan Speed to Hex (0.5 Steps)

| Level | Hex | Level | Hex | Level | Hex |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1.0** | `14` | **4.0** | `32` | **7.0** | `50` |
| **1.5** | `19` | **4.5** | `37` | **7.5** | `55` |
| **2.0** | `1E` | **5.0** | `3C` | **8.0** | `5A` |
| **2.5** | `23` | **5.5** | `41` | **8.5** | `5F` |
| **3.0** | `28` | **6.0** | `46` | **9.0** | `64` |
| **3.5** | `2D` | **6.5** | `4B` | **9.5** | `69` |
| **Auto** | `04` | | | **10.0** | `6E` |

---

## 5. Reference Table: Setpoint to Hex (Common Steps)

| Temp | Hex | Temp | Hex |
| :--- | :--- | :--- | :--- |
| **18.0** | `00B4` | **22.5** | `00E1` |
| **19.0** | `00BE` | **23.0** | `00E6` |
| **20.0** | `00C8` | **24.0** | `00F0` |
| **21.0** | `00D2` | **25.0** | `00FA` |
| **22.0** | `00DC` | **25.5** | `00FF` |

---

### Technical Notes
1. **Integer Overflow:** When the temperature exceeds 25.5°C, the high byte (Byte 2) increments from `00` to `01` as the total decimal value passes 255.
2. **Rounding:** The physical hardware may reject commands if setpoints do not end in `.0` or `.5`. Always round to the nearest 0.5 before conversion.