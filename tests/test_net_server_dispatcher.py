import time
from unittest.mock import AsyncMock

import pytest

from net.protocol import ClientMsg, MsgType
from net.server_types import ConnectedPlayer


class _FakeServer:
    def __init__(self):
        self.connections = {}
        self.ws_to_player = {}
        self.rooms = {}
        self.sent_messages = []
        self.rate_limit_calls = []
        self.allow_rate_limit = True
        self.reconnect_calls = []

    def _check_rate_limit(self, player: ConnectedPlayer) -> bool:
        self.rate_limit_calls.append(player.player_id)
        return self.allow_rate_limit

    async def _send(self, player: ConnectedPlayer, msg) -> None:
        self.sent_messages.append((player.player_id, msg))

    async def _broadcast_room_update(self, room) -> None:  # pragma: no cover - helper stub
        return None

    async def _broadcast_room(
        self, room, msg, exclude=None
    ) -> None:  # pragma: no cover - helper stub
        return None

    async def _broadcast_game_event(self, room, event_type, event_data) -> None:  # pragma: no cover
        return None

    async def reconnect_player(
        self, player, room_id, last_seq, token=""
    ) -> bool:  # pragma: no cover
        self.reconnect_calls.append((player.player_id, room_id, last_seq, token))
        return False

    async def _run_game(self, room) -> None:  # pragma: no cover - helper stub
        return None

    def _find_pending_request(self, room, player_id, request_id, request_type):  # pragma: no cover
        return None


@pytest.mark.asyncio
async def test_dispatch_heartbeat_skips_rate_limit_and_acknowledges():
    from net.server_dispatcher import ServerMessageDispatcher

    server = _FakeServer()
    websocket = AsyncMock()
    player = ConnectedPlayer(player_id=7, name="Tester", websocket=websocket)
    server.connections[player.player_id] = player
    server.ws_to_player[websocket] = player.player_id
    dispatcher = ServerMessageDispatcher(server)
    before = player.last_heartbeat

    await dispatcher.dispatch(websocket, ClientMsg.heartbeat().to_json())

    assert server.rate_limit_calls == []
    assert len(server.sent_messages) == 1
    _, message = server.sent_messages[0]
    assert message.type is MsgType.HEARTBEAT_ACK
    assert player.last_heartbeat >= before


@pytest.mark.asyncio
async def test_dispatch_rate_limited_non_heartbeat_sends_error():
    from net.server_dispatcher import ServerMessageDispatcher

    server = _FakeServer()
    server.allow_rate_limit = False
    websocket = AsyncMock()
    player = ConnectedPlayer(player_id=3, name="Tester", websocket=websocket)
    server.connections[player.player_id] = player
    server.ws_to_player[websocket] = player.player_id
    dispatcher = ServerMessageDispatcher(server)

    await dispatcher.dispatch(websocket, ClientMsg.room_list().to_json())

    assert server.rate_limit_calls == [player.player_id]
    assert len(server.sent_messages) == 1
    _, message = server.sent_messages[0]
    assert message.type is MsgType.ERROR
    assert message.data["code"] == 429
    assert message.data["error_code"] == "E_RATE_LIMITED"


@pytest.mark.asyncio
async def test_dispatch_unknown_type_returns_protocol_error():
    from net.server_dispatcher import ServerMessageDispatcher

    server = _FakeServer()
    websocket = AsyncMock()
    player = ConnectedPlayer(player_id=11, name="Tester", websocket=websocket)
    server.connections[player.player_id] = player
    server.ws_to_player[websocket] = player.player_id
    dispatcher = ServerMessageDispatcher(server)
    raw = f'{{"type":"definitely_unknown","player_id":999,"timestamp":{time.time()},"data":{{}}}}'

    await dispatcher.dispatch(websocket, raw)

    assert len(server.sent_messages) == 1
    _, message = server.sent_messages[0]
    assert message.type is MsgType.ERROR
    assert message.data["code"] == 400
    assert message.data["error_code"] == "E_PROTO_UNKNOWN_TYPE"
