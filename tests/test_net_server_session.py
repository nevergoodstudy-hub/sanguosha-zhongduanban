from unittest.mock import AsyncMock

import pytest

from net.protocol import RoomState, ServerMsg
from net.server_types import ConnectedPlayer, Room


class _FakeRateLimiter:
    def __init__(self) -> None:
        self.removed: list[int] = []

    def remove_player(self, player_id: int) -> None:
        self.removed.append(player_id)


class _FakeTokenManager:
    def __init__(self) -> None:
        self.verify_result = True
        self.verify_calls: list[tuple[str, int]] = []
        self.revoked_player_ids: list[int] = []

    def verify(self, token: str, expected_player_id: int) -> bool:
        self.verify_calls.append((token, expected_player_id))
        return self.verify_result

    def revoke(self, *, player_id: int | None = None, token: str | None = None) -> None:
        if player_id is not None:
            self.revoked_player_ids.append(player_id)


class _FakeServer:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.sent_messages: list[tuple[int, ServerMsg]] = []
        self.broadcast_updates: list[str] = []
        self._rate_limiter = _FakeRateLimiter()
        self._token_manager = _FakeTokenManager()

    async def _send(self, player: ConnectedPlayer, msg: ServerMsg) -> None:
        self.sent_messages.append((player.player_id, msg))

    async def _broadcast_room_update(self, room: Room) -> None:
        self.broadcast_updates.append(room.room_id)


@pytest.mark.asyncio
async def test_leave_room_removes_player_and_deletes_empty_room():
    from net.server_session import ServerSessionManager

    server = _FakeServer()
    manager = ServerSessionManager(server)
    player = ConnectedPlayer(
        player_id=1,
        name="Host",
        websocket=AsyncMock(),
        room_id="r1",
        ready=True,
    )
    room = Room(room_id="r1", host_id=1, state=RoomState.WAITING)
    room.players[player.player_id] = player
    server.rooms[room.room_id] = room

    await manager.leave_room(player)

    assert player.room_id is None
    assert player.ready is False
    assert room.players == {}
    assert server.broadcast_updates == ["r1"]
    assert "r1" not in server.rooms


@pytest.mark.asyncio
async def test_unregister_player_clears_room_and_security_state():
    from net.server_session import ServerSessionManager

    server = _FakeServer()
    manager = ServerSessionManager(server)
    player = ConnectedPlayer(
        player_id=9,
        name="Guest",
        websocket=AsyncMock(),
        room_id="room-a",
        ready=True,
    )
    room = Room(room_id="room-a", host_id=2, state=RoomState.WAITING)
    room.players[player.player_id] = player
    server.rooms[room.room_id] = room

    await manager.unregister_player(player)

    assert server._rate_limiter.removed == [9]
    assert server._token_manager.revoked_player_ids == [9]
    assert player.room_id is None
    assert "room-a" not in server.rooms


@pytest.mark.asyncio
async def test_reconnect_player_replays_missed_events():
    from net.server_session import ServerSessionManager

    server = _FakeServer()
    manager = ServerSessionManager(server)
    player = ConnectedPlayer(player_id=3, name="A", websocket=AsyncMock())
    room = Room(room_id="r1", host_id=1, state=RoomState.PLAYING)
    server.rooms[room.room_id] = room

    for i in range(3):
        room.event_log.append(ServerMsg.game_event("test", {"i": i}, seq=room.next_seq()))

    result = await manager.reconnect_player(player, "r1", last_seq=1, token="token-1")

    assert result is True
    assert server._token_manager.verify_calls == [("token-1", 3)]
    assert player.room_id == "r1"
    assert room.players[player.player_id] is player
    assert [msg.seq for _, msg in server.sent_messages] == [2, 3]


@pytest.mark.asyncio
async def test_reconnect_player_rejects_invalid_token():
    from net.server_session import ServerSessionManager

    server = _FakeServer()
    server._token_manager.verify_result = False
    manager = ServerSessionManager(server)
    player = ConnectedPlayer(player_id=5, name="A", websocket=AsyncMock())
    room = Room(room_id="r1", host_id=1, state=RoomState.PLAYING)
    server.rooms[room.room_id] = room

    result = await manager.reconnect_player(player, "r1", last_seq=0, token="bad-token")

    assert result is False
    assert player.player_id not in room.players
    assert len(server.sent_messages) == 1
    _, message = server.sent_messages[0]
    assert message.type.name == "ERROR"
    assert message.data["error_code"] == "E_AUTH_INVALID_TOKEN"
