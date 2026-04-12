"""Session lifecycle helpers for the game server."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from i18n import t as _t

from .protocol import ServerMsg

if TYPE_CHECKING:
    from .server import GameServer
    from .server_types import ConnectedPlayer

logger = logging.getLogger(__name__)


class ServerSessionManager:
    """Own room membership cleanup and reconnect replay logic."""

    def __init__(self, server: GameServer) -> None:
        self.server = server

    async def leave_room(self, player: ConnectedPlayer) -> None:
        """Remove a player from the current room and cleanup empty rooms."""
        room_id = player.room_id
        room = self.server.rooms.get(room_id or "")

        if room is not None:
            room.players.pop(player.player_id, None)
            await self.server._broadcast_room_update(room)
            if not room.players:
                self.server.rooms.pop(room.room_id, None)
                logger.info("Room %s removed after last player left", room.room_id)

        player.room_id = None
        player.ready = False

    async def unregister_player(self, player: ConnectedPlayer) -> None:
        """Cleanup player state after a transport disconnect."""
        self.server._rate_limiter.remove_player(player.player_id)
        self.server._token_manager.revoke(player_id=player.player_id)

        if player.room_id:
            await self.leave_room(player)

    async def reconnect_player(
        self,
        player: ConnectedPlayer,
        room_id: str,
        last_seq: int,
        token: str = "",
    ) -> bool:
        """Re-attach a disconnected player and replay missed events."""
        if token and not self.server._token_manager.verify(token, player.player_id):
            logger.warning(
                "Reconnect token verification failed player_id=%s room_id=%s",
                player.player_id,
                room_id,
            )
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.invalid_token"),
                    code=401,
                    error_code="E_AUTH_INVALID_TOKEN",
                ),
            )
            return False

        room = self.server.rooms.get(room_id)
        if room is None:
            await self.server._send(
                player,
                ServerMsg.error(
                    _t("server.room_not_found"),
                    code=404,
                    error_code="E_ROOM_NOT_FOUND",
                ),
            )
            return False

        room.players[player.player_id] = player
        player.room_id = room_id

        missed_events = [event for event in room.event_log if event.seq > last_seq]
        for event in missed_events:
            await self.server._send(player, event)

        logger.info(
            "Player %s reconnected to room %s with %s replayed events",
            player.player_id,
            room_id,
            len(missed_events),
        )
        return True
