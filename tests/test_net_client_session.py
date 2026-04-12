"""Tests for the extracted client transport/session lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest

from net.client_session import ClientSession


class _AsyncMessages:
    def __init__(self, messages: list[bytes | str]) -> None:
        self._messages = list(messages)

    def __aiter__(self) -> AsyncIterator[bytes | str]:
        return self

    async def __anext__(self) -> bytes | str:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


class TestClientSession:
    @pytest.mark.asyncio
    async def test_connect_invokes_callback(self) -> None:
        websocket = AsyncMock()
        on_connect = AsyncMock()
        session = ClientSession("ws://localhost:8765", on_connect=on_connect)

        with patch("websockets.connect", AsyncMock(return_value=websocket)):
            result = await session.connect()

        assert result is True
        assert session.is_connected is True
        on_connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_text_returns_false_when_not_connected(self) -> None:
        session = ClientSession("ws://localhost:8765")

        result = await session.send_text("payload")

        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_closes_socket_and_invokes_callback(self) -> None:
        websocket = AsyncMock()
        on_disconnect = AsyncMock()
        session = ClientSession("ws://localhost:8765", on_disconnect=on_disconnect)
        session._ws = websocket
        session._connected = True

        await session.disconnect()

        websocket.close.assert_awaited_once()
        on_disconnect.assert_awaited_once()
        assert session.is_connected is False

    @pytest.mark.asyncio
    async def test_receive_loop_dispatches_decoded_messages(self) -> None:
        on_message = AsyncMock()
        session = ClientSession("ws://localhost:8765", on_message=on_message)
        session._ws = _AsyncMessages([b"first", "second"])
        session._connected = True

        await session._receive_loop()

        assert on_message.await_count == 2
        assert on_message.await_args_list[0].args == ("first",)
        assert on_message.await_args_list[1].args == ("second",)

    @pytest.mark.asyncio
    async def test_reconnect_invokes_hook_after_success(self) -> None:
        on_reconnect = AsyncMock()
        session = ClientSession(
            "ws://localhost:8765",
            reconnect_delay=0.1,
            max_reconnect_attempts=2,
            on_reconnect=on_reconnect,
        )
        session.connect = AsyncMock(side_effect=[False, True])  # type: ignore[method-assign]

        with patch("net.client_session.asyncio.sleep", AsyncMock()):
            result = await session._reconnect()

        assert result is True
        assert session.connect.await_count == 2
        on_reconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_heartbeat_loop_uses_callback(self) -> None:
        async def stop_after_heartbeat() -> None:
            session._running = False

        heartbeat = AsyncMock(side_effect=stop_after_heartbeat)
        session = ClientSession(
            "ws://localhost:8765",
            heartbeat_interval=0.1,
            send_heartbeat=heartbeat,
        )
        session._running = True
        session._connected = True
        session._ws = object()

        async def stop_sleep(_: float) -> None:
            return None

        with patch("net.client_session.asyncio.sleep", stop_sleep):
            await session._heartbeat_loop()

        heartbeat.assert_awaited_once()
        assert session._running is False
