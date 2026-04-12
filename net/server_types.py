"""WebSocket 服务端类型定义.

将 server.py 中的数据模型抽离，降低主服务文件复杂度。
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .protocol import RoomState, ServerMsg

if TYPE_CHECKING:
    from websockets.asyncio.server import ServerConnection

    from game.actions import GameResponse, RequestType
    from game.engine import GameEngine


@dataclass
class ConnectedPlayer:
    """已连接的玩家."""

    player_id: int
    name: str
    websocket: ServerConnection
    room_id: str | None = None
    ready: bool = False
    last_heartbeat: float = field(default_factory=time.time)
    last_seq: int = 0  # 最后收到的事件序号 (用于断线重连)
    auth_token: str = ""  # 连接令牌 (用于重连验证)
    remote_ip: str = ""  # 客户端 IP
    # 速率限制: 滑动窗口内的消息时间戳
    _msg_timestamps: list[float] = field(default_factory=list)


@dataclass
class PendingGameRequest:
    """等待中的网络请求."""

    request_id: str
    player_id: int
    request_type: RequestType
    future: asyncio.Future[GameResponse]


@dataclass
class Room:
    """游戏房间."""

    room_id: str
    host_id: int  # 房主 player_id
    max_players: int = 4
    ai_fill: bool = True  # 不足时 AI 填充
    state: RoomState = RoomState.WAITING
    players: dict[int, ConnectedPlayer] = field(default_factory=dict)
    # 游戏事件日志 (用于断线重连)
    event_log: list[ServerMsg] = field(default_factory=list)
    event_seq: int = 0
    # 引擎引用 (游戏进行中)
    engine: GameEngine | None = None
    game_seed: int | None = None
    # 当前等待人类玩家动作的队列 (player_id, queue)
    _pending_action: tuple[int, asyncio.Queue[dict[str, Any]]] | None = None
    # 当前等待中的网络请求 (request_id -> pending request)
    _pending_requests: dict[str, PendingGameRequest] = field(default_factory=dict)

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def is_full(self) -> bool:
        return self.player_count >= self.max_players

    def player_list_data(self) -> list[dict[str, Any]]:
        """返回玩家列表的序列化数据."""
        return [
            {"player_id": p.player_id, "name": p.name, "ready": p.ready}
            for p in self.players.values()
        ]

    def next_seq(self) -> int:
        """获取下一个事件序号."""
        self.event_seq += 1
        return self.event_seq
