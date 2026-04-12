"""WebSocket 娓告垙鏈嶅姟绔?(M4-T02)
鍩轰簬 asyncio 鐨勪笁鍥芥潃缃戠粶瀵规垬鏈嶅姟绔?

鍔熻兘:
- 鎴块棿绠＄悊 (鍒涘缓/鍔犲叆/寮€濮?
- 娓告垙鐘舵€佸悓姝?(澧為噺浜嬩欢骞挎挱)
- 鏂嚎閲嶈繛 (鍩轰簬浜嬩欢搴忓彿閲嶆斁)
- 蹇冭烦妫€娴?
"""

from __future__ import annotations

import asyncio
import logging
import ssl
import time
import uuid
from collections.abc import Awaitable, Callable
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import suppress
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from websockets.asyncio.server import ServerConnection

    from game.actions import GameRequest, GameResponse, RequestType
    from game.engine import GameEngine
    from game.player import Player

from game.events import EventType
from i18n import t as _t

from .action_codec import decode_client_action
from .protocol import ClientMsg, MsgType, RoomState, ServerMsg
from .request_codec import encode_game_request
from .security import (
    DEFAULT_HEARTBEAT_TIMEOUT,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_MAX_CONNECTIONS_PER_IP,
    DEFAULT_MAX_MESSAGE_SIZE,
    ConnectionTokenManager,
    IPConnectionTracker,
    OriginValidator,
    RateLimiter,
)
from .server_dispatcher import ServerMessageDispatcher
from .server_session import ServerSessionManager
from .server_types import ConnectedPlayer, PendingGameRequest, Room
from .settings import ServerSettings

logger = logging.getLogger(__name__)


# ==================== 鏈嶅姟绔牳蹇?====================

# 閫熺巼闄愬埗榛樿鍊?
RATE_LIMIT_WINDOW: float = 1.0  # 婊戝姩绐楀彛 (绉?
RATE_LIMIT_MAX_MSGS: int = 30  # 绐楀彛鍐呮渶澶ф秷鎭暟


class GameServer:
    """涓夊浗鏉€ WebSocket 娓告垙鏈嶅姟绔?

    鑱岃矗:
    1. 绠＄悊 WebSocket 杩炴帴
    2. 鎴块棿鐢熷懡鍛ㄦ湡绠＄悊
    3. 灏嗗紩鎿庝簨浠跺箍鎾粰瀹㈡埛绔?
    4. 璺敱瀹㈡埛绔秷鎭埌瀵瑰簲澶勭悊鍣?
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        rate_limit_window: float = RATE_LIMIT_WINDOW,
        rate_limit_max_msgs: int = RATE_LIMIT_MAX_MSGS,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        max_connections_per_ip: int = DEFAULT_MAX_CONNECTIONS_PER_IP,
        max_message_size: int = DEFAULT_MAX_MESSAGE_SIZE,
        heartbeat_timeout: float = DEFAULT_HEARTBEAT_TIMEOUT,
        allowed_origins: str = "",
        allow_localhost_dev: bool = False,
        ssl_cert: str = "",
        ssl_key: str = "",
        settings: ServerSettings | None = None,
    ):
        if settings is not None:
            host = settings.host
            port = settings.port
            rate_limit_window = settings.rate_limit_window
            rate_limit_max_msgs = settings.rate_limit_max_msgs
            max_connections = settings.max_connections
            max_connections_per_ip = settings.max_connections_per_ip
            max_message_size = settings.max_message_size
            heartbeat_timeout = settings.heartbeat_timeout
            allowed_origins = settings.allowed_origins
            allow_localhost_dev = settings.allow_localhost_dev
            ssl_cert = settings.ssl_cert
            ssl_key = settings.ssl_key

        self.host = host
        self.port = port
        # 瀹夊叏鍙傛暟
        self._max_connections = max_connections
        self._max_message_size = max_message_size
        self._heartbeat_timeout = heartbeat_timeout
        # TLS
        self._ssl_cert = ssl_cert
        self._ssl_key = ssl_key
        # 杩炴帴绠＄悊
        self.connections: dict[int, ConnectedPlayer] = {}  # player_id 鈫?player
        self.ws_to_player: dict[ServerConnection, int] = {}  # websocket 鈫?player_id
        self._next_player_id: int = 1
        # 瀹夊叏缁勪欢
        self._token_manager = ConnectionTokenManager()
        self._ip_tracker = IPConnectionTracker(max_per_ip=max_connections_per_ip)
        self._origin_validator = OriginValidator(
            allowed_origins,
            allow_localhost_dev=allow_localhost_dev,
        )
        if not self._origin_validator.allowed_origins:
            logger.warning(
                "No allowed_origins configured. All WebSocket connections "
                "will be rejected (fail-closed). Set SANGUOSHA_WS_ALLOWED_ORIGINS "
                "e.g. 'http://localhost:3000,https://game.example.com'."
            )
        else:
            logger.info(
                "Origin allowlist enabled: %s",
                ", ".join(self._origin_validator.allowed_origins),
            )
            if allow_localhost_dev:
                logger.warning(
                    "Development localhost origin bypass is enabled "
                    "(SANGUOSHA_DEV_ALLOW_LOCALHOST=1)."
                )
        self._rate_limiter = RateLimiter(rate_limit_window, rate_limit_max_msgs)
        # 鎴块棿绠＄悊
        self.rooms: dict[str, Room] = {}  # room_id 鈫?room
        # 娑堟伅璺敱琛?
        self._dispatcher = ServerMessageDispatcher(self)
        self._session_manager = ServerSessionManager(self)
        self._handlers: dict[MsgType, Callable[[ConnectedPlayer, ClientMsg], Awaitable[None]]] = (
            self._dispatcher.handlers
        )
        # 鏈嶅姟绔姸鎬?
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None

    # ==================== 杩炴帴绠＄悊 ====================

    def _assign_player_id(self) -> int:
        """鍒嗛厤鍞竴鐜╁ ID."""
        pid = self._next_player_id
        self._next_player_id += 1
        return pid

    def _get_remote_ip(self, websocket: ServerConnection) -> str:
        """鑾峰彇瀹㈡埛绔?IP 鍦板潃."""
        try:
            peername = websocket.transport.get_extra_info("peername")
            if peername:
                return str(peername[0])
        except Exception:
            pass
        return "unknown"

    async def _register(self, websocket: ServerConnection) -> ConnectedPlayer | None:
        """娉ㄥ唽鏂拌繛鎺?(鍚繛鎺ユ暟闄愬埗鍜屼护鐗岀鍙?."""
        remote_ip = self._get_remote_ip(websocket)

        # 鎬昏繛鎺ユ暟妫€鏌?
        if len(self.connections) >= self._max_connections:
            logger.warning(f"杩炴帴鏁板凡杈句笂闄?({self._max_connections}), 鎷掔粷 {remote_ip}")
            await websocket.close(1013, _t("server.full"))  # 1013 = Try Again Later
            return None

        # 鍗?IP 杩炴帴鏁版鏌?
        if not self._ip_tracker.can_connect(remote_ip):
            logger.warning(f"IP {remote_ip} 杩炴帴鏁拌秴闄? 鎷掔粷")
            await websocket.close(1008, _t("server.ip_limit"))  # 1008 = Policy Violation
            return None

        pid = self._assign_player_id()
        token = self._token_manager.issue(pid)
        player = ConnectedPlayer(
            player_id=pid,
            name=_t("game.player_name", index=pid),
            websocket=websocket,
            auth_token=token,
            remote_ip=remote_ip,
        )
        self.connections[pid] = player
        self.ws_to_player[websocket] = pid
        self._ip_tracker.add(remote_ip)

        # 鍙戦€佹杩庢秷鎭?(鍖呭惈浠ょ墝)
        welcome = ServerMsg(
            type=MsgType.HEARTBEAT_ACK,
            data={
                "player_id": pid,
                "token": token,
            },
        )
        await self._send(player, welcome)
        logger.info(f"鐜╁ {pid} 宸茶繛鎺?(IP: {remote_ip})")
        return player

    async def _unregister(self, websocket: ServerConnection) -> None:
        """娉ㄩ攢杩炴帴."""
        pid = self.ws_to_player.pop(websocket, None)
        if pid is None:
            return
        player = self.connections.pop(pid, None)
        if player:
            self._ip_tracker.remove(player.remote_ip)
            await self._session_manager.unregister_player(player)
        logger.info("Player %s disconnected", pid)

    # ==================== 娑堟伅鏀跺彂 ====================

    async def _send(self, player: ConnectedPlayer, msg: ServerMsg) -> None:
        """鍙戦€佹秷鎭粰鍗曚釜鐜╁."""
        try:
            await player.websocket.send(msg.to_json())
        except Exception as e:
            logger.warning(f"鍙戦€佹秷鎭け璐?(鐜╁{player.player_id}): {e}")

    async def _broadcast_room(self, room: Room, msg: ServerMsg, exclude: int | None = None) -> None:
        """骞挎挱娑堟伅缁欐埧闂村唴鎵€鏈夌帺瀹?"""
        for pid, player in room.players.items():
            if pid != exclude:
                await self._send(player, msg)

    async def _broadcast_room_update(self, room: Room) -> None:
        """骞挎挱鎴块棿鐘舵€佹洿鏂?"""
        msg = ServerMsg.room_update(room.room_id, room.player_list_data(), room.state)
        await self._broadcast_room(room, msg)

    async def _broadcast_game_event(
        self, room: Room, event_type: str, event_data: dict[str, Any]
    ) -> None:
        """骞挎挱娓告垙浜嬩欢骞惰褰曞埌浜嬩欢鏃ュ織."""
        seq = room.next_seq()
        msg = ServerMsg.game_event(event_type, event_data, seq=seq)
        room.event_log.append(msg)
        await self._broadcast_room(room, msg)

    def _request_game_response_sync(
        self,
        loop: asyncio.AbstractEventLoop,
        room: Room,
        request: GameRequest,
    ) -> GameResponse:
        from game.actions import GameResponse

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._request_game_response(room, request), loop
            )
            return future.result(timeout=request.timeout + 1.0)
        except FutureTimeoutError:
            logger.info(
                "Timed out waiting for game response request_type=%s player_id=%s",
                request.request_type.name,
                request.player_id,
            )
        except Exception as exc:
            logger.warning("Game response bridge failed: %s", exc)

        return GameResponse(
            request_type=request.request_type,
            player_id=request.player_id,
            accepted=False,
        )

    async def _request_game_response(self, room: Room, request: GameRequest) -> GameResponse:
        from game.actions import GameResponse

        player = room.players.get(request.player_id)
        if player is None:
            return GameResponse(
                request_type=request.request_type,
                player_id=request.player_id,
                accepted=False,
            )

        request_id = uuid.uuid4().hex
        future: asyncio.Future[GameResponse] = asyncio.get_running_loop().create_future()
        room._pending_requests[request_id] = PendingGameRequest(
            request_id=request_id,
            player_id=request.player_id,
            request_type=request.request_type,
            future=future,
        )

        try:
            await self._send(player, encode_game_request(request_id, request))
            return await asyncio.wait_for(future, timeout=request.timeout)
        except asyncio.TimeoutError:
            logger.info(
                "Player %d response timeout for %s",
                request.player_id,
                request.request_type.name,
            )
            return GameResponse(
                request_type=request.request_type,
                player_id=request.player_id,
                accepted=False,
            )
        finally:
            room._pending_requests.pop(request_id, None)

    def _find_pending_request(
        self,
        room: Room,
        player_id: int,
        request_id: str | None,
        request_type: RequestType,
    ) -> PendingGameRequest | None:
        if request_id:
            pending = room._pending_requests.get(request_id)
            if pending and pending.player_id == player_id and pending.request_type == request_type:
                return pending
            return None

        candidates = [
            pending
            for pending in room._pending_requests.values()
            if pending.player_id == player_id and pending.request_type == request_type
        ]
        return candidates[0] if len(candidates) == 1 else None

    # ==================== 娑堟伅璺敱 ====================

    def _check_rate_limit(self, player: ConnectedPlayer) -> bool:
        """妫€鏌ョ帺瀹舵槸鍚﹁秴鍑烘秷鎭€熺巼闄愬埗銆?

        Returns:
            True 琛ㄧず鍏佽澶勭悊, False 琛ㄧず搴斾涪寮?
        """
        return bool(self._rate_limiter.check(player.player_id))

    async def _handle_message(self, websocket: ServerConnection, raw: str) -> None:
        """Delegate raw message validation and routing to the dispatcher."""
        await self._dispatcher.dispatch(websocket, raw)

    # ==================== 鎴块棿绠＄悊澶勭悊鍣?====================

    async def _handle_heartbeat(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_heartbeat(player, msg)

    async def _handle_room_create(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_room_create(player, msg)

    async def _handle_room_join(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_room_join(player, msg)

    async def _handle_room_leave(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_room_leave(player, msg)

    async def _handle_room_list(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_room_list(player, msg)

    async def _handle_room_ready(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_room_ready(player, msg)

    async def _handle_room_start(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_room_start(player, msg)

    # ==================== 娓告垙閫昏緫 ====================

    # 浜虹被鐜╁鎿嶄綔瓒呮椂锛堢锛?
    _ACTION_TIMEOUT: float = 60.0

    async def _run_game(self, room: Room) -> None:
        """鍦ㄦ埧闂翠腑鍚姩浜や簰寮忓紓姝ユ父鎴忓惊鐜?

        绗竴闃舵鍏堟墦閫氣€滄埧闂寸帺瀹?-> 寮曟搸鐜╁鈥濆拰鈥滅綉缁滃姩浣?-> 棰嗗煙鍔ㄤ綔鈥濄€?
        """
        try:
            import random

            from game.engine import GameEngine
            from game.enums import GameState
            from game.request_handler import NetworkRequestHandler

            seed = random.randint(0, 2**32 - 1)
            room.game_seed = seed

            engine = GameEngine()
            room.engine = engine
            loop = asyncio.get_running_loop()
            engine.request_handler = NetworkRequestHandler(
                engine,
                request_callback=lambda request: self._request_game_response_sync(
                    loop, room, request
                ),
                connected_player_ids=set(room.players),
            )

            # 鍒濆鍖栨父鎴?
            player_count = room.max_players if room.ai_fill else room.player_count
            engine.setup_room_game(
                [
                    (connected_player.player_id, connected_player.name)
                    for connected_player in room.players.values()
                ],
                total_player_count=player_count,
                seed=seed,
            )

            # 骞挎挱鍒濆娓告垙鐘舵€?
            state_data = {
                "player_count": player_count,
                "seed": seed,
                "players": [
                    {"id": p.id, "name": p.name, "identity": p.identity.value}
                    for p in engine.players
                ]
                if engine.players
                else [],
            }
            await self._broadcast_room(room, ServerMsg.game_state(state_data))

            # 浜や簰寮忔父鎴忓惊鐜?
            while engine.state == GameState.IN_PROGRESS:
                current = engine.current_player
                player_conn = room.players.get(current.id)

                if player_conn and not current.is_ai:
                    await self._run_human_turn(room, engine, player_conn, current)
                else:
                    # AI 鍥炲悎
                    await asyncio.to_thread(engine.run_headless_turn)

                await self._broadcast_game_state(room, engine)

                if engine.is_game_over():
                    break
                engine.next_turn()

            # 娓告垙缁撴潫
            winner = engine.winner_identity.value if engine.winner_identity else "unknown"
            await self._broadcast_room(
                room,
                ServerMsg.game_over(
                    winner=winner,
                    reason=_t("game.over_generic"),
                    stats={"rounds": engine.round_count, "seed": seed},
                ),
            )
            room.state = RoomState.FINISHED

        except Exception as e:
            logger.exception(f"娓告垙杩愯寮傚父: {e}")
            await self._broadcast_room(
                room,
                ServerMsg.error(
                    _t("server.game_error", error=str(e)),
                    code=500,
                    error_code="E_GAME_RUNTIME",
                ),
            )
            room.state = RoomState.FINISHED

    async def _broadcast_game_state(self, room: Room, engine: GameEngine) -> None:
        """骞挎挱褰撳墠娓告垙鐘舵€佺粰鎴块棿鍐呮墍鏈夌帺瀹?"""
        state_data = {
            "current_player": engine.current_player.id if engine.current_player else None,
            "round": engine.round_count,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "hp": p.hp,
                    "max_hp": p.max_hp,
                    "alive": p.is_alive,
                }
                for p in engine.players
            ]
            if engine.players
            else [],
        }
        await self._broadcast_room(room, ServerMsg.game_state(state_data))

    async def _run_human_turn(
        self,
        room: Room,
        engine: GameEngine,
        player_conn: ConnectedPlayer,
        player: Player,
    ) -> None:
        """鎵ц鐪熶汉鐜╁鐨勪富鍔ㄥ洖鍚堟祦绋?"""
        from game.enums import GamePhase

        player.reset_turn()
        engine.event_bus.emit(EventType.TURN_START, player=player)
        engine.log_event("turn_start", _t("turn.start", name=player.name))

        await asyncio.to_thread(engine.phase_prepare, player)
        await asyncio.to_thread(engine.phase_judge, player)
        await asyncio.to_thread(engine.phase_draw, player)
        engine.phase = GamePhase.PLAY
        engine.event_bus.emit(EventType.PHASE_PLAY_START, player=player)
        engine.log_event("phase", _t("turn.phase_play"))
        await self._broadcast_game_state(room, engine)
        await self._run_human_play_phase(room, engine, player_conn)
        engine.event_bus.emit(EventType.PHASE_PLAY_END, player=player)

        if player.need_discard > 0:
            engine.phase = GamePhase.DISCARD
            await self._run_human_discard_phase(room, engine, player)

        await asyncio.to_thread(engine.phase_end, player)
        engine.log_event("turn_end", _t("turn.end", name=player.name))
        engine.event_bus.emit(EventType.TURN_END, player=player)

    async def _run_human_discard_phase(
        self,
        room: Room,
        engine: GameEngine,
        player: Player,
    ) -> None:
        """鎵ц鐪熶汉鐜╁鐨勫純鐗岃姹?"""
        discard_count = player.need_discard
        if discard_count <= 0:
            return

        engine.log_event("phase", _t("turn.discard_phase", count=discard_count))
        selected_cards = await asyncio.to_thread(
            engine.request_handler.request_discard,
            player,
            discard_count,
            discard_count,
        )
        if len(selected_cards) < discard_count:
            selected_cards = list(player.hand[-discard_count:])
        if selected_cards:
            await asyncio.to_thread(engine.discard_cards, player, selected_cards)
            await self._broadcast_game_state(room, engine)

    async def _run_human_play_phase(
        self,
        room: Room,
        engine: GameEngine,
        player_conn: ConnectedPlayer,
    ) -> None:
        """绛夊緟骞舵墽琛岀湡浜虹帺瀹剁殑涓诲姩鍔ㄤ綔鐩村埌缁撴潫鍥炲悎鎴栬秴鏃?"""
        action_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        room._pending_action = (player_conn.player_id, action_queue)
        try:
            while not engine.is_game_over():
                try:
                    action_data = await asyncio.wait_for(
                        action_queue.get(),
                        timeout=self._ACTION_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    logger.info("Player %d action timeout, auto-ending turn", player_conn.player_id)
                    break

                should_end_turn = await self._apply_human_action(room, player_conn, action_data)
                await self._broadcast_game_state(room, engine)
                if should_end_turn:
                    break
        finally:
            room._pending_action = None

    async def _apply_human_action(
        self,
        room: Room,
        player: ConnectedPlayer,
        action_data: dict[str, Any],
    ) -> bool:
        """鎵ц涓€鏉＄湡浜轰富鍔ㄥ姩浣滐紝杩斿洖鏄惁搴旂粨鏉熷洖鍚?"""
        if action_data.get("action_type") == "end_turn":
            return True

        if room.engine is None:
            return True

        try:
            action = decode_client_action(player.player_id, action_data)
        except ValueError as exc:
            await self._send(
                player,
                ServerMsg.error(
                    _t("error.invalid_action", msg=str(exc)),
                    code=400,
                    error_code="E_GAME_INVALID_ACTION",
                ),
            )
            return False

        executed = await asyncio.to_thread(room.engine.execute_action, action)
        if not executed:
            await self._send(
                player,
                ServerMsg.error(
                    _t("exc.invalid_action"),
                    code=400,
                    error_code="E_GAME_INVALID_ACTION",
                ),
            )
            return False

        await self._broadcast_game_event(
            room,
            "player_action",
            {
                "player_id": player.player_id,
                "action": action_data,
            },
        )
        return False

    async def _handle_game_action(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_game_action(player, msg)

    async def _handle_game_response(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_game_response(player, msg)

    async def _handle_hero_chosen(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_hero_chosen(player, msg)

    async def _handle_chat(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        await self._dispatcher.handle_chat(player, msg)

    # ==================== 鏂嚎閲嶈繛 ====================

    async def reconnect_player(
        self, player: ConnectedPlayer, room_id: str, last_seq: int, token: str = ""
    ) -> bool:
        """Compatibility wrapper for session-manager reconnect handling."""
        return await self._session_manager.reconnect_player(
            player,
            room_id,
            last_seq,
            token=token,
        )

    # ==================== 蹇冭烦瓒呮椂妫€娴?====================

    async def _heartbeat_checker(self) -> None:
        """鍚庡彴浠诲姟: 瀹氭湡妫€鏌ュ績璺宠秴鏃剁殑杩炴帴骞舵竻鐞嗐€?"""
        while self._running:
            await asyncio.sleep(self._heartbeat_timeout / 2)
            now = time.time()
            stale: list[int] = []
            for pid, player in list(self.connections.items()):
                if now - player.last_heartbeat > self._heartbeat_timeout:
                    stale.append(pid)
            for pid in stale:
                stale_player = self.connections.get(pid)
                if stale_player:
                    logger.info(f"鐜╁ {pid} 蹇冭烦瓒呮椂锛屾柇寮€杩炴帴")
                    with suppress(Exception):
                        await stale_player.websocket.close(1001, _t("server.heartbeat_timeout"))
                    await self._unregister(stale_player.websocket)
            # 瀹氭湡娓呯悊杩囨湡浠ょ墝
            self._token_manager.cleanup_expired()

    # ==================== 鏈嶅姟绔敓鍛藉懆鏈?====================

    async def _connection_handler(self, websocket: ServerConnection) -> None:
        """澶勭悊鍗曚釜 WebSocket 杩炴帴."""
        # Origin 楠岃瘉
        if not self._check_origin(websocket):
            await websocket.close(1008, "Origin not allowed")
            return

        player = await self._register(websocket)
        if player is None:
            return  # 杩炴帴琚嫆缁?
        try:
            async for raw_message in websocket:
                payload = (
                    raw_message.decode("utf-8", errors="replace")
                    if isinstance(raw_message, bytes)
                    else raw_message
                )
                await self._handle_message(websocket, payload)
        except Exception as e:
            logger.warning(f"杩炴帴寮傚父 (鐜╁{player.player_id}): {e}")
        finally:
            await self._unregister(websocket)

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        """鏋勫缓 SSL 涓婁笅鏂?(濡傛灉閰嶇疆浜嗚瘉涔?銆?"""
        if not self._ssl_cert or not self._ssl_key:
            return None

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self._ssl_cert, self._ssl_key)
        logger.info("宸插姞杞?TLS 璇佷功")
        return ctx

    def _check_origin(self, websocket: ServerConnection) -> bool:
        """妫€鏌?WebSocket 鎻℃墜涓殑 Origin 澶淬€?"""
        remote_ip = self._get_remote_ip(websocket)
        if not self._origin_validator.is_enabled:
            logger.warning(
                "Reject websocket handshake: origin allowlist disabled (fail-closed) remote_ip=%s",
                remote_ip,
            )
            return False

        origin = None
        try:
            request = websocket.request
            if request is not None:
                origin = request.headers.get("Origin")
        except Exception:
            pass

        if not self._origin_validator.is_allowed(origin):
            logger.warning(
                "Reject websocket handshake: origin not allowed "
                "origin=%s remote_ip=%s allowlist=%s",
                origin,
                remote_ip,
                ", ".join(self._origin_validator.allowed_origins),
            )
            return False
        return True

    def _get_serve_origins(self) -> list[str] | None:
        """涓?websockets.serve 鎻愪緵 origins 鍙傛暟銆?"""
        if not self._origin_validator.is_enabled:
            return None
        return list(self._origin_validator.allowed_origins)

    async def start(self) -> None:
        """鍚姩鏈嶅姟绔?"""
        try:
            import websockets
        except ImportError:
            logger.error("闇€瑕佸畨瑁?websockets: pip install websockets")
            return

        self._running = True
        ssl_ctx = self._build_ssl_context()
        if not ssl_ctx:
            logger.warning(
                "Running without TLS (ws://). Auth tokens will be transmitted "
                "in plaintext. Use --ssl-cert and --ssl-key for production."
            )
        protocol = "wss" if ssl_ctx else "ws"
        logger.info(f"涓夊浗鏉€鏈嶅姟绔惎鍔? {protocol}://{self.host}:{self.port}")

        # 鍚姩蹇冭烦瓒呮椂妫€娴嬪悗鍙颁换鍔?
        self._heartbeat_task = asyncio.create_task(self._heartbeat_checker())
        serve_origins = self._get_serve_origins()

        async with websockets.serve(
            self._connection_handler,
            self.host,
            self.port,
            max_size=self._max_message_size,
            origins=cast(Any, serve_origins),
            ssl=ssl_ctx,
        ):
            while self._running:
                await asyncio.sleep(1)

    def stop(self) -> None:
        """鍋滄鏈嶅姟绔?"""
        self._running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        logger.info("Game server stopped")


# ==================== CLI 鍏ュ彛 ====================


def main() -> None:
    """鍛戒护琛屽惎鍔ㄦ湇鍔＄."""
    import argparse

    parser = argparse.ArgumentParser(description="Sanguosha WebSocket game server")
    parser.add_argument("--host", default="127.0.0.1", help="鐩戝惉鍦板潃")
    parser.add_argument("--port", type=int, default=8765, help="鐩戝惉绔彛")
    parser.add_argument("-v", "--verbose", action="store_true", help="璇︾粏鏃ュ織")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    server = GameServer(host=args.host, port=args.port)
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
