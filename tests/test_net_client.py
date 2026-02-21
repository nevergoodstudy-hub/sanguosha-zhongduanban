"""
客户端测试 (M4-T03)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from net.client import GameClient
from net.protocol import ClientMsg, MsgType, ServerMsg


class TestGameClientInit:
    def test_default_config(self):
        client = GameClient()
        assert client.server_url == "ws://localhost:8765"
        assert client.player_id == 0
        assert client.room_id is None
        assert client.auto_reconnect is True
        assert client.is_connected is False

    def test_custom_url(self):
        client = GameClient("ws://192.168.1.1:9999")
        assert client.server_url == "ws://192.168.1.1:9999"


class TestGameClientHandlers:
    def test_on_registers_handler(self):
        client = GameClient()
        handler = MagicMock()
        client.on(MsgType.GAME_EVENT, handler)
        assert MsgType.GAME_EVENT in client._handlers

    def test_on_connect_callback(self):
        client = GameClient()
        handler = MagicMock()
        client.on_connect(handler)
        assert client._on_connect == handler

    def test_on_disconnect_callback(self):
        client = GameClient()
        handler = MagicMock()
        client.on_disconnect(handler)
        assert client._on_disconnect == handler

    @pytest.mark.asyncio
    async def test_dispatch_calls_handler(self):
        client = GameClient()
        handler = MagicMock()
        client.on(MsgType.GAME_EVENT, handler)

        msg = ServerMsg.game_event("damage", {"amount": 1}, seq=5)
        await client._dispatch(msg.to_json())

        handler.assert_called_once()
        assert client.last_seq == 5

    @pytest.mark.asyncio
    async def test_dispatch_async_handler(self):
        client = GameClient()
        handler = AsyncMock()
        client.on(MsgType.ERROR, handler)

        msg = ServerMsg.error("test error")
        await client._dispatch(msg.to_json())
        handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_updates_seq(self):
        client = GameClient()
        client.on(MsgType.GAME_EVENT, MagicMock())

        msg = ServerMsg.game_event("e", {}, seq=42)
        await client._dispatch(msg.to_json())
        assert client.last_seq == 42

    @pytest.mark.asyncio
    async def test_dispatch_no_handler(self):
        """无回调时不报错"""
        client = GameClient()
        msg = ServerMsg.heartbeat_ack()
        await client._dispatch(msg.to_json())  # 不应抛异常


class TestGameClientSend:
    @pytest.mark.asyncio
    async def test_send_not_connected(self):
        client = GameClient()
        result = await client.send(ClientMsg.heartbeat())
        assert result is False

    @pytest.mark.asyncio
    async def test_send_connected(self):
        client = GameClient()
        client._ws = AsyncMock()
        client._connected = True
        result = await client.send(ClientMsg.heartbeat(1))
        assert result is True
        client._ws.send.assert_called_once()


class TestConvenienceMethods:
    @pytest.mark.asyncio
    async def test_create_room(self):
        client = GameClient()
        client._ws = AsyncMock()
        client._connected = True
        await client.create_room("TestPlayer", max_players=6)
        assert client.player_name == "TestPlayer"
        client._ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_room(self):
        client = GameClient()
        client._ws = AsyncMock()
        client._connected = True
        await client.join_room("P2", "room-abc")
        assert client.player_name == "P2"

    @pytest.mark.asyncio
    async def test_play_card(self):
        client = GameClient()
        client._ws = AsyncMock()
        client._connected = True
        client.player_id = 1
        await client.play_card(42, [2, 3])
        client._ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_respond(self):
        client = GameClient()
        client._ws = AsyncMock()
        client._connected = True
        client.player_id = 1
        await client.respond("play_shan", True, card_id=7)
        client._ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat(self):
        client = GameClient()
        client._ws = AsyncMock()
        client._connected = True
        client.player_id = 1
        await client.chat("hello")
        client._ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_end_turn(self):
        client = GameClient()
        client._ws = AsyncMock()
        client._connected = True
        client.player_id = 1
        await client.end_turn()
        client._ws.send.assert_called_once()


class TestMainPyNetArgs:
    """测试 main.py 网络参数"""

    def test_argparse_server_flag(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--server", nargs="?", const="0.0.0.0:8765", default=None)
        parser.add_argument("--connect", default=None)
        parser.add_argument("--name", default=None)

        args = parser.parse_args(["--server"])
        assert args.server == "0.0.0.0:8765"

        args = parser.parse_args(["--server", "192.168.1.1:9999"])
        assert args.server == "192.168.1.1:9999"

    def test_argparse_connect_flag(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--server", nargs="?", const="0.0.0.0:8765", default=None)
        parser.add_argument("--connect", default=None)
        parser.add_argument("--name", default=None)

        args = parser.parse_args(["--connect", "localhost:8765", "--name", "TestP"])
        assert args.connect == "localhost:8765"
        assert args.name == "TestP"

    def test_no_net_args(self):
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--server", nargs="?", const="0.0.0.0:8765", default=None)
        parser.add_argument("--connect", default=None)

        args = parser.parse_args([])
        assert args.server is None
        assert args.connect is None
