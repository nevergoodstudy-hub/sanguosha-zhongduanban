# -*- coding: utf-8 -*-
"""
WebSocket 游戏服务端 (M4-T02)
基于 asyncio 的三国杀网络对战服务端

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
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Any, TYPE_CHECKING

from .protocol import MsgType, RoomState, ServerMsg, ClientMsg, parse_message

logger = logging.getLogger(__name__)


# ==================== 数据模型 ====================

@dataclass
class ConnectedPlayer:
    """已连接的玩家"""
    player_id: int
    name: str
    websocket: Any  # websockets.WebSocketServerProtocol
    room_id: Optional[str] = None
    ready: bool = False
    last_heartbeat: float = field(default_factory=time.time)
    last_seq: int = 0  # 最后收到的事件序号 (用于断线重连)
    # 速率限制: 滑动窗口内的消息时间戳
    _msg_timestamps: List[float] = field(default_factory=list)


@dataclass
class Room:
    """游戏房间"""
    room_id: str
    host_id: int               # 房主 player_id
    max_players: int = 4
    ai_fill: bool = True       # 不足时 AI 填充
    state: RoomState = RoomState.WAITING
    players: Dict[int, ConnectedPlayer] = field(default_factory=dict)
    # 游戏事件日志 (用于断线重连)
    event_log: List[ServerMsg] = field(default_factory=list)
    event_seq: int = 0
    # 引擎引用 (游戏进行中)
    engine: Any = None
    game_seed: Optional[int] = None

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def is_full(self) -> bool:
        return self.player_count >= self.max_players

    def player_list_data(self) -> List[Dict[str, Any]]:
        """返回玩家列表的序列化数据"""
        return [
            {"player_id": p.player_id, "name": p.name, "ready": p.ready}
            for p in self.players.values()
        ]

    def next_seq(self) -> int:
        """获取下一个事件序号"""
        self.event_seq += 1
        return self.event_seq


# ==================== 服务端核心 ====================

# 速率限制默认值
RATE_LIMIT_WINDOW: float = 1.0   # 滑动窗口 (秒)
RATE_LIMIT_MAX_MSGS: int = 30    # 窗口内最大消息数


class GameServer:
    """
    三国杀 WebSocket 游戏服务端

    职责:
    1. 管理 WebSocket 连接
    2. 房间生命周期管理
    3. 将引擎事件广播给客户端
    4. 路由客户端消息到对应处理器
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765,
                 rate_limit_window: float = RATE_LIMIT_WINDOW,
                 rate_limit_max_msgs: int = RATE_LIMIT_MAX_MSGS):
        self.host = host
        self.port = port
        # 速率限制参数
        self._rate_window = rate_limit_window
        self._rate_max = rate_limit_max_msgs
        # 连接管理
        self.connections: Dict[int, ConnectedPlayer] = {}  # player_id → player
        self.ws_to_player: Dict[Any, int] = {}  # websocket → player_id
        self._next_player_id: int = 1
        # 房间管理
        self.rooms: Dict[str, Room] = {}  # room_id → room
        # 消息路由表
        self._handlers: Dict[MsgType, Any] = {
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

    # ==================== 连接管理 ====================

    def _assign_player_id(self) -> int:
        """分配唯一玩家 ID"""
        pid = self._next_player_id
        self._next_player_id += 1
        return pid

    async def _register(self, websocket: Any) -> ConnectedPlayer:
        """注册新连接"""
        pid = self._assign_player_id()
        player = ConnectedPlayer(
            player_id=pid,
            name=f"玩家{pid}",
            websocket=websocket,
        )
        self.connections[pid] = player
        self.ws_to_player[websocket] = pid
        logger.info(f"玩家 {pid} 已连接")
        return player

    async def _unregister(self, websocket: Any) -> None:
        """注销连接"""
        pid = self.ws_to_player.pop(websocket, None)
        if pid is None:
            return
        player = self.connections.pop(pid, None)
        if player and player.room_id:
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
        """发送消息给单个玩家"""
        try:
            await player.websocket.send(msg.to_json())
        except Exception as e:
            logger.warning(f"发送消息失败 (玩家{player.player_id}): {e}")

    async def _broadcast_room(self, room: Room, msg: ServerMsg,
                              exclude: Optional[int] = None) -> None:
        """广播消息给房间内所有玩家"""
        for pid, player in room.players.items():
            if pid != exclude:
                await self._send(player, msg)

    async def _broadcast_room_update(self, room: Room) -> None:
        """广播房间状态更新"""
        msg = ServerMsg.room_update(room.room_id, room.player_list_data(), room.state)
        await self._broadcast_room(room, msg)

    async def _broadcast_game_event(self, room: Room, event_type: str,
                                    event_data: Dict[str, Any]) -> None:
        """广播游戏事件并记录到事件日志"""
        seq = room.next_seq()
        msg = ServerMsg.game_event(event_type, event_data, seq=seq)
        room.event_log.append(msg)
        await self._broadcast_room(room, msg)

    # ==================== 消息路由 ====================

    def _check_rate_limit(self, player: ConnectedPlayer) -> bool:
        """检查玩家是否超出消息速率限制。

        Returns:
            True 表示允许处理, False 表示应丢弃
        """
        now = time.time()
        cutoff = now - self._rate_window
        # 清除过期时间戳
        ts = player._msg_timestamps
        while ts and ts[0] < cutoff:
            ts.pop(0)
        if len(ts) >= self._rate_max:
            return False
        ts.append(now)
        return True

    async def _handle_message(self, websocket: Any, raw: str) -> None:
        """路由消息到对应处理器"""
        try:
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
                await self._send(player, ServerMsg.error("消息过快，请稍后再试"))
                return

            # 覆盖 player_id 为服务端分配的 (防伪造)
            client_msg.player_id = player.player_id

            handler = self._handlers.get(msg_type)
            if handler:
                await handler(player, client_msg)
            else:
                await self._send(player, ServerMsg.error(f"未知消息类型: {type_str}"))

        except json.JSONDecodeError:
            logger.warning("收到无效 JSON")
        except ValueError as e:
            logger.warning(f"消息解析错误: {e}")
        except Exception as e:
            logger.exception(f"处理消息异常: {e}")

    # ==================== 房间管理处理器 ====================

    async def _handle_heartbeat(self, player: ConnectedPlayer,
                                msg: ClientMsg) -> None:
        player.last_heartbeat = time.time()
        await self._send(player, ServerMsg.heartbeat_ack())

    async def _handle_room_create(self, player: ConnectedPlayer,
                                  msg: ClientMsg) -> None:
        if player.room_id:
            await self._send(player, ServerMsg.error("已在房间中"))
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
        await self._send(player, ServerMsg.room_created(room_id, {
            "max_players": max_players,
            "ai_fill": ai_fill,
            "host_id": player.player_id,
        }))

    async def _handle_room_join(self, player: ConnectedPlayer,
                                msg: ClientMsg) -> None:
        if player.room_id:
            await self._send(player, ServerMsg.error("已在房间中"))
            return

        room_id = msg.data.get("room_id", "")
        room = self.rooms.get(room_id)
        if not room:
            await self._send(player, ServerMsg.error("房间不存在"))
            return
        if room.is_full:
            await self._send(player, ServerMsg.error("房间已满"))
            return
        if room.state != RoomState.WAITING:
            await self._send(player, ServerMsg.error("游戏已开始"))
            return

        player_name = msg.data.get("player_name", player.name)
        player.name = player_name
        room.players[player.player_id] = player
        player.room_id = room_id

        logger.info(f"玩家 {player.name} 加入房间 {room_id}")
        await self._send(player, ServerMsg.room_joined(
            room_id, player.player_id, player.name, room.player_list_data()
        ))
        await self._broadcast_room_update(room)

    async def _handle_room_leave(self, player: ConnectedPlayer,
                                 msg: ClientMsg) -> None:
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

    async def _handle_room_list(self, player: ConnectedPlayer,
                                msg: ClientMsg) -> None:
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

    async def _handle_room_ready(self, player: ConnectedPlayer,
                                 msg: ClientMsg) -> None:
        player.ready = msg.data.get("ready", True)
        room = self.rooms.get(player.room_id or "")
        if room:
            await self._broadcast_room_update(room)

    async def _handle_room_start(self, player: ConnectedPlayer,
                                 msg: ClientMsg) -> None:
        """房主开始游戏"""
        room = self.rooms.get(player.room_id or "")
        if not room:
            await self._send(player, ServerMsg.error("不在房间中"))
            return
        if room.host_id != player.player_id:
            await self._send(player, ServerMsg.error("只有房主可以开始游戏"))
            return
        if room.state != RoomState.WAITING:
            await self._send(player, ServerMsg.error("游戏已在进行中"))
            return

        room.state = RoomState.PLAYING
        await self._broadcast_room(room, ServerMsg(type=MsgType.ROOM_STARTED))
        logger.info(f"房间 {room.room_id} 游戏开始 ({room.player_count} 人)")

        # 启动游戏引擎 (异步)
        asyncio.create_task(self._run_game(room))

    # ==================== 游戏逻辑 ====================

    async def _run_game(self, room: Room) -> None:
        """
        在房间中启动游戏引擎

        当前实现: 创建 headless 引擎，通过事件广播同步状态
        引擎运行在 executor 中 (避免阻塞事件循环)
        """
        try:
            import random
            from game.engine import GameEngine

            seed = random.randint(0, 2**32 - 1)
            room.game_seed = seed

            engine = GameEngine()
            room.engine = engine

            # 初始化 headless 游戏
            player_count = room.max_players if room.ai_fill else room.player_count
            engine.setup_headless_game(player_count, seed=seed)

            # 广播初始游戏状态
            state_data = {
                "player_count": player_count,
                "seed": seed,
                "players": [
                    {"id": p.id, "name": p.name, "identity": p.identity.value}
                    for p in engine.players
                ] if engine.players else [],
            }
            await self._broadcast_room(room, ServerMsg.game_state(state_data))

            # 通知游戏结束 (headless 模式立即结束)
            winner = engine.winner_identity.value if engine.winner_identity else "unknown"
            await self._broadcast_room(room, ServerMsg.game_over(
                winner=winner,
                reason="游戏结束",
                stats={"rounds": engine.round_count, "seed": seed},
            ))
            room.state = RoomState.FINISHED

        except Exception as e:
            logger.exception(f"游戏运行异常: {e}")
            await self._broadcast_room(room, ServerMsg.error(f"游戏异常: {e}"))
            room.state = RoomState.FINISHED

    async def _handle_game_action(self, player: ConnectedPlayer,
                                  msg: ClientMsg) -> None:
        """处理玩家游戏操作"""
        room = self.rooms.get(player.room_id or "")
        if not room or room.state != RoomState.PLAYING:
            await self._send(player, ServerMsg.error("不在游戏中"))
            return

        # 广播玩家操作给其他人
        await self._broadcast_game_event(room, "player_action", {
            "player_id": player.player_id,
            "action": msg.data,
        })

    async def _handle_game_response(self, player: ConnectedPlayer,
                                    msg: ClientMsg) -> None:
        """处理玩家响应"""
        room = self.rooms.get(player.room_id or "")
        if not room or room.state != RoomState.PLAYING:
            return

        await self._broadcast_game_event(room, "player_response", {
            "player_id": player.player_id,
            "response": msg.data,
        })

    async def _handle_hero_chosen(self, player: ConnectedPlayer,
                                  msg: ClientMsg) -> None:
        """处理选将"""
        room = self.rooms.get(player.room_id or "")
        if not room:
            return

        hero_id = msg.data.get("hero_id", "")
        await self._broadcast_game_event(room, "hero_chosen", {
            "player_id": player.player_id,
            "hero_id": hero_id,
        })

    async def _handle_chat(self, player: ConnectedPlayer,
                           msg: ClientMsg) -> None:
        """处理聊天"""
        room = self.rooms.get(player.room_id or "")
        if not room:
            return

        text = msg.data.get("message", "")
        if text:
            await self._broadcast_room(
                room,
                ServerMsg.chat_broadcast(player.name, text),
                exclude=player.player_id,
            )

    # ==================== 断线重连 ====================

    async def reconnect_player(self, player: ConnectedPlayer,
                               room_id: str, last_seq: int) -> bool:
        """
        断线重连: 重放玩家缺失的事件

        Args:
            player: 重连的玩家
            room_id: 房间 ID
            last_seq: 玩家最后收到的事件序号

        Returns:
            是否成功重连
        """
        room = self.rooms.get(room_id)
        if not room:
            await self._send(player, ServerMsg.error("房间不存在"))
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

    # ==================== 服务端生命周期 ====================

    async def _connection_handler(self, websocket: Any) -> None:
        """处理单个 WebSocket 连接"""
        player = await self._register(websocket)
        try:
            async for raw_message in websocket:
                await self._handle_message(websocket, raw_message)
        except Exception as e:
            logger.warning(f"连接异常 (玩家{player.player_id}): {e}")
        finally:
            await self._unregister(websocket)

    async def start(self) -> None:
        """启动服务端"""
        try:
            import websockets
        except ImportError:
            logger.error("需要安装 websockets: pip install websockets")
            return

        self._running = True
        logger.info(f"三国杀服务端启动: ws://{self.host}:{self.port}")

        async with websockets.serve(self._connection_handler, self.host, self.port):
            while self._running:
                await asyncio.sleep(1)

    def stop(self) -> None:
        """停止服务端"""
        self._running = False
        logger.info("服务端停止")


# ==================== CLI 入口 ====================

def main():
    """命令行启动服务端"""
    import argparse

    parser = argparse.ArgumentParser(description="三国杀 WebSocket 服务端")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
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
