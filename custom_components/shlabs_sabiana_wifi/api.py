"""API client for SHLabs Sabiana Wifi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .lastdate_decoder import SabianaCloudWM
from .const import API_COMMANDS, API_DEVICES, API_LOGIN, API_RENEW, APP_ID_HEADER, CONF_BASE_URL


class SabianaApiError(Exception):
    """Base API error."""


class SabianaAuthError(SabianaApiError):
    """Authentication failed."""


@dataclass(slots=True)
class SabianaDevice:
    """Device payload from the cloud API."""

    id: str
    name: str
    payload: dict[str, Any]
    lastData: dict[str, Any]


class SabianaApiClient:
    """Sabiana Wifi REST client."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the client."""
        self.hass = hass
        self.entry = entry
        self._session = async_get_clientsession(hass)
        self._token: str | None = None
        self._renew_token: str | None = None

    @property
    def base_url(self) -> str:
        """Return the configured API base URL."""
        return str(self.entry.data[CONF_BASE_URL]).rstrip("/")

    @property
    def token(self) -> str | None:
        """Return the current short-lived JWT, or None if not authenticated."""
        return self._token

    async def async_ensure_authenticated(self) -> None:
        """Ensure a valid token exists, logging in if necessary."""
        if not self._token:
            await self.async_login()

    async def async_login(self) -> None:
        """Log in and cache tokens in memory."""
        payload = {
            "email": self.entry.data[CONF_USERNAME],
            "password": self.entry.data[CONF_PASSWORD],
        }
        data = await self._async_request(
            "post",
            API_LOGIN,
            json=payload,
            auth_required=False,
            retry_on_unauthorized=False,
        )
        self._token = self._extract_value(data, "shortJwt")
        self._renew_token = self._extract_value(data, "longJwt")

    async def async_refresh_token(self) -> None:
        """Refresh the JWT using the stored renew token."""
        if not self._renew_token:
            raise SabianaAuthError("Missing renew token")

        data = await self._async_request(
            "post",
            API_RENEW,
            headers={"renewAuth": self._renew_token},
            auth_required=False,
            retry_on_unauthorized=False,
        )
        self._token = self._extract_value(data, "newToken")

    async def async_get_devices(self) -> list[SabianaDevice]:
        """Fetch devices available to the account."""
        data = await self._async_request("get", API_DEVICES)
        devices = data.get("body", {}).get("devices", [])
        result: list[SabianaDevice] = []

        for device in devices:
            device_id = str(device.get("idDevice") or device.get("id") or "")
            if not device_id:
                continue
            name = str(device.get("deviceName") or device.get("name") or device_id)
            hex_input = str(device.get("lastData") or "")
            result.append(SabianaDevice(id=device_id, name=name, payload=device, lastData=SabianaCloudWM.parse(hex_input)))

        return result

    async def async_send_command(self, device_id: str, data: str) -> None:
        """Send a command to a device."""
        payload = {
            "deviceID": device_id,
            "start": 2304,
            "data": data,
            "restart": False,
        }
        await self._async_request("post", API_COMMANDS, json=payload)

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        auth_required: bool = True,
        retry_on_unauthorized: bool = True,
    ) -> dict[str, Any]:
        """Perform an API request."""
        if auth_required and not self._token:
            await self.async_login()

        request_headers = {"X-Requested-With": APP_ID_HEADER}
        if auth_required and self._token:
            request_headers["auth"] = self._token
        if headers:
            request_headers.update(headers)

        try:
            response = await self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=request_headers,
                json=json,
            )
        except ClientError as err:
            raise SabianaApiError("Request failed") from err

        if response.status == 401:
            response.release()
            if retry_on_unauthorized:
                await self.async_refresh_token()
                return await self._async_request(
                    method,
                    path,
                    headers=headers,
                    json=json,
                    auth_required=auth_required,
                    retry_on_unauthorized=False,
                )
            raise SabianaAuthError("Unauthorized")

        if response.status >= 400:
            text = await response.text()
            raise SabianaApiError(f"HTTP {response.status}: {text}")

        try:
            return await response.json(content_type=None)
        except Exception as err:
            raise SabianaApiError("Invalid JSON response") from err

    @staticmethod
    def _extract_value(payload: dict[str, Any], key: str) -> str:
        """Extract a token from the known payload layouts."""
        body = payload.get("body", {})
        user = body.get("user", {}) if isinstance(body, dict) else {}

        for container in (payload, body, user, payload.get("data", {})):
            value = container.get(key)
            if value:
                return str(value)
        raise SabianaAuthError(f"Missing {key} in response")
