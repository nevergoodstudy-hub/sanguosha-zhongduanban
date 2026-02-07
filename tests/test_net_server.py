# -*- coding: utf-8 -*-
"""
服务端测试 (M4-T02)
测试房间管理、消息路由、断线重连
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from net.protocol import MsgType, RoomState, ServerMsg, ClientMsg
from net.server import GameServer, Room, ConnectedPlayer


# ==================== Room 数据模型测试 ====================

class TestRoom:
    def test_player_count(self):
        room = Room(room_id="r1", host_id=1, max_players=4)
        assert room.player_count == 0
        room.players[1] = MagicMock()
        assert room.player_count == 1

    def test_is_full(self):
        room = Room(room_id="r1", host_id=1, max_players=2)
        room.players[1] = MagicMock()
        assert not room.is_full
        room.players[2] = MagicMock()
        assert room.is_full

    def test_player_list_data(self):
        room = Room(room_id="r1", host_id=1)
        p = ConnectedPlayer(player_id=1, name="A", websocket=None)
        room.players[1] = p
        data = room.player_list_data()
        assert len(data) == 1
        assert data[0]["player_id"] == 1
        assert data[0]["name"] == "A"

    def test_next_seq(self):
        room = Room(room_id="r1", host_id=1)
        assert room.next_seq() == 1
        assert room.next_seq() == 2
        assert room.next_seq() == 3

    def test_initial_state(self):
        room = Room(room_id="r1", host_id=1)
        assert room.state == RoomState.WAITING
        assert room.engine is None
        assert room.event_log == []


# ==================== GameServer 测试 ====================

class TestGameServer:
    def test_init(self):
        server = GameServer(host="localhost", port=9999)
        assert server.host == "localhost"
        assert server.port == 9999
        assert len(server.connections) == 0
        assert len(server.rooms) == 0

    def test_assign_player_id(self):
        server = GameServer()
        assert server._assign_player_id() == 1
        assert server._assign_player_id() == 2
        assert server._assign_player_id() == 3

    @pytest.mark.asyncio
    async def test_register(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)
        assert player.player_id == 1
        assert player.name == "玩家1"
        assert 1 in server.connections
        assert ws in server.ws_to_player

    @pytest.mark.asyncio
    async def test_unregister(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)
        await server._unregister(ws)
        assert ws not in server.ws_to_player
        assert player.player_id not in server.connections

    @pytest.mark.asyncio
    async def test_unregister_with_room(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)

        # 创建房间并加入
        room = Room(room_id="test-room", host_id=player.player_id)
        room.players[player.player_id] = player
        player.room_id = "test-room"
        server.rooms["test-room"] = room

        await server._unregister(ws)
        # 房间应被清理
        assert "test-room" not in server.rooms

    @pytest.mark.asyncio
    async def test_send(self):
        server = GameServer()
        ws = AsyncMock()
        player = ConnectedPlayer(player_id=1, name="A", websocket=ws)
        msg = ServerMsg.heartbeat_ack()
        await server._send(player, msg)
        ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_room(self):
        server = GameServer()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        p1 = ConnectedPlayer(player_id=1, name="A", websocket=ws1)
        p2 = ConnectedPlayer(player_id=2, name="B", websocket=ws2)
        room = Room(room_id="r1", host_id=1)
        room.players[1] = p1
        room.players[2] = p2

        msg = ServerMsg.heartbeat_ack()
        await server._broadcast_room(room, msg)
        ws1.send.assert_called_once()
        ws2.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_room_exclude(self):
        server = GameServer()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        p1 = ConnectedPlayer(player_id=1, name="A", websocket=ws1)
        p2 = ConnectedPlayer(player_id=2, name="B", websocket=ws2)
        room = Room(room_id="r1", host_id=1)
        room.players[1] = p1
        room.players[2] = p2

        msg = ServerMsg.heartbeat_ack()
        await server._broadcast_room(room, msg, exclude=1)
        ws1.send.assert_not_called()
        ws2.send.assert_called_once()


# ==================== 消息处理器测试 ====================

class TestHandlers:
    @pytest.mark.asyncio
    async def test_heartbeat(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)
        msg = ClientMsg.heartbeat(player.player_id)
        await server._handle_heartbeat(player, msg)
        ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_room_create(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)
        msg = ClientMsg.room_create(player.player_id, "Host", max_players=4)
        await server._handle_room_create(player, msg)
        assert player.room_id is not None
        assert len(server.rooms) == 1
        room = list(server.rooms.values())[0]
        assert room.host_id == player.player_id
        assert player.name == "Host"

    @pytest.mark.asyncio
    async def test_room_create_already_in_room(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)
        player.room_id = "existing-room"
        msg = ClientMsg.room_create(player.player_id, "Host")
        await server._handle_room_create(player, msg)
        # 应发送错误
        assert ws.send.call_count == 1

    @pytest.mark.asyncio
    async def test_room_join(self):
        server = GameServer()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        p1 = await server._register(ws1)
        p2 = await server._register(ws2)

        # p1 创建房间
        create_msg = ClientMsg.room_create(p1.player_id, "Host")
        await server._handle_room_create(p1, create_msg)
        room_id = p1.room_id

        # p2 加入房间
        join_msg = ClientMsg.room_join(p2.player_id, "Guest", room_id)
        await server._handle_room_join(p2, join_msg)
        assert p2.room_id == room_id
        assert len(server.rooms[room_id].players) == 2

    @pytest.mark.asyncio
    async def test_room_join_nonexistent(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)
        msg = ClientMsg.room_join(player.player_id, "A", "no-such-room")
        await server._handle_room_join(player, msg)
        assert player.room_id is None

    @pytest.mark.asyncio
    async def test_room_leave(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)

        create_msg = ClientMsg.room_create(player.player_id, "Host")
        await server._handle_room_create(player, create_msg)
        assert player.room_id is not None

        leave_msg = ClientMsg.room_leave(player.player_id)
        await server._handle_room_leave(player, leave_msg)
        assert player.room_id is None

    @pytest.mark.asyncio
    async def test_room_list(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)

        # 创建一个房间
        server.rooms["r1"] = Room(room_id="r1", host_id=1, max_players=4)

        msg = ClientMsg.room_list()
        await server._handle_room_list(player, msg)
        ws.send.assert_called()

    @pytest.mark.asyncio
    async def test_room_ready(self):
        server = GameServer()
        ws = AsyncMock()
        player = await server._register(ws)

        create_msg = ClientMsg.room_create(player.player_id, "Host")
        await server._handle_room_create(player, create_msg)

        ready_msg = ClientMsg.room_ready(player.player_id, ready=True)
        await server._handle_room_ready(player, ready_msg)
        assert player.ready is True

    @pytest.mark.asyncio
    async def test_room_start_not_host(self):
        server = GameServer()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        p1 = await server._register(ws1)
        p2 = await server._register(ws2)

        create_msg = ClientMsg.room_create(p1.player_id, "Host")
        await server._handle_room_create(p1, create_msg)
        room_id = p1.room_id

        join_msg = ClientMsg.room_join(p2.player_id, "Guest", room_id)
        await server._handle_room_join(p2, join_msg)

        # p2 (非房主) 尝试开始 → 应报错
        start_msg = ClientMsg.room_start(p2.player_id)
        await server._handle_room_start(p2, start_msg)
        # 房间状态应仍为 WAITING
        assert server.rooms[room_id].state == RoomState.WAITING


# ==================== 断线重连测试 ====================

class TestReconnect:
    @pytest.mark.asyncio
    async def test_reconnect_replays_events(self):
        server = GameServer()
        ws = AsyncMock()
        player = ConnectedPlayer(player_id=1, name="A", websocket=ws)

        room = Room(room_id="r1", host_id=1)
        server.rooms["r1"] = room

        # 模拟3个事件
        for i in range(3):
            seq = room.next_seq()
            room.event_log.append(
                ServerMsg.game_event("test", {"i": i}, seq=seq)
            )

        # 玩家在 seq=1 之后断线, 重连时 last_seq=1
        result = await server.reconnect_player(player, "r1", last_seq=1)
        assert result is True
        # 应重放 seq=2 和 seq=3 两条
        assert ws.send.call_count == 2

    @pytest.mark.asyncio
    async def test_reconnect_room_not_exist(self):
        server = GameServer()
        ws = AsyncMock()
        player = ConnectedPlayer(player_id=1, name="A", websocket=ws)
        result = await server.reconnect_player(player, "no-room", 0)
        assert result is False


# ==================== 广播事件测试 ====================

class TestBroadcastGameEvent:
    @pytest.mark.asyncio
    async def test_event_appended_to_log(self):
        server = GameServer()
        ws = AsyncMock()
        p = ConnectedPlayer(player_id=1, name="A", websocket=ws)
        room = Room(room_id="r1", host_id=1)
        room.players[1] = p

        await server._broadcast_game_event(room, "damage", {"amount": 1})
        assert len(room.event_log) == 1
        assert room.event_log[0].seq == 1
        assert room.event_log[0].data["event_type"] == "damage"

    @pytest.mark.asyncio
    async def test_seq_increments(self):
        server = GameServer()
        room = Room(room_id="r1", host_id=1)
        ws = AsyncMock()
        p = ConnectedPlayer(player_id=1, name="A", websocket=ws)
        room.players[1] = p

        await server._broadcast_game_event(room, "e1", {})
        await server._broadcast_game_event(room, "e2", {})
        assert room.event_log[0].seq == 1
        assert room.event_log[1].seq == 2
