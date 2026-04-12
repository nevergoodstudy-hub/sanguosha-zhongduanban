"""Game server message dispatching and handler coordination."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import TYPE_CHECKING

from i18n import t as _t

from .models import validate_client_message
from .protocol import ClientMsg, MsgType, RoomState, ServerMsg, parse_message
from .request_codec import decode_game_response
from .security import sanitize_chat_message
from .server_types import Room

if TYPE_CHECKING:
    from websockets.asyncio.server import ServerConnection

    from .server import GameServer
    from .server_types import ConnectedPlayer

logger = logging.getLogger(__name__)


class ServerMessageDispatcher:
    """Route validated client messages to the appropriate server handlers."""

    def __init__(self, server: GameServer):
        self.server = server
        self.handlers = {
            MsgType.HEARTBEAT: self.handle_heartbeat,
            MsgType.ROOM_CREATE: self.handle_room_create,
            MsgType.ROOM_JOIN: self.handle_room_join,
            MsgType.ROOM_LEAVE: self.handle_room_leave,
            MsgType.ROOM_LIST: self.handle_room_list,
            MsgType.ROOM_READY: self.handle_room_ready,
            MsgType.ROOM_START: self.handle_room_start,
            MsgType.GAME_ACTION: self.handle_game_action,
            MsgType.GAME_RESPONSE: self.handle_game_response,
            MsgType.HERO_CHOSEN: self.handle_hero_chosen,
            MsgType.CHAT: self.handle_chat,
        }

    def _resolve_player(self, websocket: ServerConnection) -> ConnectedPlayer | None:
        pid = self.server.ws_to_player.get(websocket)
        return self.server.connections.get(pid) if pid else None

    async def dispatch(self, websocket: ServerConnection, raw: str) -> None:
        """Validate, parse, rate-limit, and dispatch a raw client message."""
        try:
            try:
                validate_client_message(raw)
            except Exception as exc:
                logger.warning("Message validation failed: %s", exc)
                player = self._resolve_player(websocket)
                if player:
                    await self.server._send(
                        player,
                        ServerMsg.error(
                            _t("server.invalid_format"),
                            code=400,
                            error_code="E_PROTO_INVALID_FORMAT",
                        ),
                    )
                return

            type_str, _ = parse_message(raw)
            try:
                msg_type = MsgType(type_str)
            except ValueError:
                logger.warning("Unknown client message type: %s", type_str)
                player = self._resolve_player(websocket)
                if player:
                    await self.server._send(
                        player,
                        ServerMsg.error(
                            _t("server.unknown_type", type=type_str),
                            code=400,
                            error_code="E_PROTO_UNKNOWN_TYPE",
                        ),
                    )
                return

            client_msg = ClientMsg.from_json(raw)
            player = self._resolve_player(websocket)
            if not player:
                return

            if msg_type != MsgType.HEARTBEAT and not self.server._check_rate_limit(player):
                logger.warning(
                    "Rate limited player_id=%s message_type=%s",
                    player.player_id,
                    msg_type.value,
                )
                await self.server._send(
                    player,
                    ServerMsg.error(
                        _t("server.rate_limited"),
                        code=429,
                        error_code="E_RATE_LIMITED",
                    ),
                )
                return

            client_msg.player_id = player.player_id
            handler = self.handlers.get(msg_type)
            if handler:
                await handler(player, client_msg)
                return

            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.unknown_type", type=type_str),
                    code=400,
                    error_code="E_PROTO_UNKNOWN_TYPE",
                ),
            )
        except json.JSONDecodeError:
            logger.warning("Received invalid JSON payload")
        except ValueError as exc:
            logger.warning("Message parsing error: %s", exc)
        except Exception as exc:
            logger.exception("Unexpected dispatcher error: %s", exc)

    async def handle_heartbeat(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        player.last_heartbeat = time.time()
        await self.server._send(player, ServerMsg.heartbeat_ack())

    async def handle_room_create(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        if player.room_id:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.already_in_room"),
                    code=409,
                    error_code="E_ROOM_ALREADY_IN_ROOM",
                ),
            )
            return

        room_id = str(uuid.uuid4())[:8]
        player_name = msg.data.get("player_name", player.name)
        player.name = player_name
        max_players = msg.data.get("max_players", 4)
        ai_fill = msg.data.get("ai_fill", True)

        room = Room(
            room_id=room_id,
            host_id=player.player_id,
            max_players=max_players,
            ai_fill=ai_fill,
        )
        room.players[player.player_id] = player
        player.room_id = room_id
        self.server.rooms[room_id] = room

        logger.info("Room %s created by %s", room_id, player.name)
        await self.server._send(
            player,
            ServerMsg.room_created(
                room_id,
                {
                    "max_players": max_players,
                    "ai_fill": ai_fill,
                    "host_id": player.player_id,
                },
            ),
        )

    async def handle_room_join(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        if player.room_id:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.already_in_room"),
                    code=409,
                    error_code="E_ROOM_ALREADY_IN_ROOM",
                ),
            )
            return

        room_id = msg.data.get("room_id", "")
        reconnect = bool(msg.data.get("reconnect", False))
        reconnect_last_seq = int(msg.data.get("last_seq", 0))
        reconnect_token = msg.data.get("token", "")
        room = self.server.rooms.get(room_id)
        if not room:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.room_not_found"),
                    code=404,
                    error_code="E_ROOM_NOT_FOUND",
                ),
            )
            return

        if reconnect:
            if not reconnect_token:
                await self.server._send(
                    player,
                    ServerMsg.error(
                        _t("server.invalid_token"),
                        code=401,
                        error_code="E_AUTH_INVALID_TOKEN",
                    ),
                )
                return
            if not await self.server.reconnect_player(
                player,
                room_id,
                max(reconnect_last_seq, 0),
                token=reconnect_token,
            ):
                return
            await self.server._send(
                player,
                ServerMsg.room_joined(
                    room_id,
                    player.player_id,
                    player.name,
                    room.player_list_data(),
                ),
            )
            await self.server._broadcast_room_update(room)
            return

        if room.is_full:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.room_full"),
                    code=409,
                    error_code="E_ROOM_FULL",
                ),
            )
            return

        if room.state != RoomState.WAITING:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.game_started"),
                    code=409,
                    error_code="E_ROOM_ALREADY_PLAYING",
                ),
            )
            return

        player_name = msg.data.get("player_name", player.name)
        player.name = player_name
        room.players[player.player_id] = player
        player.room_id = room_id

        logger.info("Player %s joined room %s", player.name, room_id)
        await self.server._send(
            player,
            ServerMsg.room_joined(
                room_id,
                player.player_id,
                player.name,
                room.player_list_data(),
            ),
        )
        await self.server._broadcast_room_update(room)

    async def handle_room_leave(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        if not player.room_id:
            return

        await self.server._session_manager.leave_room(player)
        await self.server._send(player, ServerMsg(type=MsgType.ROOM_LEFT))

    async def handle_room_list(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        rooms_data = [
            {
                "room_id": room.room_id,
                "host_id": room.host_id,
                "player_count": room.player_count,
                "max_players": room.max_players,
                "state": room.state.value,
            }
            for room in self.server.rooms.values()
        ]
        await self.server._send(player, ServerMsg.room_listing(rooms_data))

    async def handle_room_ready(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        player.ready = msg.data.get("ready", True)
        room = self.server.rooms.get(player.room_id or "")
        if room:
            await self.server._broadcast_room_update(room)

    async def handle_room_start(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        room = self.server.rooms.get(player.room_id or "")
        if not room:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.not_in_room"),
                    code=400,
                    error_code="E_ROOM_NOT_IN_ROOM",
                ),
            )
            return

        if room.host_id != player.player_id:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.not_owner"),
                    code=403,
                    error_code="E_ROOM_NOT_OWNER",
                ),
            )
            return

        if room.state != RoomState.WAITING:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.game_in_progress"),
                    code=409,
                    error_code="E_ROOM_GAME_IN_PROGRESS",
                ),
            )
            return

        room.state = RoomState.PLAYING
        await self.server._broadcast_room(room, ServerMsg(type=MsgType.ROOM_STARTED))
        logger.info("Room %s started (%s players)", room.room_id, room.player_count)
        asyncio.create_task(self.server._run_game(room))

    async def handle_game_action(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        room = self.server.rooms.get(player.room_id or "")
        if not room or room.state != RoomState.PLAYING:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.not_in_game"),
                    code=400,
                    error_code="E_GAME_NOT_IN_PROGRESS",
                ),
            )
            return

        pending = room._pending_action
        if pending is None:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("error.not_your_turn"),
                    code=403,
                    error_code="E_GAME_NOT_YOUR_TURN",
                ),
            )
            return

        expected_pid, action_queue = pending
        if expected_pid != player.player_id:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("error.not_your_turn"),
                    code=403,
                    error_code="E_GAME_NOT_YOUR_TURN",
                ),
            )
            return

        await action_queue.put(msg.data)

    async def handle_game_response(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        room = self.server.rooms.get(player.room_id or "")
        if not room or room.state != RoomState.PLAYING:
            return

        try:
            request_id, response = decode_game_response(player.player_id, msg.data)
        except ValueError:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.invalid_format"),
                    code=400,
                    error_code="E_PROTO_INVALID_FORMAT",
                ),
            )
            return

        pending = self.server._find_pending_request(
            room,
            player.player_id,
            request_id,
            response.request_type,
        )
        if pending is None:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("exc.invalid_action"),
                    code=400,
                    error_code="E_GAME_INVALID_RESPONSE",
                ),
            )
            return

        if not pending.future.done():
            pending.future.set_result(response)

        await self.server._broadcast_game_event(
            room,
            "player_response",
            {
                "request_id": pending.request_id,
                "request_type": response.request_type.name.lower(),
                "player_id": player.player_id,
                "response": msg.data,
            },
        )

    async def handle_hero_chosen(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        room = self.server.rooms.get(player.room_id or "")
        if not room:
            return

        hero_id = msg.data.get("hero_id", "")
        await self.server._broadcast_game_event(
            room,
            "hero_chosen",
            {
                "player_id": player.player_id,
                "hero_id": hero_id,
            },
        )

    async def handle_chat(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        room = self.server.rooms.get(player.room_id or "")
        if not room:
            return

        text = sanitize_chat_message(msg.data.get("message", ""))
        if text:
            await self.server._broadcast_room(
                room,
                ServerMsg.chat_broadcast(player.name, text),
                exclude=player.player_id,
            )
