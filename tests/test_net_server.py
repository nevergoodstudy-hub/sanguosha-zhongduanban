"""
服务端测试 (M4-T02)
测试房间管理、消息路由、断线重连
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from net.protocol import ClientMsg, RoomState, ServerMsg
from net.server import ConnectedPlayer, GameServer, Room

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

    def test_get_serve_origins_disabled(self):
        server = GameServer(allowed_origins="")
        assert server._get_serve_origins() is None

    def test_get_serve_origins_enabled(self):
        server = GameServer(allowed_origins="https://b.example, https://a.example")
        assert server._get_serve_origins() == ["https://a.example", "https://b.example"]

    @pytest.mark.asyncio
    async def test_register(self):
        server = GameServer()
        ws = AsyncMock()
        ws.transport = MagicMock()
        ws.transport.get_extra_info.return_value = ("127.0.0.1", 12345)
        player = await server._register(ws)
        assert player.player_id == 1
        assert player.name == "玩家1"
        assert player.auth_token != ""  # 令牌已签发
        assert player.remote_ip == "127.0.0.1"
        assert 1 in server.connections
        assert ws in server.ws_to_player
        # 欢迎消息已发送
        ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister(self):
        server = GameServer()
        ws = AsyncMock()
        ws.transport = MagicMock()
        ws.transport.get_extra_info.return_value = ("127.0.0.1", 12345)
        player = await server._register(ws)
        await server._unregister(ws)
        assert ws not in server.ws_to_player
        assert player.player_id not in server.connections

    @pytest.mark.asyncio
    async def test_unregister_with_room(self):
        server = GameServer()
        ws = AsyncMock()
        ws.transport = MagicMock()
        ws.transport.get_extra_info.return_value = ("127.0.0.1", 12345)
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
    """_register 现在会发送欢迎消息，因此 handler 测试在 register 后重置 mock。"""

    async def _make_player(self, server: GameServer) -> tuple:
        ws = AsyncMock()
        ws.transport = MagicMock()
        ws.transport.get_extra_info.return_value = ("127.0.0.1", 12345)
        player = await server._register(ws)
        ws.reset_mock()  # 清除欢迎消息的 send 记录
        return ws, player

    @pytest.mark.asyncio
    async def test_heartbeat(self):
        server = GameServer()
        ws, player = await self._make_player(server)
        msg = ClientMsg.heartbeat(player.player_id)
        await server._handle_heartbeat(player, msg)
        ws.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_room_create(self):
        server = GameServer()
        ws, player = await self._make_player(server)
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
        ws, player = await self._make_player(server)
        player.room_id = "existing-room"
        msg = ClientMsg.room_create(player.player_id, "Host")
        await server._handle_room_create(player, msg)
        # 应发送错误
        assert ws.send.call_count == 1

    @pytest.mark.asyncio
    async def test_room_join(self):
        server = GameServer()
        ws1, p1 = await self._make_player(server)
        ws2, p2 = await self._make_player(server)

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
        ws, player = await self._make_player(server)
        msg = ClientMsg.room_join(player.player_id, "A", "no-such-room")
        await server._handle_room_join(player, msg)
        assert player.room_id is None

    @pytest.mark.asyncio
    async def test_room_leave(self):
        server = GameServer()
        ws, player = await self._make_player(server)

        create_msg = ClientMsg.room_create(player.player_id, "Host")
        await server._handle_room_create(player, create_msg)
        assert player.room_id is not None

        leave_msg = ClientMsg.room_leave(player.player_id)
        await server._handle_room_leave(player, leave_msg)
        assert player.room_id is None

    @pytest.mark.asyncio
    async def test_room_list(self):
        server = GameServer()
        ws, player = await self._make_player(server)

        # 创建一个房间
        server.rooms["r1"] = Room(room_id="r1", host_id=1, max_players=4)

        msg = ClientMsg.room_list()
        await server._handle_room_list(player, msg)
        ws.send.assert_called()

    @pytest.mark.asyncio
    async def test_room_ready(self):
        server = GameServer()
        ws, player = await self._make_player(server)

        create_msg = ClientMsg.room_create(player.player_id, "Host")
        await server._handle_room_create(player, create_msg)

        ready_msg = ClientMsg.room_ready(player.player_id, ready=True)
        await server._handle_room_ready(player, ready_msg)
        assert player.ready is True

    @pytest.mark.asyncio
    async def test_room_start_not_host(self):
        server = GameServer()
        ws1, p1 = await self._make_player(server)
        ws2, p2 = await self._make_player(server)

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
            room.event_log.append(ServerMsg.game_event("test", {"i": i}, seq=seq))

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


# ==================== 网络安全测试 (Phase 4.4) ====================


class TestSecurity:
    """验证 Phase 4.4 网络安全加固"""

    # ---------- ConnectionTokenManager ----------

    def test_token_issue_and_verify(self):
        from net.security import ConnectionTokenManager

        mgr = ConnectionTokenManager()
        token = mgr.issue(player_id=1)
        assert isinstance(token, str)
        assert len(token) > 20  # secrets.token_urlsafe(32) ≈ 43 chars
        assert mgr.verify(token, expected_player_id=1)

    def test_token_verify_wrong_player(self):
        from net.security import ConnectionTokenManager

        mgr = ConnectionTokenManager()
        token = mgr.issue(player_id=1)
        assert not mgr.verify(token, expected_player_id=2)

    def test_token_verify_wrong_token(self):
        from net.security import ConnectionTokenManager

        mgr = ConnectionTokenManager()
        mgr.issue(player_id=1)
        assert not mgr.verify("invalid-token", expected_player_id=1)

    def test_token_revoke(self):
        from net.security import ConnectionTokenManager

        mgr = ConnectionTokenManager()
        token = mgr.issue(player_id=1)
        mgr.revoke(player_id=1)
        assert not mgr.verify(token, expected_player_id=1)

    def test_token_expiry(self):
        import time

        from net.security import ConnectionTokenManager

        mgr = ConnectionTokenManager(expiry=0.01)  # 10ms expiry
        token = mgr.issue(player_id=1)
        time.sleep(0.02)
        assert not mgr.verify(token, expected_player_id=1)

    def test_token_reissue_replaces_old(self):
        from net.security import ConnectionTokenManager

        mgr = ConnectionTokenManager()
        t1 = mgr.issue(player_id=1)
        t2 = mgr.issue(player_id=1)
        assert t1 != t2
        assert not mgr.verify(t1, expected_player_id=1)
        assert mgr.verify(t2, expected_player_id=1)

    def test_cleanup_expired(self):
        import time

        from net.security import ConnectionTokenManager

        mgr = ConnectionTokenManager(expiry=0.01)
        mgr.issue(player_id=1)
        mgr.issue(player_id=2)
        time.sleep(0.02)
        cleaned = mgr.cleanup_expired()
        assert cleaned == 2
        assert mgr.active_count == 0

    # ---------- IPConnectionTracker ----------

    def test_ip_tracker_limit(self):
        from net.security import IPConnectionTracker

        tracker = IPConnectionTracker(max_per_ip=2)
        assert tracker.can_connect("1.2.3.4")
        tracker.add("1.2.3.4")
        tracker.add("1.2.3.4")
        assert not tracker.can_connect("1.2.3.4")
        # 其他 IP 不受影响
        assert tracker.can_connect("5.6.7.8")

    def test_ip_tracker_remove(self):
        from net.security import IPConnectionTracker

        tracker = IPConnectionTracker(max_per_ip=2)
        tracker.add("1.2.3.4")
        tracker.add("1.2.3.4")
        assert not tracker.can_connect("1.2.3.4")
        tracker.remove("1.2.3.4")
        assert tracker.can_connect("1.2.3.4")

    # ---------- sanitize_chat_message ----------

    def test_sanitize_removes_html(self):
        from net.security import sanitize_chat_message

        assert (
            sanitize_chat_message("<script>alert(1)</script>")
            == "&lt;script&gt;alert(1)&lt;/script&gt;"
        )

    def test_sanitize_truncates(self):
        from net.security import sanitize_chat_message

        long_text = "a" * 1000
        assert len(sanitize_chat_message(long_text, max_length=100)) == 100

    def test_sanitize_strips_whitespace(self):
        from net.security import sanitize_chat_message

        assert sanitize_chat_message("  hello  ") == "hello"

    # ---------- 服务器连接限制 ----------

    @pytest.mark.asyncio
    async def test_server_connection_cap(self):
        """Connection cap rejects when full"""
        server = GameServer(max_connections=2)
        ws1 = AsyncMock()
        ws1.transport = MagicMock()
        ws1.transport.get_extra_info.return_value = ("10.0.0.1", 1)
        ws2 = AsyncMock()
        ws2.transport = MagicMock()
        ws2.transport.get_extra_info.return_value = ("10.0.0.2", 2)
        ws3 = AsyncMock()
        ws3.transport = MagicMock()
        ws3.transport.get_extra_info.return_value = ("10.0.0.3", 3)

        p1 = await server._register(ws1)
        p2 = await server._register(ws2)
        assert p1 is not None
        assert p2 is not None
        p3 = await server._register(ws3)
        assert p3 is None  # 拒绝
        ws3.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_per_ip_cap(self):
        """Per-IP cap rejects excess connections from same IP"""
        server = GameServer(max_connections_per_ip=1)
        ws1 = AsyncMock()
        ws1.transport = MagicMock()
        ws1.transport.get_extra_info.return_value = ("10.0.0.1", 1)
        ws2 = AsyncMock()
        ws2.transport = MagicMock()
        ws2.transport.get_extra_info.return_value = ("10.0.0.1", 2)

        p1 = await server._register(ws1)
        assert p1 is not None
        p2 = await server._register(ws2)
        assert p2 is None
        ws2.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_welcome_message_contains_token(self):
        """Register sends welcome with token and player_id"""
        server = GameServer()
        ws = AsyncMock()
        ws.transport = MagicMock()
        ws.transport.get_extra_info.return_value = ("127.0.0.1", 1)
        player = await server._register(ws)
        assert player is not None
        import json

        call_args = ws.send.call_args[0][0]
        data = json.loads(call_args)
        assert data["type"] == "heartbeat_ack"
        assert "token" in data["data"]
        assert data["data"]["player_id"] == player.player_id

    # ---------- 速率限制 ----------

    def test_rate_limit_blocks_flood(self):
        """Rate limiter blocks when messages exceed threshold"""
        server = GameServer(rate_limit_max_msgs=3, rate_limit_window=10.0)
        player = ConnectedPlayer(player_id=1, name="A", websocket=AsyncMock())
        assert server._check_rate_limit(player) is True
        assert server._check_rate_limit(player) is True
        assert server._check_rate_limit(player) is True
        assert server._check_rate_limit(player) is False  # 4th blocked

    # ---------- 聊天净化 ----------

    @pytest.mark.asyncio
    async def test_chat_sanitized(self):
        """Chat messages are sanitized before broadcast"""
        server = GameServer()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        p1 = ConnectedPlayer(player_id=1, name="A", websocket=ws1)
        p2 = ConnectedPlayer(player_id=2, name="B", websocket=ws2)
        room = Room(room_id="r1", host_id=1)
        room.players[1] = p1
        room.players[2] = p2
        p1.room_id = "r1"
        server.rooms["r1"] = room

        msg = ClientMsg.chat(1, "<img src=x onerror=alert(1)>hello")
        await server._handle_chat(p1, msg)
        import json

        call_args = ws2.send.call_args[0][0]
        data = json.loads(call_args)
        text = data["data"]["message"]
        # 原始 HTML 标签已被转义，不会作为活动内容执行
        assert "<img" not in text
        assert "<script" not in text
        # 转义后的安全形式应存在
        assert "&lt;" in text
        assert "hello" in text
