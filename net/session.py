"""玩家会话管理 — 支持断线重连

提供基于令牌的会话持久化，允许断线玩家在超时期内
使用原始令牌重新连接并恢复游戏状态。
"""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PlayerSession:
    """玩家会话信息"""

    player_id: str
    token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    room_id: str | None = None
    connected: bool = True
    last_seen: float = field(default_factory=time.time)
    game_seat: int | None = None  # 游戏中的座位号


class SessionManager:
    """会话管理器

    维护玩家会话状态，支持断线重连。
    断线超过 timeout 秒后会话过期。

    Args:
        timeout: 会话超时秒数（默认 300 秒 = 5 分钟）
    """

    def __init__(self, timeout: float = 300.0) -> None:
        self._sessions: dict[str, PlayerSession] = {}  # player_id → session
        self._token_index: dict[str, str] = {}  # token → player_id
        self._timeout = timeout

    def create(self, player_id: str, room_id: str | None = None) -> PlayerSession:
        """创建新会话

        Args:
            player_id: 玩家标识
            room_id: 所在房间 ID

        Returns:
            新创建的会话
        """
        # 如果已有旧会话，先清理
        old = self._sessions.pop(player_id, None)
        if old:
            self._token_index.pop(old.token, None)

        session = PlayerSession(player_id=player_id, room_id=room_id)
        self._sessions[player_id] = session
        self._token_index[session.token] = player_id
        logger.info("Session created: player=%s", player_id)
        return session

    def get(self, player_id: str) -> PlayerSession | None:
        """获取玩家会话"""
        return self._sessions.get(player_id)

    def reconnect(self, token: str) -> PlayerSession | None:
        """使用令牌尝试重连

        Args:
            token: 玩家持有的会话令牌

        Returns:
            成功重连返回会话，令牌无效或过期返回 None
        """
        player_id = self._token_index.get(token)
        if not player_id:
            logger.warning("Reconnect failed: unknown token")
            return None

        session = self._sessions.get(player_id)
        if not session:
            logger.warning("Reconnect failed: session not found for player=%s", player_id)
            self._token_index.pop(token, None)
            return None

        # 检查超时
        if time.time() - session.last_seen > self._timeout:
            logger.info("Reconnect failed: session expired for player=%s", player_id)
            self._remove(player_id)
            return None

        session.connected = True
        session.last_seen = time.time()
        logger.info("Player reconnected: %s", player_id)
        return session

    def disconnect(self, player_id: str) -> None:
        """标记玩家断线（保留会话用于重连）"""
        session = self._sessions.get(player_id)
        if session:
            session.connected = False
            session.last_seen = time.time()
            logger.info("Player disconnected: %s", player_id)

    def remove(self, player_id: str) -> None:
        """彻底移除会话"""
        self._remove(player_id)

    def _remove(self, player_id: str) -> None:
        session = self._sessions.pop(player_id, None)
        if session:
            self._token_index.pop(session.token, None)

    def cleanup_expired(self) -> int:
        """清理所有过期会话，返回清理数量"""
        now = time.time()
        expired = [
            pid
            for pid, s in self._sessions.items()
            if not s.connected and now - s.last_seen > self._timeout
        ]
        for pid in expired:
            self._remove(pid)
        return len(expired)

    @property
    def active_count(self) -> int:
        """活跃（已连接）会话数"""
        return sum(1 for s in self._sessions.values() if s.connected)

    @property
    def total_count(self) -> int:
        """总会话数（含断线未过期的）"""
        return len(self._sessions)
