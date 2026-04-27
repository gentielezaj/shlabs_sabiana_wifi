# SHLabs Sabiana WiFi

Custom Home Assistant integration for Sabiana fan coils that use the Sabiana cloud API.

The integration authenticates against the Sabiana service, polls device state every 30 seconds, parses the `lastData` payload, and exposes each unit as a Home Assistant `climate` entity.

GitHub repository:

```text
https://github.com/gentielezaj/shlabs_sabiana_wifi
```

## What This Integration Does

The integration currently supports:

1. Login with email and password
2. In-memory session refresh during runtime
3. Polling all devices from the Sabiana cloud
4. Creating one Home Assistant climate entity per device
5. Reading:
   - current temperature
   - target temperature
   - HVAC mode
   - HVAC action
   - fan level
   - RSSI
   - firmware version
6. Writing:
   - turn off
   - set cool mode
   - set heat mode
   - set fan-only mode
   - set target temperature
   - set fan level

## Folder Layout

The custom component lives in:

```text
custom_components/shlabs_sabiana_wifi/
```

Main files:

1. `manifest.json`
2. `__init__.py`
3. `config_flow.py`
4. `api.py`
5. `coordinator.py`
6. `entity.py`
7. `climate.py`
8. `const.py`
9. `translations/en.json`

## Installation

### Install with HACS

1. Open HACS in Home Assistant.
2. Open the menu in the top right and choose `Custom repositories`.
3. Add this repository URL:

```text
https://github.com/gentielezaj/shlabs_sabiana_wifi
```

4. Select category `Integration`.
5. Search for `SHLabs Sabiana WiFi` in HACS and install it.
6. Restart Home Assistant.
7. Go to `Settings -> Devices & Services`.
8. Click `Add Integration`.
9. Search for `SHLabs Sabiana WiFi`.
10. Enter your API base URL, email, and password.

Default base URL:

```text
https://be-standard.sabianawm.cloud
```

### Manual installation

Copy the `custom_components/shlabs_sabiana_wifi` folder into your Home Assistant configuration directory:

```text
config/custom_components/shlabs_sabiana_wifi/
```

Restart Home Assistant, then add the integration from `Settings -> Devices & Services`.

## Configuration

1. Go to `Settings -> Devices & Services`.
2. Click `Add Integration`.
3. Search for `SHLabs Sabiana WiFi`.
4. Enter API base URL.
5. Enter email.
6. Enter password.

## API Flow

The integration uses this sequence:

### 1. Login

Endpoint:

```text
POST /users/newLogin
```

Request body:

```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

Relevant response values:

```json
{
  "body": {
    "user": {
      "shortJwt": "session token",
      "longJwt": "refresh token"
    }
  }
}
```

The integration keeps session tokens only in memory while Home Assistant is running.

### 2. Refresh token when needed

Endpoint:

```text
POST /renewJwt
```

The API returns a new JWT in `body.newToken`.

### 3. Poll devices

Endpoint:

```text
GET /devices/getDeviceForUserV2
```

Response shape used by the integration:

```json
{
  "body": {
    "devices": [
      {
        "idDevice": "swm-...",
        "deviceName": "Sleeping room",
        "lastData": "5020003f14030160000000d200cd00c800dcc800c800001400001971012d00200000000200000000",
        "deviceStateFw": "1.45",
        "deviceWiFiRSSI": -53
      }
    ]
  }
}
```

### 4. Send command

Endpoint:

```text
POST /devices/cmd
```

Body:

```json
{
  "deviceID": "swm-...",
  "start": 2304,
  "data": "140100C8FF00FFFF0000",
  "restart": false
}
```

## How The Code Is Structured

If you come from C# or JavaScript, the easiest mental model is this:

1. `config_flow.py` is like your setup wizard or configuration form
2. `api.py` is your HTTP service class
3. `coordinator.py` is a polling cache or background refresh service
4. `climate.py` is the domain model plus command handlers exposed to Home Assistant
5. `__init__.py` is the composition root / startup registration

## File-By-File Explanation

### `manifest.json`

This is the integration metadata file.

It tells Home Assistant:

1. the domain name: `shlabs_sabiana_wifi`
2. that the integration has a UI setup flow: `config_flow: true`
3. that the integration type is a device integration
4. that it is `cloud_polling`

If you compare it to C# or Node.js:

1. in C#, think of it as package metadata plus registration hints
2. in Node.js, think of it as a very small `package.json` used by Home Assistant

### `const.py`

This file holds constants so they are not scattered across the codebase.

It contains:

1. domain name
2. API routes
3. mode codes
4. action codes
5. default base URL
6. temperature limits

This is similar to:

1. a static `Constants` class in C#
2. a `constants.js` or `constants.ts` module in JavaScript

### `__init__.py`

This is the integration startup file.

Main function:

```python
async def async_setup_entry(hass, entry):
```

What it does:

1. creates the API client
2. creates the polling coordinator
3. does the first refresh immediately
4. stores the coordinator in `entry.runtime_data`
5. forwards setup to the `climate` platform

C# analogy:

This is close to application startup code where you wire services together and start background dependencies.

JavaScript analogy:

This is similar to initializing a service, loading initial state, and then registering route/module handlers.

### `config_flow.py`

This file defines the setup UI shown inside Home Assistant.

Important class:

```python
class SabianaCloudWmConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
```

Important method:

```python
async def async_step_user(self, user_input=None):
```

What happens here:

1. Home Assistant shows a form for `base_url`, `username`, and `password`
2. when the user submits, the code creates a temporary API client
3. it tries to log in immediately
4. if login works, it creates a config entry for the connection settings
5. if login fails, it shows an error on the form

C# analogy:

Think of this as a controller action plus validation logic for a connection wizard.

JavaScript analogy:

Think of this as a form submit handler that calls the backend, validates credentials, and saves config.

### `api.py`

This file is the HTTP client and in-memory session manager.

The main class is:

```python
class SabianaApiClient:
```

This is the equivalent of:

1. a typed service around `HttpClient` in C#
2. a wrapper around `fetch` or `axios` in JavaScript

#### `async_login()`

```python
async def async_login(self) -> None:
```

Responsibilities:

1. sends email/password to `/users/newLogin`
2. reads the access token from the response
3. reads the refresh token from the response
4. keeps both in memory for the running Home Assistant process

#### `async_refresh_token()`

```python
async def async_refresh_token(self) -> None:
```

Responsibilities:

1. uses the in-memory refresh token
2. calls `/renewJwt`
3. reads `body.newToken`
4. updates the in-memory access token

#### `async_get_devices()`

This fetches the list of devices from `/devices/getDeviceForUserV2`.

It converts raw JSON dictionaries into `SabianaDevice` objects.

The `SabianaDevice` dataclass is similar to:

1. a C# record or DTO
2. a TypeScript interface-backed object

#### `async_send_command()`

This sends a command to one device through `/devices/cmd`.

It builds this payload:

```json
{
  "deviceID": "...",
  "start": 2304,
  "data": "HEXCOMMAND",
  "restart": false
}
```

#### `_async_request()`

This is the core reusable HTTP method.

It does the cross-cutting concerns:

1. ensures login happened before authenticated requests
2. adds common headers
3. performs the HTTP request
4. if the response is `401`, refreshes the token and retries once
5. raises errors for non-success responses
6. parses JSON

This is the most important infrastructure method in the integration.

C# analogy:

This is like a shared `SendAsync` wrapper around `HttpClient` with automatic bearer refresh.

JavaScript analogy:

This is like an Axios instance with request/response interceptors.

### `coordinator.py`

This file is Home Assistant's polling layer.

Main class:

```python
class SabianaDataUpdateCoordinator(DataUpdateCoordinator[SabianaCoordinatorData]):
```

What it does:

1. runs every 30 seconds
2. calls `client.async_get_devices()`
3. stores the latest device snapshot in memory
4. lets all entities read from the same cached data

This avoids every entity making its own HTTP request.

C# analogy:

This is like a singleton background refresh service with in-memory cache.

JavaScript analogy:

This is similar to a polling store that updates shared app state every 30 seconds.

### `entity.py`

This file contains shared entity behavior.

Main class:

```python
class SabianaCoordinatorEntity(CoordinatorEntity[SabianaDataUpdateCoordinator]):
```

This is a base class used by actual entities.

It mostly provides `device_info`, which tells Home Assistant:

1. unique device identifier
2. manufacturer
3. device name
4. model
5. firmware version

This is similar to a shared base model or abstract class in C#.

### `climate.py`

This is the business logic file.

If you only want to understand one file deeply, this is the one.

It does three main things:

1. creates climate entities
2. reads values from `lastData`
3. generates command hex strings when Home Assistant asks to change something

#### `async_setup_entry()`

This creates one `SabianaClimateEntity` per device returned by the coordinator.

#### `SabianaClimateEntity`

This class represents one Sabiana unit.

Think of it as:

1. a domain object
2. plus a view-model for Home Assistant
3. plus command handlers

#### Reading state from `lastData`

The raw field is a hex string like:

```text
5020003f14030160000000d200cd00c800dcc800c800001400001971012d00200000000200000000
```

The helper function:

```python
def _byte_at(payload, byte_index):
```

returns one byte from the hex string using a 1-based index.

Example:

1. byte 1 means chars `0..1`
2. byte 2 means chars `2..3`
3. byte 7 means chars `12..13`

Then higher-level properties use this helper.

#### `current_temperature`

```python
return _parse_temperature(self._device_payload.get("lastData"), 12)
```

This reads byte 12 and converts hex to decimal and then divides by 10.

Example:

1. byte value `CD`
2. hex `CD` = decimal `205`
3. `205 / 10 = 20.5 C`

#### `target_temperature`

Same idea, but reads byte 14.

#### `hvac_mode`

This reads byte 7.

Mappings:

1. `00` = cool
2. `01` = heat
3. `03` = fan_only
4. `04` = off

#### `hvac_action`

This reads byte 8.

Mappings used right now:

1. `21` = actively running
2. `60` or `63` = idle

If current mode is:

1. cool and action is running -> `cooling`
2. heat and action is running -> `heating`
3. fan_only and action is running -> `fan`

#### `fan_mode`

This reads byte 1.

Encoding rule from your notes:

```text
(level + 1) * 10 -> hex
```

Examples:

1. level `1` -> `20` decimal -> `14` hex
2. level `10` -> `110` decimal -> `6E` hex

To decode, the code does the inverse:

```text
hex -> decimal -> divide by 10 -> minus 1
```

#### Writing commands

The methods:

1. `async_set_hvac_mode()`
2. `async_set_temperature()`
3. `async_set_fan_mode()`

all call `_build_command(...)`.

That function returns the 10-byte command hex string.

Current layout:

```text
[fan][mode][temp_hi][temp_lo]FF00FFFF00[night]
```

Examples:

1. cool 14.5 -> `14000091FF00FFFF0000`
2. heat 20 -> `140100C8FF00FFFF0000`
3. fan only -> `14030000FF00FFFF0000`
4. off -> `04040000FF00FFFF0000`

#### Helper functions

`_parse_temperature()`

1. gets one byte from the status string
2. converts hex to int
3. divides by 10

`_encode_temperature()`

1. multiplies by 10
2. converts to hex
3. formats as 4 hex digits

Example:

1. `20.0 * 10 = 200`
2. `200 = C8` hex
3. formatted as `00C8`

`_encode_fan_level()`

1. applies `(level + 1) * 10`
2. converts to hex

Example:

1. level `1`
2. `(1 + 1) * 10 = 20`
3. `20 = 14` hex

## How Data Flows Through The Integration

Here is the full path from Home Assistant startup to device control.

### Startup flow

1. Home Assistant loads `manifest.json`
2. Home Assistant calls `async_setup_entry()` in `__init__.py`
3. `__init__.py` creates `SabianaApiClient`
4. `__init__.py` creates `SabianaDataUpdateCoordinator`
5. the coordinator fetches devices immediately
6. `climate.py` creates one entity per device

### Read flow

1. coordinator calls `/devices/getDeviceForUserV2`
2. API response is cached in memory
3. each climate entity reads its own `lastData`
4. entity properties convert raw hex into Home Assistant values

### Write flow

1. user changes HVAC mode, setpoint, or fan speed in Home Assistant
2. Home Assistant calls a method on `SabianaClimateEntity`
3. the entity builds a hex command string
4. `api.py` posts it to `/devices/cmd`
5. coordinator refreshes device state again

## Important Python Concepts If You Come From C# / JavaScript

### `async` and `await`

Python async works very similarly to:

1. `async/await` in C# with `Task`
2. `async/await` in JavaScript with `Promise`

Example:

```python
data = await self._async_request("get", API_DEVICES)
```

This is conceptually the same as:

```csharp
var data = await client.GetAsync(...);
```

or:

```javascript
const data = await client.get(...)
```

### `@property`

Python uses `@property` to make method calls look like fields.

Example:

```python
@property
def target_temperature(self):
    ...
```

Usage:

```python
self.target_temperature
```

This is similar to a C# getter property.

### `dataclass`

Python `@dataclass` is similar to:

1. a C# record
2. a simple TypeScript object model with generated constructor behavior

### Exceptions

Custom exceptions here:

1. `SabianaApiError`
2. `SabianaAuthError`

This is the same idea as custom exception types in C#.

## Current Assumptions

These are the parts most likely to need refinement if you capture more traffic:

1. exact byte positions in `lastData` beyond the fields already mapped
2. whether `connectionUp` should directly affect entity availability
3. whether night mode should be its own switch entity
4. whether some devices need multi-device command endpoint `/devices/cmds`

## Suggested Next Improvements

1. Add a night mode switch entity
2. Mark entities unavailable when `connectionUp` is false
3. Add diagnostics or debug logging for raw `lastData`
4. Add tests for hex parsing and command generation
5. Confirm all byte offsets with more sample payloads

## Quick Mental Summary

If you want the shortest possible explanation:

1. `config_flow.py` logs the user in and saves credentials/tokens
2. `api.py` talks to Sabiana's cloud and refreshes tokens automatically
3. `coordinator.py` refreshes all devices every 30 seconds
4. `climate.py` converts Sabiana hex data into Home Assistant climate state and commands
5. `entity.py` provides common device metadata

If you want, the next step I can do is add inline comments to the Python files so each important part is easier to recognize while reading the code.
