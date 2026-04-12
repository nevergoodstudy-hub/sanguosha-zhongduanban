"""WebSocket game client entrypoints and high-level protocol facade."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from inspect import isawaitable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

from .client_session import ClientSession
from .protocol import ClientMsg, MsgType, ServerMsg
from .settings import ClientSettings

logger = logging.getLogger(__name__)


class GameClient:
    """High-level client facade over the transport/session lifecycle."""

    def __init__(
        self,
        server_url: str = "ws://localhost:8765",
        settings: ClientSettings | None = None,
    ) -> None:
        if settings is not None:
            server_url = settings.server_url

        self.server_url = server_url
        self.player_id: int = 0
        self.player_name: str = ""
        self.room_id: str | None = None
        self.last_seq: int = 0
        self.auth_token: str = ""

        self._handlers: dict[MsgType, Callable[[ServerMsg], Any]] = {}
        self._on_connect: Callable[[], Any] | None = None
        self._on_disconnect: Callable[[], Any] | None = None

        auto_reconnect = True
        reconnect_delay = 2.0
        max_reconnect_attempts = 5
        heartbeat_interval = 15.0

        if settings is not None:
            auto_reconnect = settings.auto_reconnect
            reconnect_delay = settings.reconnect_delay
            max_reconnect_attempts = settings.max_reconnect_attempts
            heartbeat_interval = settings.heartbeat_interval

        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        self._heartbeat_interval = heartbeat_interval

        self._session = ClientSession(
            server_url=self.server_url,
            auto_reconnect=self.auto_reconnect,
            reconnect_delay=self.reconnect_delay,
            max_reconnect_attempts=self.max_reconnect_attempts,
            heartbeat_interval=self._heartbeat_interval,
            on_connect=self._handle_connect,
            on_disconnect=self._handle_disconnect,
            on_message=self._dispatch,
            on_reconnect=self._handle_reconnect,
            send_heartbeat=self._send_heartbeat,
        )

    def on(self, msg_type: MsgType, handler: Callable[[ServerMsg], Any]) -> None:
        """Register a message handler."""
        self._handlers[msg_type] = handler

    def on_connect(self, handler: Callable[[], Any]) -> None:
        """Register a callback for successful transport connects."""
        self._on_connect = handler

    def on_disconnect(self, handler: Callable[[], Any]) -> None:
        """Register a callback for transport disconnects."""
        self._on_disconnect = handler

    async def _invoke_callback(self, callback: Callable[..., Any], *args: Any) -> None:
        """Run sync or async callbacks safely."""
        try:
            result = callback(*args)
            if isawaitable(result):
                await result
        except Exception as exc:
            logger.warning("Callback execution failed: %s", exc)

    @property
    def _ws(self) -> ClientConnection | Any | None:
        return self._session._ws

    @_ws.setter
    def _ws(self, value: ClientConnection | Any | None) -> None:
        self._session._ws = value

    @property
    def _connected(self) -> bool:
        return self._session._connected

    @_connected.setter
    def _connected(self, value: bool) -> None:
        self._session._connected = value

    @property
    def _running(self) -> bool:
        return self._session._running

    @_running.setter
    def _running(self, value: bool) -> None:
        self._session._running = value

    async def _handle_connect(self) -> None:
        if self._on_connect is not None:
            await self._invoke_callback(self._on_connect)

    async def _handle_disconnect(self) -> None:
        if self._on_disconnect is not None:
            await self._invoke_callback(self._on_disconnect)

    async def _handle_reconnect(self) -> None:
        if self.room_id:
            await self.send(
                ClientMsg(
                    type=MsgType.ROOM_JOIN,
                    player_id=self.player_id,
                    data={
                        "room_id": self.room_id,
                        "reconnect": True,
                        "last_seq": self.last_seq,
                        "token": self.auth_token,
                    },
                )
            )

    async def _send_heartbeat(self) -> None:
        await self.send(ClientMsg.heartbeat(self.player_id))

    async def connect(self) -> bool:
        """Connect to the server."""
        return await self._session.connect()

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        await self._session.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._session.is_connected

    async def send(self, msg: ClientMsg) -> bool:
        """Send a client protocol message."""
        return await self._session.send_text(msg.to_json())

    async def _receive_loop(self) -> None:
        """Compatibility wrapper for direct receive-loop tests/debugging."""
        await self._session._receive_loop()

    async def _dispatch(self, raw: str) -> None:
        """Decode and dispatch a server message."""
        try:
            msg = ServerMsg.from_json(raw)

            if msg.seq > 0:
                self.last_seq = msg.seq

            if msg.type == MsgType.HEARTBEAT_ACK and "token" in msg.data:
                self.auth_token = msg.data["token"]
                player_id = msg.data.get("player_id", 0)
                if player_id:
                    self.player_id = player_id

            handler = self._handlers.get(msg.type)
            if handler is not None:
                await self._invoke_callback(handler, msg)
            else:
                logger.debug("Unhandled message type: %s", msg.type.value)
        except Exception as exc:
            logger.warning("Message dispatch failed: %s", exc)

    async def _heartbeat_loop(self) -> None:
        """Compatibility wrapper for direct heartbeat-loop tests/debugging."""
        await self._session._heartbeat_loop()

    async def _reconnect(self) -> bool:
        """Compatibility wrapper for reconnect tests/debugging."""
        return await self._session._reconnect()

    async def run(self) -> None:
        """Run the transport/session lifecycle."""
        await self._session.run()

    async def create_room(
        self,
        player_name: str,
        max_players: int = 4,
        ai_fill: bool = True,
    ) -> None:
        """Create a room."""
        self.player_name = player_name
        await self.send(ClientMsg.room_create(self.player_id, player_name, max_players, ai_fill))

    async def join_room(self, player_name: str, room_id: str) -> None:
        """Join a room."""
        self.player_name = player_name
        await self.send(ClientMsg.room_join(self.player_id, player_name, room_id))

    async def leave_room(self) -> None:
        """Leave the current room."""
        await self.send(ClientMsg.room_leave(self.player_id))
        self.room_id = None

    async def set_ready(self, ready: bool = True) -> None:
        """Set the ready state."""
        await self.send(ClientMsg.room_ready(self.player_id, ready))

    async def start_game(self) -> None:
        """Start the game as host."""
        await self.send(ClientMsg.room_start(self.player_id))

    async def list_rooms(self) -> None:
        """Request the current room list."""
        await self.send(ClientMsg.room_list())

    async def play_card(self, card_id: str, target_ids: list[int] | None = None) -> None:
        """Play a card."""
        await self.send(
            ClientMsg.game_action(
                self.player_id,
                "play_card",
                {"card_id": card_id, "target_ids": target_ids or []},
            )
        )

    async def use_skill(self, skill_id: str, target_ids: list[int] | None = None) -> None:
        """Use a skill."""
        await self.send(
            ClientMsg.game_action(
                self.player_id,
                "use_skill",
                {"skill_id": skill_id, "target_ids": target_ids or []},
            )
        )

    async def end_turn(self) -> None:
        """End the current turn."""
        await self.send(ClientMsg.game_action(self.player_id, "end_turn"))

    async def discard(self, card_ids: list[str]) -> None:
        """Discard cards."""
        await self.send(ClientMsg.game_action(self.player_id, "discard", {"card_ids": card_ids}))

    async def respond(
        self,
        request_type: str,
        accepted: bool,
        card_id: str | None = None,
        *,
        request_id: str = "",
        card_ids: list[str] | None = None,
        target_ids: list[int] | None = None,
        option: str | int | bool | list[str] | list[int] | None = None,
    ) -> None:
        """Respond to a runtime request."""
        data: dict[str, Any] = {}
        if card_id is not None:
            data["card_id"] = card_id
        if card_ids is not None:
            data["card_ids"] = card_ids
        if target_ids is not None:
            data["target_ids"] = target_ids
        if option is not None:
            data["option"] = option
        await self.send(
            ClientMsg.game_response(
                self.player_id,
                request_type,
                accepted,
                data,
                request_id=request_id,
            )
        )

    async def choose_hero(self, hero_id: str) -> None:
        """Choose a hero."""
        await self.send(ClientMsg.hero_chosen(self.player_id, hero_id))

    async def chat(self, message: str) -> None:
        """Send a chat message."""
        await self.send(ClientMsg.chat(self.player_id, message))


async def cli_client_main(
    server_url: str,
    player_name: str,
    *,
    settings: ClientSettings | None = None,
) -> None:
    """Run the simplified CLI client entrypoint."""
    client = GameClient(server_url=server_url, settings=settings)
    client.player_name = player_name

    cli_log = logging.getLogger("sanguosha.cli")

    def on_room_created(msg: ServerMsg) -> None:
        client.room_id = msg.data.get("room_id", "")
        cli_log.info("Room created: %s", client.room_id)

    def on_room_joined(msg: ServerMsg) -> None:
        client.room_id = msg.data.get("room_id", "")
        client.player_id = msg.data.get("player_id", 0)
        cli_log.info("Joined room %s as player %s", client.room_id, client.player_id)

    def on_room_update(msg: ServerMsg) -> None:
        players = msg.data.get("players", [])
        state = msg.data.get("state", "")
        cli_log.info("Room state %s, players=%s", state, [player["name"] for player in players])

    def on_game_event(msg: ServerMsg) -> None:
        event_type = msg.data.get("event_type", "")
        cli_log.info("[event] %s: %s", event_type, msg.data)

    def on_game_over(msg: ServerMsg) -> None:
        cli_log.info("Game over, winner=%s", msg.data.get("winner"))

    def on_chat(msg: ServerMsg) -> None:
        cli_log.info("[chat] %s: %s", msg.data.get("player_name"), msg.data.get("message"))

    def on_error(msg: ServerMsg) -> None:
        cli_log.error("[error] %s", msg.data.get("message"))

    client.on(MsgType.ROOM_CREATED, on_room_created)
    client.on(MsgType.ROOM_JOINED, on_room_joined)
    client.on(MsgType.ROOM_UPDATE, on_room_update)
    client.on(MsgType.GAME_EVENT, on_game_event)
    client.on(MsgType.GAME_OVER, on_game_over)
    client.on(MsgType.CHAT_BROADCAST, on_chat)
    client.on(MsgType.ERROR, on_error)

    await client.run()


def main() -> None:
    """CLI client entrypoint."""
    import argparse

    parser = argparse.ArgumentParser(description="Sanguosha client")
    parser.add_argument("--server", default="ws://localhost:8765", help="Server URL")
    parser.add_argument("--name", default="玩家", help="Player name")

    args = parser.parse_args()
    asyncio.run(cli_client_main(args.server, args.name))


if __name__ == "__main__":
    main()
