"""网络协议定义 (M4-T01)
基于 WebSocket 的 JSON 消息格式

协议设计:
- 客户端 → 服务端: ClientMsg (动作/请求)
- 服务端 → 客户端: ServerMsg (事件/状态)
- 所有消息均为 JSON，包含 type 字段用于路由
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ==================== 消息类型枚举 ====================

class MsgType(Enum):
    """网络消息类型"""

    # ---- 连接管理 ----
    HEARTBEAT = "heartbeat"             # 心跳
    HEARTBEAT_ACK = "heartbeat_ack"     # 心跳响应
    ERROR = "error"                     # 错误
    DISCONNECT = "disconnect"           # 断开连接

    # ---- 房间管理 (Client → Server) ----
    ROOM_CREATE = "room_create"         # 创建房间
    ROOM_JOIN = "room_join"             # 加入房间
    ROOM_LEAVE = "room_leave"           # 离开房间
    ROOM_LIST = "room_list"             # 列出房间
    ROOM_READY = "room_ready"           # 准备
    ROOM_START = "room_start"           # 开始游戏 (房主)

    # ---- 房间管理 (Server → Client) ----
    ROOM_CREATED = "room_created"       # 房间已创建
    ROOM_JOINED = "room_joined"         # 已加入房间
    ROOM_LEFT = "room_left"             # 已离开房间
    ROOM_LISTING = "room_listing"       # 房间列表
    ROOM_UPDATE = "room_update"         # 房间状态更新
    ROOM_STARTED = "room_started"       # 游戏已开始

    # ---- 游戏流程 (Server → Client) ----
    GAME_STATE = "game_state"           # 完整游戏状态 (初始/重连)
    GAME_EVENT = "game_event"           # 增量游戏事件
    GAME_REQUEST = "game_request"       # 请求玩家输入
    GAME_OVER = "game_over"             # 游戏结束

    # ---- 游戏流程 (Client → Server) ----
    GAME_ACTION = "game_action"         # 玩家操作
    GAME_RESPONSE = "game_response"     # 玩家响应请求

    # ---- 选将 ----
    HERO_OPTIONS = "hero_options"       # 服务端发送可选武将
    HERO_CHOSEN = "hero_chosen"         # 客户端选择武将

    # ---- 聊天 ----
    CHAT = "chat"                       # 聊天消息
    CHAT_BROADCAST = "chat_broadcast"   # 聊天广播


class RoomState(Enum):
    """房间状态"""
    WAITING = "waiting"     # 等待中
    FULL = "full"           # 已满
    PLAYING = "playing"     # 游戏中
    FINISHED = "finished"   # 已结束


# ==================== 消息数据类 ====================

@dataclass
class ServerMsg:
    """服务端 → 客户端消息

    所有服务端发出的消息都使用此格式:
    {
        "type": "game_event",
        "seq": 42,
        "timestamp": 1706000000.0,
        "data": { ... }
    }
    """
    type: MsgType
    data: dict[str, Any] = field(default_factory=dict)
    seq: int = 0                # 消息序号 (用于断线重连)
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps({
            "type": self.type.value,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "data": self.data,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> ServerMsg:
        """从 JSON 字符串反序列化"""
        obj = json.loads(raw)
        return cls(
            type=MsgType(obj["type"]),
            data=obj.get("data", {}),
            seq=obj.get("seq", 0),
            timestamp=obj.get("timestamp", 0.0),
        )

    # ---------- 工厂方法 ----------

    @classmethod
    def error(cls, message: str, code: int = 400) -> ServerMsg:
        return cls(type=MsgType.ERROR, data={"message": message, "code": code})

    @classmethod
    def heartbeat_ack(cls) -> ServerMsg:
        return cls(type=MsgType.HEARTBEAT_ACK)

    @classmethod
    def room_created(cls, room_id: str, room_info: dict[str, Any]) -> ServerMsg:
        return cls(type=MsgType.ROOM_CREATED, data={"room_id": room_id, **room_info})

    @classmethod
    def room_joined(cls, room_id: str, player_id: int, player_name: str,
                    players: list[dict[str, Any]]) -> ServerMsg:
        return cls(type=MsgType.ROOM_JOINED, data={
            "room_id": room_id,
            "player_id": player_id,
            "player_name": player_name,
            "players": players,
        })

    @classmethod
    def room_update(cls, room_id: str, players: list[dict[str, Any]],
                    state: RoomState) -> ServerMsg:
        return cls(type=MsgType.ROOM_UPDATE, data={
            "room_id": room_id,
            "players": players,
            "state": state.value,
        })

    @classmethod
    def room_listing(cls, rooms: list[dict[str, Any]]) -> ServerMsg:
        return cls(type=MsgType.ROOM_LISTING, data={"rooms": rooms})

    @classmethod
    def game_state(cls, state: dict[str, Any]) -> ServerMsg:
        """完整游戏状态 (初始化 / 断线重连)"""
        return cls(type=MsgType.GAME_STATE, data=state)

    @classmethod
    def game_event(cls, event_type: str, event_data: dict[str, Any],
                   seq: int = 0) -> ServerMsg:
        """增量游戏事件"""
        return cls(type=MsgType.GAME_EVENT, seq=seq, data={
            "event_type": event_type,
            **event_data,
        })

    @classmethod
    def game_request(cls, request_type: str, player_id: int,
                     options: dict[str, Any] = None,
                     timeout: float = 30.0) -> ServerMsg:
        """请求玩家输入"""
        return cls(type=MsgType.GAME_REQUEST, data={
            "request_type": request_type,
            "player_id": player_id,
            "options": options or {},
            "timeout": timeout,
        })

    @classmethod
    def game_over(cls, winner: str, reason: str,
                  stats: dict[str, Any] = None) -> ServerMsg:
        return cls(type=MsgType.GAME_OVER, data={
            "winner": winner,
            "reason": reason,
            "stats": stats or {},
        })

    @classmethod
    def hero_options(cls, player_id: int, heroes: list[dict[str, Any]]) -> ServerMsg:
        return cls(type=MsgType.HERO_OPTIONS, data={
            "player_id": player_id,
            "heroes": heroes,
        })

    @classmethod
    def chat_broadcast(cls, player_name: str, message: str) -> ServerMsg:
        return cls(type=MsgType.CHAT_BROADCAST, data={
            "player_name": player_name,
            "message": message,
        })


@dataclass
class ClientMsg:
    """客户端 → 服务端消息

    格式:
    {
        "type": "game_action",
        "player_id": 1,
        "timestamp": 1706000000.0,
        "data": { ... }
    }
    """
    type: MsgType
    player_id: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        """序列化为 JSON 字符串"""
        return json.dumps({
            "type": self.type.value,
            "player_id": self.player_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> ClientMsg:
        """从 JSON 字符串反序列化"""
        obj = json.loads(raw)
        return cls(
            type=MsgType(obj["type"]),
            player_id=obj.get("player_id", 0),
            data=obj.get("data", {}),
            timestamp=obj.get("timestamp", 0.0),
        )

    # ---------- 工厂方法 ----------

    @classmethod
    def heartbeat(cls, player_id: int = 0) -> ClientMsg:
        return cls(type=MsgType.HEARTBEAT, player_id=player_id)

    @classmethod
    def room_create(cls, player_id: int, player_name: str,
                    max_players: int = 4, ai_fill: bool = True) -> ClientMsg:
        return cls(type=MsgType.ROOM_CREATE, player_id=player_id, data={
            "player_name": player_name,
            "max_players": max_players,
            "ai_fill": ai_fill,
        })

    @classmethod
    def room_join(cls, player_id: int, player_name: str,
                  room_id: str) -> ClientMsg:
        return cls(type=MsgType.ROOM_JOIN, player_id=player_id, data={
            "player_name": player_name,
            "room_id": room_id,
        })

    @classmethod
    def room_leave(cls, player_id: int) -> ClientMsg:
        return cls(type=MsgType.ROOM_LEAVE, player_id=player_id)

    @classmethod
    def room_list(cls) -> ClientMsg:
        return cls(type=MsgType.ROOM_LIST)

    @classmethod
    def room_ready(cls, player_id: int, ready: bool = True) -> ClientMsg:
        return cls(type=MsgType.ROOM_READY, player_id=player_id, data={"ready": ready})

    @classmethod
    def room_start(cls, player_id: int) -> ClientMsg:
        return cls(type=MsgType.ROOM_START, player_id=player_id)

    @classmethod
    def game_action(cls, player_id: int, action_type: str,
                    action_data: dict[str, Any] = None) -> ClientMsg:
        """玩家主动操作 (出牌/技能/弃牌/结束)"""
        return cls(type=MsgType.GAME_ACTION, player_id=player_id, data={
            "action_type": action_type,
            **(action_data or {}),
        })

    @classmethod
    def game_response(cls, player_id: int, request_type: str,
                      accepted: bool = False,
                      response_data: dict[str, Any] = None) -> ClientMsg:
        """玩家响应请求 (出闪/出杀/出桃等)"""
        return cls(type=MsgType.GAME_RESPONSE, player_id=player_id, data={
            "request_type": request_type,
            "accepted": accepted,
            **(response_data or {}),
        })

    @classmethod
    def hero_chosen(cls, player_id: int, hero_id: str) -> ClientMsg:
        return cls(type=MsgType.HERO_CHOSEN, player_id=player_id, data={
            "hero_id": hero_id,
        })

    @classmethod
    def chat(cls, player_id: int, message: str) -> ClientMsg:
        return cls(type=MsgType.CHAT, player_id=player_id, data={
            "message": message,
        })


# ==================== 工具函数 ====================

def parse_message(raw: str) -> tuple[str, dict]:
    """快速解析 JSON 消息，返回 (type_str, full_dict)

    用于路由层在不构造完整对象时快速判断消息类型
    """
    obj = json.loads(raw)
    return obj.get("type", ""), obj


def validate_msg_type(type_str: str) -> bool:
    """检查消息类型是否合法"""
    try:
        MsgType(type_str)
        return True
    except ValueError:
        return False
