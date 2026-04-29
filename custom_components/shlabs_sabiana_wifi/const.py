"""Constants for the SHLabs Sabiana Wifi integration."""

DOMAIN = "shlabs_sabiana_wifi"
PLATFORMS = ["climate", "switch", "sensor"]

ENTITY_PICTURE_URL = f"/{DOMAIN}/static/sabiana.webp"

CONF_BASE_URL = "base_url"

DEFAULT_NAME = "SHLabs Sabiana WiFi"
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_BASE_URL = "https://be-standard.sabianawm.cloud"

ATTR_RSSI = "rssi"
ATTR_FIRMWARE = "firmware"

MANUFACTURER = "Sabiana"
APP_ID_HEADER = "it.sabiana.cloud.wm"

API_LOGIN = "/users/newLogin"
API_RENEW = "/renewJwt"
API_DEVICES = "/devices/getDeviceForUserV2"
API_COMMANDS = "/devices/cmd"

MODE_COOL = "00"
MODE_HEAT = "01"
MODE_FAN = "03"
MODE_OFF = "04"

ACTION_RUNNING = "RUNNING"
ACTION_IDLE_VALUES = {"IDLE", "OFF"}

OFF_COMMAND = "04040000FF00FFFF0000"
NIGHT_MODE_ON_COMMAND = "14030000FF00FFFF0002"
NIGHT_MODE_OFF_COMMAND = "14030000FF00FFFF0000"

MIN_TEMP = 10.0
MAX_TEMP = 30.0
TARGET_TEMPERATURE_STEP = 0.5
