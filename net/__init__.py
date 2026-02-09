"""网络对战模块 (M4)
基于 WebSocket 的 C/S 架构
"""

from .client import GameClient
from .protocol import ClientMsg, MsgType, RoomState, ServerMsg
from .server import ConnectedPlayer, GameServer, Room

__all__ = [
    "MsgType", "ServerMsg", "ClientMsg", "RoomState",
    "GameServer", "Room", "ConnectedPlayer",
    "GameClient",
]
