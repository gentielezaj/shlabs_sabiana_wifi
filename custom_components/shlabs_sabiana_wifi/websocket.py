"""Socket.IO WebSocket client for real-time Sabiana device updates."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable

from aiohttp import ClientError, WSMsgType

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SabianaApiClient, SabianaApiError, SabianaAuthError
from .const import APP_ID_HEADER, WEBSOCKET_BASE_URL, WEBSOCKET_ORIGIN, WEBSOCKET_WSS_URL

_LOGGER = logging.getLogger(__name__)

# Exponential backoff: 5 -> 10 -> 20 -> 40 -> ... capped at 1 hour
_INITIAL_BACKOFF = 5
_MAX_BACKOFF = 3600
_BACKOFF_RESET_AFTER_SECONDS = 60

# Socket.IO / Engine.IO packet type prefixes
_EIO_PING = "2"
_EIO_PONG = "3"
_EIO_UPGRADE = "5"
_EIO_PROBE_REQUEST = "2probe"
_EIO_PROBE_RESPONSE = "3probe"
_SIO_CONNECT_ACK = "40"
_SIO_EVENT_PREFIX = "42"


class SabianaWebSocketClient:
    """Manages a persistent Socket.IO connection for real-time device updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: SabianaApiClient,
        on_device_data: Callable[[str, str], None],
    ) -> None:
        """Initialise the WebSocket client.

        Args:
            hass: The Home Assistant instance.
            client: Authenticated REST API client (used to obtain the JWT token).
            on_device_data: Callback invoked with (device_id, hex_data) for every
                            incoming ``["data", {...}]`` Socket.IO event.
        """
        self._hass = hass
        self._client = client
        self._on_device_data = on_device_data
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Public lifecycle
    # ------------------------------------------------------------------

    def async_start(self) -> None:
        """Schedule the persistent WebSocket loop as an HA background task."""
        if self._task and not self._task.done():
            _LOGGER.debug("Sabiana WebSocket task already running")
            return

        self._stop_event.clear()
        self._task = self._hass.async_create_background_task(
            self._run_forever(), "sabiana_websocket"
        )
        _LOGGER.debug("Sabiana WebSocket task started")

    async def async_stop(self) -> None:
        """Signal the WebSocket loop to stop and wait for it to finish."""
        _LOGGER.debug("Stopping Sabiana WebSocket task")
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
        self._task = None

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    async def _run_forever(self) -> None:
        """Reconnect loop with exponential backoff."""
        backoff = _INITIAL_BACKOFF
        while not self._stop_event.is_set():
            connected_duration = 0.0
            try:
                connected_duration = await self._connect()
            except asyncio.CancelledError:
                raise
            except (SabianaApiError, SabianaAuthError, ClientError, OSError) as err:
                _LOGGER.warning("Sabiana WebSocket connection error: %s", err)
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected error in Sabiana WebSocket: %s", err)

            if self._stop_event.is_set():
                break

            if connected_duration >= _BACKOFF_RESET_AFTER_SECONDS:
                # Reset backoff only after a meaningfully stable connection.
                backoff = _INITIAL_BACKOFF
            else:
                # Double backoff on repeated failures or short-lived connections.
                backoff = min(backoff * 2, _MAX_BACKOFF)

            _LOGGER.debug(
                "Sabiana WebSocket disconnected; reconnecting in %d seconds", backoff
            )
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass

    # ------------------------------------------------------------------
    # Connection handshake + message loop
    # ------------------------------------------------------------------

    async def _connect(self) -> float:
        """Perform the Socket.IO handshake and run the receive loop."""
        session = async_get_clientsession(self._hass)
        connected_at = time.monotonic()

        # Ensure we have a valid JWT before starting
        await self._client.async_ensure_authenticated()
        token = self._client.token
        if not token:
            raise SabianaAuthError("No authentication token available")

        base_headers = {
            "X-Requested-With": APP_ID_HEADER,
            "Origin": WEBSOCKET_ORIGIN,
        }

        # ----------------------------------------------------------------
        # Step 1 – GET polling handshake → obtain sid
        # ----------------------------------------------------------------
        handshake_url = (
            f"{WEBSOCKET_BASE_URL}/socket.io/?EIO=4&transport=polling"
            f"&t={self._socketio_timestamp()}"
        )
        async with session.get(handshake_url, headers=base_headers) as resp:
            if resp.status != 200:
                raise SabianaApiError(
                    f"WebSocket handshake GET failed: HTTP {resp.status}"
                )
            raw = await resp.text()
        _LOGGER.debug("Sabiana WebSocket handshake raw response: %s", raw)

        # Engine.IO wraps the JSON in "0{...}"
        json_start = raw.find("{")
        if json_start == -1:
            raise SabianaApiError(f"Unexpected handshake response: {raw!r}")
        try:
            handshake_data = json.loads(raw[json_start:])
        except json.JSONDecodeError as err:
            raise SabianaApiError(f"Cannot parse handshake JSON: {err}") from err

        sid = handshake_data.get("sid")
        if not sid:
            raise SabianaApiError("No sid in handshake response")
        _LOGGER.debug("Sabiana WebSocket handshake ok, sid=%s", sid)

        # ----------------------------------------------------------------
        # Step 2 – POST auth: send token as Socket.IO connect payload
        # ----------------------------------------------------------------
        auth_url = (
            f"{WEBSOCKET_BASE_URL}/socket.io/?EIO=4&transport=polling"
            f"&t={self._socketio_timestamp()}&sid={sid}"
        )
        auth_body = f'40{json.dumps({"token": token})}'
        auth_headers = {
            **base_headers,
            "Content-Type": "text/plain;charset=UTF-8",
        }
        _LOGGER.debug(
            "Sabiana WebSocket auth POST: sid=%s payload=%s",
            sid,
            '{"token":"<redacted>"}',
        )
        async with session.post(
            auth_url, data=auth_body, headers=auth_headers
        ) as auth_resp:
            if auth_resp.status != 200:
                text = await auth_resp.text()
                if auth_resp.status == 401:
                    # Token expired – refresh once and propagate to retry
                    await self._client.async_refresh_token()
                    raise SabianaAuthError("Token rejected by WebSocket server (refreshed)")
                raise SabianaApiError(
                    f"WebSocket auth POST failed: HTTP {auth_resp.status}: {text}"
                )
        _LOGGER.debug("Sabiana WebSocket auth POST accepted")

        # Step 2b – Drain the polling connect ack before upgrading transport.
        connect_ack_url = (
            f"{WEBSOCKET_BASE_URL}/socket.io/?EIO=4&transport=polling"
            f"&t={self._socketio_timestamp()}&sid={sid}"
        )
        async with session.get(connect_ack_url, headers=base_headers) as connect_resp:
            if connect_resp.status != 200:
                raise SabianaApiError(
                    f"WebSocket auth ACK GET failed: HTTP {connect_resp.status}"
                )
            connect_ack = await connect_resp.text()
        _LOGGER.debug("Sabiana WebSocket auth ACK response: %s", connect_ack)

        if _SIO_CONNECT_ACK not in connect_ack:
            _LOGGER.debug(
                "Sabiana WebSocket auth ACK response did not include connect frame: %r",
                connect_ack,
            )

        # ----------------------------------------------------------------
        # Step 3 – Upgrade to WebSocket
        # ----------------------------------------------------------------
        ws_url = (
            f"{WEBSOCKET_WSS_URL}/socket.io/?EIO=4&transport=websocket&sid={sid}"
        )
        ws_headers = {
            "Origin": WEBSOCKET_ORIGIN,
        }

        async with session.ws_connect(
            ws_url, headers=ws_headers, heartbeat=None
        ) as ws:
            _LOGGER.debug("Sabiana WebSocket connection established")

            # Send probe to confirm transport upgrade
            await ws.send_str(_EIO_PROBE_REQUEST)
            _LOGGER.debug("Sabiana WebSocket sent frame: %s", _EIO_PROBE_REQUEST)

            upgrade_confirmed = False

            async for msg in ws:
                if self._stop_event.is_set():
                    await ws.close()
                    return

                if msg.type == WSMsgType.TEXT:
                    data: str = msg.data
                    _LOGGER.debug("Sabiana WebSocket received frame: %s", data)

                    if not upgrade_confirmed:
                        # Expect server probe response, then send upgrade packet
                        if data == _EIO_PROBE_RESPONSE:
                            await ws.send_str(_EIO_UPGRADE)
                            _LOGGER.debug("Sabiana WebSocket sent frame: %s", _EIO_UPGRADE)
                            upgrade_confirmed = True
                            _LOGGER.debug("Sabiana WebSocket transport upgrade complete")
                        continue

                    if data == _EIO_PING:
                        # Engine.IO heartbeat – respond with pong
                        await ws.send_str(_EIO_PONG)
                        _LOGGER.debug("Sabiana WebSocket sent frame: %s", _EIO_PONG)

                    elif data.startswith(_SIO_EVENT_PREFIX):
                        # Socket.IO event: "42[...]"
                        await self._handle_event(data[len(_SIO_EVENT_PREFIX):])
                    else:
                        _LOGGER.debug("Sabiana WebSocket unhandled text frame: %s", data)

                elif msg.type in (WSMsgType.CLOSED, WSMsgType.CLOSING):
                    _LOGGER.debug("Sabiana WebSocket closed by server")
                    break

                elif msg.type == WSMsgType.ERROR:
                    _LOGGER.warning("Sabiana WebSocket error frame: %s", msg.data)
                    break

        return time.monotonic() - connected_at

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def _handle_event(self, payload: str) -> None:
        """Parse a Socket.IO event payload and dispatch device data."""
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            _LOGGER.debug("Sabiana WebSocket: cannot parse event JSON: %r", payload)
            return

        if not isinstance(event, list) or len(event) < 2:
            return

        event_name = event[0]
        if event_name != "data":
            return

        body = event[1]
        if not isinstance(body, dict):
            return

        device_id: str | None = body.get("device")
        hex_data: str | None = body.get("data")

        if device_id and hex_data:
            _LOGGER.debug(
                "Sabiana WebSocket data event: device=%s data=%s", device_id, hex_data
            )
            self._on_device_data(device_id, hex_data)

    @staticmethod
    def _socketio_timestamp() -> str:
        """Return a cache-busting value for Engine.IO polling requests."""
        return str(time.time_ns())
