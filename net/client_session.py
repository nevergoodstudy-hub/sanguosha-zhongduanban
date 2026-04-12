"""Client transport/session lifecycle helpers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)


class ClientSession:
    """Own transport lifecycle for the WebSocket client."""

    def __init__(
        self,
        server_url: str,
        *,
        auto_reconnect: bool = True,
        reconnect_delay: float = 2.0,
        max_reconnect_attempts: int = 5,
        heartbeat_interval: float = 15.0,
        on_connect: Callable[[], Any] | None = None,
        on_disconnect: Callable[[], Any] | None = None,
        on_message: Callable[[str], Any] | None = None,
        on_reconnect: Callable[[], Any] | None = None,
        send_heartbeat: Callable[[], Any] | None = None,
    ) -> None:
        self.server_url = server_url
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self.heartbeat_interval = heartbeat_interval

        self._ws: ClientConnection | Any | None = None
        self._connected = False
        self._running = False

        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._on_message = on_message
        self._on_reconnect = on_reconnect
        self._send_heartbeat = send_heartbeat

    async def _invoke_callback(self, callback: Callable[..., Any], *args: Any) -> None:
        """Run sync or async callbacks safely."""
        try:
            result = callback(*args)
            if isawaitable(result):
                await result
        except Exception as exc:
            logger.warning("Client session callback failed: %s", exc)

    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    async def connect(self) -> bool:
        """Open a WebSocket connection."""
        try:
            import websockets

            self._ws = await websockets.connect(self.server_url)
            self._connected = True
            logger.info("Connected to %s", self.server_url)
            if self._on_connect is not None:
                await self._invoke_callback(self._on_connect)
            return True
        except ImportError:
            logger.error("websockets is required: pip install websockets")
            return False
        except Exception as exc:
            logger.error("Connect failed: %s", exc)
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Close the current WebSocket connection."""
        had_connection = self._connected or self._ws is not None
        websocket = self._ws

        self._running = False
        self._connected = False
        self._ws = None

        if websocket is not None:
            with suppress(Exception):
                await websocket.close()

        logger.info("Disconnected from %s", self.server_url)
        if had_connection and self._on_disconnect is not None:
            await self._invoke_callback(self._on_disconnect)

    async def send_text(self, payload: str) -> bool:
        """Send a serialized payload to the server."""
        if not self.is_connected:
            logger.warning("Cannot send payload while disconnected")
            return False

        websocket = self._ws
        if websocket is None:
            logger.warning("Cannot send payload without a websocket")
            return False

        try:
            await websocket.send(payload)
            return True
        except Exception as exc:
            logger.warning("Send failed: %s", exc)
            self._connected = False
            return False

    async def _receive_loop(self) -> None:
        """Receive raw messages from the server."""
        websocket = self._ws
        if websocket is None:
            return

        try:
            async for raw in websocket:
                payload = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                if self._on_message is not None:
                    await self._invoke_callback(self._on_message, payload)
        except Exception as exc:
            logger.warning("Receive loop stopped: %s", exc)
            self._connected = False

    async def _heartbeat_loop(self) -> None:
        """Emit application-level heartbeats while connected."""
        if self._send_heartbeat is None:
            return

        while self._running and self.is_connected:
            await asyncio.sleep(self.heartbeat_interval)
            if self._running and self.is_connected:
                await self._invoke_callback(self._send_heartbeat)

    async def _reconnect(self) -> bool:
        """Reconnect and run the reconnect hook if one is registered."""
        for attempt in range(1, self.max_reconnect_attempts + 1):
            logger.info(
                "Reconnect attempt %s/%s",
                attempt,
                self.max_reconnect_attempts,
            )
            await asyncio.sleep(self.reconnect_delay * attempt)

            if await self.connect():
                if self._on_reconnect is not None:
                    await self._invoke_callback(self._on_reconnect)
                return True

        logger.error("Reconnect failed after %s attempts", self.max_reconnect_attempts)
        return False

    async def run(self) -> None:
        """Run the receive/heartbeat lifecycle."""
        if not await self.connect():
            return

        self._running = True

        try:
            await asyncio.gather(
                self._receive_loop(),
                self._heartbeat_loop(),
            )
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.warning("Client session failed: %s", exc)
        finally:
            if self._running and self.auto_reconnect:
                if await self._reconnect():
                    await self.run()
            else:
                await self.disconnect()
