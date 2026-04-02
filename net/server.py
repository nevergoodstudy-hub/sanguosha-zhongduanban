"""WebSocket 游戏服务端 (M4-T02)
基于 asyncio 的三国杀网络对战服务端.

功能:
- 房间管理 (创建/加入/开始)
- 游戏状态同步 (增量事件广播)
- 断线重连 (基于事件序号重放)
- 心跳检测
"""

from __future__ import annotations

import asyncio
import json
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
from .models import validate_client_message
from .protocol import ClientMsg, MsgType, RoomState, ServerMsg, parse_message
from .request_codec import decode_game_response, encode_game_request
from .security import (
    DEFAULT_HEARTBEAT_TIMEOUT,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_MAX_CONNECTIONS_PER_IP,
    DEFAULT_MAX_MESSAGE_SIZE,
    ConnectionTokenManager,
    IPConnectionTracker,
    OriginValidator,
    RateLimiter,
    sanitize_chat_message,
)
from .server_types import ConnectedPlayer, PendingGameRequest, Room

logger = logging.getLogger(__name__)


# ==================== 服务端核心 ====================

# 速率限制默认值
RATE_LIMIT_WINDOW: float = 1.0  # 滑动窗口 (秒)
RATE_LIMIT_MAX_MSGS: int = 30  # 窗口内最大消息数


class GameServer:
    """三国杀 WebSocket 游戏服务端.

    职责:
    1. 管理 WebSocket 连接
    2. 房间生命周期管理
    3. 将引擎事件广播给客户端
    4. 路由客户端消息到对应处理器
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
    ):
        self.host = host
        self.port = port
        # 安全参数
        self._max_connections = max_connections
        self._max_message_size = max_message_size
        self._heartbeat_timeout = heartbeat_timeout
        # TLS
        self._ssl_cert = ssl_cert
        self._ssl_key = ssl_key
        # 连接管理
        self.connections: dict[int, ConnectedPlayer] = {}  # player_id → player
        self.ws_to_player: dict[ServerConnection, int] = {}  # websocket → player_id
        self._next_player_id: int = 1
        # 安全组件
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
        # 房间管理
        self.rooms: dict[str, Room] = {}  # room_id → room
        # 消息路由表
        self._handlers: dict[MsgType, Callable[[ConnectedPlayer, ClientMsg], Awaitable[None]]] = {
            MsgType.HEARTBEAT: self._handle_heartbeat,
            MsgType.ROOM_CREATE: self._handle_room_create,
            MsgType.ROOM_JOIN: self._handle_room_join,
            MsgType.ROOM_LEAVE: self._handle_room_leave,
            MsgType.ROOM_LIST: self._handle_room_list,
            MsgType.ROOM_READY: self._handle_room_ready,
            MsgType.ROOM_START: self._handle_room_start,
            MsgType.GAME_ACTION: self._handle_game_action,
            MsgType.GAME_RESPONSE: self._handle_game_response,
            MsgType.HERO_CHOSEN: self._handle_hero_chosen,
            MsgType.CHAT: self._handle_chat,
        }
        # 服务端状态
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None

    # ==================== 连接管理 ====================

    def _assign_player_id(self) -> int:
        """分配唯一玩家 ID."""
        pid = self._next_player_id
        self._next_player_id += 1
        return pid

    def _get_remote_ip(self, websocket: ServerConnection) -> str:
        """获取客户端 IP 地址."""
        try:
            peername = websocket.transport.get_extra_info("peername")
            if peername:
                return str(peername[0])
        except Exception:
            pass
        return "unknown"

    async def _register(self, websocket: ServerConnection) -> ConnectedPlayer | None:
        """注册新连接 (含连接数限制和令牌签发)."""
        remote_ip = self._get_remote_ip(websocket)

        # 总连接数检查
        if len(self.connections) >= self._max_connections:
            logger.warning(f"连接数已达上限 ({self._max_connections}), 拒绝 {remote_ip}")
            await websocket.close(1013, _t("server.full"))  # 1013 = Try Again Later
            return None

        # 单 IP 连接数检查
        if not self._ip_tracker.can_connect(remote_ip):
            logger.warning(f"IP {remote_ip} 连接数超限, 拒绝")
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

        # 发送欢迎消息 (包含令牌)
        welcome = ServerMsg(
            type=MsgType.HEARTBEAT_ACK,
            data={
                "player_id": pid,
                "token": token,
            },
        )
        await self._send(player, welcome)
        logger.info(f"玩家 {pid} 已连接 (IP: {remote_ip})")
        return player

    async def _unregister(self, websocket: ServerConnection) -> None:
        """注销连接."""
        pid = self.ws_to_player.pop(websocket, None)
        if pid is None:
            return
        player = self.connections.pop(pid, None)
        if player:
            self._ip_tracker.remove(player.remote_ip)
            self._token_manager.revoke(player_id=pid)
            self._rate_limiter.remove_player(pid)
            if player.room_id:
                room = self.rooms.get(player.room_id)
                if room:
                    room.players.pop(pid, None)
                    # 通知房间内其他玩家
                    await self._broadcast_room_update(room)
                    # 如果房间空了，清理
                    if not room.players:
                        self.rooms.pop(room.room_id, None)
                        logger.info(f"房间 {room.room_id} 已空，已删除")
        logger.info(f"玩家 {pid} 已断开")

    # ==================== 消息收发 ====================

    async def _send(self, player: ConnectedPlayer, msg: ServerMsg) -> None:
        """发送消息给单个玩家."""
        try:
            await player.websocket.send(msg.to_json())
        except Exception as e:
            logger.warning(f"发送消息失败 (玩家{player.player_id}): {e}")

    async def _broadcast_room(self, room: Room, msg: ServerMsg, exclude: int | None = None) -> None:
        """广播消息给房间内所有玩家."""
        for pid, player in room.players.items():
            if pid != exclude:
                await self._send(player, msg)

    async def _broadcast_room_update(self, room: Room) -> None:
        """广播房间状态更新."""
        msg = ServerMsg.room_update(room.room_id, room.player_list_data(), room.state)
        await self._broadcast_room(room, msg)

    async def _broadcast_game_event(
        self, room: Room, event_type: str, event_data: dict[str, Any]
    ) -> None:
        """广播游戏事件并记录到事件日志."""
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
            future = asyncio.run_coroutine_threadsafe(self._request_game_response(room, request), loop)
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

    # ==================== 消息路由 ====================

    def _check_rate_limit(self, player: ConnectedPlayer) -> bool:
        """检查玩家是否超出消息速率限制。.

        Returns:
            True 表示允许处理, False 表示应丢弃
        """
        return bool(self._rate_limiter.check(player.player_id))

    async def _handle_message(self, websocket: ServerConnection, raw: str) -> None:
        """路由消息到对应处理器（含 Pydantic 校验）."""
        try:
            # Phase 3.3: Pydantic 校验 — 拒绝结构不合法的消息
            try:
                validate_client_message(raw)
            except Exception as ve:
                logger.warning(f"消息校验失败: {ve}")
                pid = self.ws_to_player.get(websocket)
                player = self.connections.get(pid) if pid else None
                if player:
                    await self._send(
                        player,
                        ServerMsg.error(
                            _t("server.invalid_format"),
                            code=400,
                            error_code="E_PROTO_INVALID_FORMAT",
                        ),
                    )
                return

            type_str, obj = parse_message(raw)
            msg_type = MsgType(type_str)
            client_msg = ClientMsg.from_json(raw)

            # 获取玩家
            pid = self.ws_to_player.get(websocket)
            player = self.connections.get(pid) if pid else None
            if not player:
                return

            # 速率限制 (心跳不受限)
            if msg_type != MsgType.HEARTBEAT and not self._check_rate_limit(player):
                logger.warning(f"速率限制: 玩家 {player.player_id} 消息过快，已丢弃")
                await self._send(
                    player,
                    ServerMsg.error(
                        _t("server.rate_limited"),
                        code=429,
                        error_code="E_RATE_LIMITED",
                    ),
                )
                return

            # 覆盖 player_id 为服务端分配的 (防伪造)
            client_msg.player_id = player.player_id

            handler = self._handlers.get(msg_type)
            if handler:
                await handler(player, client_msg)
            else:
                await self._send(
                    player,
                    ServerMsg.error(
                        _t("server.unknown_type", type=type_str),
                        code=400,
                        error_code="E_PROTO_UNKNOWN_TYPE",
                    ),
                )

        except json.JSONDecodeError:
            logger.warning("收到无效 JSON")
        except ValueError as e:
            logger.warning(f"消息解析错误: {e}")
        except Exception as e:
            logger.exception(f"处理消息异常: {e}")

    # ==================== 房间管理处理器 ====================

    async def _handle_heartbeat(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        player.last_heartbeat = time.time()
        await self._send(player, ServerMsg.heartbeat_ack())

    async def _handle_room_create(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        if player.room_id:
            await self._send(
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
        self.rooms[room_id] = room

        logger.info(f"房间 {room_id} 已创建 (房主: {player.name})")
        await self._send(
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

    async def _handle_room_join(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        if player.room_id:
            await self._send(
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
        room = self.rooms.get(room_id)
        if not room:
            await self._send(
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
                await self._send(
                    player,
                    ServerMsg.error(
                        _t("server.invalid_token"),
                        code=401,
                        error_code="E_AUTH_INVALID_TOKEN",
                    ),
                )
                return
            if not await self.reconnect_player(
                player,
                room_id,
                max(reconnect_last_seq, 0),
                token=reconnect_token,
            ):
                return
            await self._send(
                player,
                ServerMsg.room_joined(
                    room_id, player.player_id, player.name, room.player_list_data()
                ),
            )
            await self._broadcast_room_update(room)
            return
        if room.is_full:
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.room_full"),
                    code=409,
                    error_code="E_ROOM_FULL",
                ),
            )
            return
        if room.state != RoomState.WAITING:
            await self._send(
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

        logger.info(f"玩家 {player.name} 加入房间 {room_id}")
        await self._send(
            player,
            ServerMsg.room_joined(room_id, player.player_id, player.name, room.player_list_data()),
        )
        await self._broadcast_room_update(room)

    async def _handle_room_leave(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        if not player.room_id:
            return
        room = self.rooms.get(player.room_id)
        if room:
            room.players.pop(player.player_id, None)
            await self._broadcast_room_update(room)
            if not room.players:
                self.rooms.pop(room.room_id, None)
        player.room_id = None
        player.ready = False
        await self._send(player, ServerMsg(type=MsgType.ROOM_LEFT))

    async def _handle_room_list(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        rooms_data = [
            {
                "room_id": r.room_id,
                "host_id": r.host_id,
                "player_count": r.player_count,
                "max_players": r.max_players,
                "state": r.state.value,
            }
            for r in self.rooms.values()
        ]
        await self._send(player, ServerMsg.room_listing(rooms_data))

    async def _handle_room_ready(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        player.ready = msg.data.get("ready", True)
        room = self.rooms.get(player.room_id or "")
        if room:
            await self._broadcast_room_update(room)

    async def _handle_room_start(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        """房主开始游戏."""
        room = self.rooms.get(player.room_id or "")
        if not room:
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.not_in_room"),
                    code=400,
                    error_code="E_ROOM_NOT_IN_ROOM",
                ),
            )
            return
        if room.host_id != player.player_id:
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.not_owner"),
                    code=403,
                    error_code="E_ROOM_NOT_OWNER",
                ),
            )
            return
        if room.state != RoomState.WAITING:
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.game_in_progress"),
                    code=409,
                    error_code="E_ROOM_GAME_IN_PROGRESS",
                ),
            )
            return

        room.state = RoomState.PLAYING
        await self._broadcast_room(room, ServerMsg(type=MsgType.ROOM_STARTED))
        logger.info(f"房间 {room.room_id} 游戏开始 ({room.player_count} 人)")

        # 启动游戏引擎 (异步)
        asyncio.create_task(self._run_game(room))

    # ==================== 游戏逻辑 ====================

    # 人类玩家操作超时（秒）
    _ACTION_TIMEOUT: float = 60.0

    async def _run_game(self, room: Room) -> None:
        """在房间中启动交互式异步游戏循环.

        第一阶段先打通“房间玩家 -> 引擎玩家”和“网络动作 -> 领域动作”。
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
                request_callback=lambda request: self._request_game_response_sync(loop, room, request),
                connected_player_ids=set(room.players),
            )

            # 初始化游戏
            player_count = room.max_players if room.ai_fill else room.player_count
            engine.setup_room_game(
                [
                    (connected_player.player_id, connected_player.name)
                    for connected_player in room.players.values()
                ],
                total_player_count=player_count,
                seed=seed,
            )

            # 广播初始游戏状态
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

            # 交互式游戏循环
            while engine.state == GameState.IN_PROGRESS:
                current = engine.current_player
                player_conn = room.players.get(current.id)

                if player_conn and not current.is_ai:
                    await self._run_human_turn(room, engine, player_conn, current)
                else:
                    # AI 回合
                    await asyncio.to_thread(engine.run_headless_turn)

                await self._broadcast_game_state(room, engine)

                if engine.is_game_over():
                    break
                engine.next_turn()

            # 游戏结束
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
            logger.exception(f"游戏运行异常: {e}")
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
        """广播当前游戏状态给房间内所有玩家."""
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
        """执行真人玩家的主动回合流程."""
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
        """执行真人玩家的弃牌请求."""
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
        """等待并执行真人玩家的主动动作直到结束回合或超时."""
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
        """执行一条真人主动动作，返回是否应结束回合."""
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
        """处理玩家游戏操作.
        当有 pending action queue 且玩家 ID 匹配时，将动作压入队列。
        以推进异步游戏循环.
        """
        room = self.rooms.get(player.room_id or "")
        if not room or room.state != RoomState.PLAYING:
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.not_in_game"),
                    code=400,
                    error_code="E_GAME_NOT_IN_PROGRESS",
                ),
            )
            return

        # 解析当前等待中的真人动作队列
        pending = room._pending_action
        if pending is None:
            await self._send(
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
            await self._send(
                player,
                ServerMsg.error(
                    _t("error.not_your_turn"),
                    code=403,
                    error_code="E_GAME_NOT_YOUR_TURN",
                ),
            )
            return

        await action_queue.put(msg.data)

    async def _handle_game_response(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        """处理玩家响应."""
        room = self.rooms.get(player.room_id or "")
        if not room or room.state != RoomState.PLAYING:
            return
        try:
            request_id, response = decode_game_response(player.player_id, msg.data)
        except ValueError:
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.invalid_format"),
                    code=400,
                    error_code="E_PROTO_INVALID_FORMAT",
                ),
            )
            return

        pending = self._find_pending_request(
            room,
            player.player_id,
            request_id,
            response.request_type,
        )
        if pending is None:
            await self._send(
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

        await self._broadcast_game_event(
            room,
            "player_response",
            {
                "request_id": pending.request_id,
                "request_type": response.request_type.name.lower(),
                "player_id": player.player_id,
                "response": msg.data,
            },
        )

    async def _handle_hero_chosen(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        """处理选将."""
        room = self.rooms.get(player.room_id or "")
        if not room:
            return

        hero_id = msg.data.get("hero_id", "")
        await self._broadcast_game_event(
            room,
            "hero_chosen",
            {
                "player_id": player.player_id,
                "hero_id": hero_id,
            },
        )

    async def _handle_chat(self, player: ConnectedPlayer, msg: ClientMsg) -> None:
        """处理聊天 (含输入净化)."""
        room = self.rooms.get(player.room_id or "")
        if not room:
            return

        text = msg.data.get("message", "")
        text = sanitize_chat_message(text)
        if text:
            await self._broadcast_room(
                room,
                ServerMsg.chat_broadcast(player.name, text),
                exclude=player.player_id,
            )

    # ==================== 断线重连 ====================

    async def reconnect_player(
        self, player: ConnectedPlayer, room_id: str, last_seq: int, token: str = ""
    ) -> bool:
        """断线重连: 验证令牌并重放玩家缺失的事件.

        Args:
            player: 重连的玩家
            room_id: 房间 ID
            last_seq: 玩家最后收到的事件序号
            token: 重连令牌

        Returns:
            是否成功重连
        """
        # 令牌验证
        if token and not self._token_manager.verify(token, player.player_id):
            logger.warning(
                "Reconnect token verification failed player_id=%s room_id=%s",
                player.player_id,
                room_id,
            )
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.invalid_token"),
                    code=401,
                    error_code="E_AUTH_INVALID_TOKEN",
                ),
            )
            return False

        room = self.rooms.get(room_id)
        if not room:
            await self._send(
                player,
                ServerMsg.error(
                    _t("server.room_not_found"),
                    code=404,
                    error_code="E_ROOM_NOT_FOUND",
                ),
            )
            return False

        # 重新加入房间
        room.players[player.player_id] = player
        player.room_id = room_id

        # 重放缺失的事件
        missed = [e for e in room.event_log if e.seq > last_seq]
        for event in missed:
            await self._send(player, event)

        logger.info(f"玩家 {player.name} 重连成功 (重放 {len(missed)} 条事件)")
        return True

    # ==================== 心跳超时检测 ====================

    async def _heartbeat_checker(self) -> None:
        """后台任务: 定期检查心跳超时的连接并清理。."""
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
                    logger.info(f"玩家 {pid} 心跳超时，断开连接")
                    with suppress(Exception):
                        await stale_player.websocket.close(1001, _t("server.heartbeat_timeout"))
                    await self._unregister(stale_player.websocket)
            # 定期清理过期令牌
            self._token_manager.cleanup_expired()

    # ==================== 服务端生命周期 ====================

    async def _connection_handler(self, websocket: ServerConnection) -> None:
        """处理单个 WebSocket 连接."""
        # Origin 验证
        if not self._check_origin(websocket):
            await websocket.close(1008, "Origin not allowed")
            return

        player = await self._register(websocket)
        if player is None:
            return  # 连接被拒绝
        try:
            async for raw_message in websocket:
                payload = (
                    raw_message.decode("utf-8", errors="replace")
                    if isinstance(raw_message, bytes)
                    else raw_message
                )
                await self._handle_message(websocket, payload)
        except Exception as e:
            logger.warning(f"连接异常 (玩家{player.player_id}): {e}")
        finally:
            await self._unregister(websocket)

    def _build_ssl_context(self) -> ssl.SSLContext | None:
        """构建 SSL 上下文 (如果配置了证书)。."""
        if not self._ssl_cert or not self._ssl_key:
            return None

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self._ssl_cert, self._ssl_key)
        logger.info("已加载 TLS 证书")
        return ctx

    def _check_origin(self, websocket: ServerConnection) -> bool:
        """检查 WebSocket 握手中的 Origin 头。."""
        remote_ip = self._get_remote_ip(websocket)
        if not self._origin_validator.is_enabled:
            logger.warning(
                "Reject websocket handshake: origin allowlist disabled "
                "(fail-closed) remote_ip=%s",
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
        """为 websockets.serve 提供 origins 参数。."""
        if not self._origin_validator.is_enabled:
            return None
        return list(self._origin_validator.allowed_origins)

    async def start(self) -> None:
        """启动服务端."""
        try:
            import websockets
        except ImportError:
            logger.error("需要安装 websockets: pip install websockets")
            return

        self._running = True
        ssl_ctx = self._build_ssl_context()
        if not ssl_ctx:
            logger.warning(
                "Running without TLS (ws://). Auth tokens will be transmitted "
                "in plaintext. Use --ssl-cert and --ssl-key for production."
            )
        protocol = "wss" if ssl_ctx else "ws"
        logger.info(f"三国杀服务端启动: {protocol}://{self.host}:{self.port}")

        # 启动心跳超时检测后台任务
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
        """停止服务端."""
        self._running = False
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        logger.info("服务端停止")


# ==================== CLI 入口 ====================


def main() -> None:
    """命令行启动服务端."""
    import argparse

    parser = argparse.ArgumentParser(description="三国杀 WebSocket 服务端")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细日志")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    server = GameServer(host=args.host, port=args.port)
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
