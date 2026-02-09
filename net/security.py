"""网络安全模块 (Phase 4.4)

提供:
- ConnectionTokenManager: 基于 secrets 的连接令牌管理
- sanitize_chat_message: 聊天内容净化 (防 XSS / 注入)
- 安全相关常量
"""
from __future__ import annotations

import hmac
import html
import logging
import re
import secrets
import time

logger = logging.getLogger(__name__)

# ==================== 安全常量 ====================

# WebSocket 消息体最大字节数 (OWASP 建议 64KB 以下)
DEFAULT_MAX_MESSAGE_SIZE: int = 65_536  # 64 KB

# 连接限制
DEFAULT_MAX_CONNECTIONS: int = 200        # 服务器总连接上限
DEFAULT_MAX_CONNECTIONS_PER_IP: int = 8   # 单 IP 连接上限

# 心跳超时 (秒): 超过此时间未收到心跳则视为断线
DEFAULT_HEARTBEAT_TIMEOUT: float = 60.0

# 令牌字节长度 (256 bits = 32 bytes，secrets.token_urlsafe 输出 ~43 字符)
TOKEN_BYTES: int = 32

# 令牌过期时间 (秒)
TOKEN_EXPIRY: float = 86_400.0  # 24 小时


# ==================== 连接令牌管理 ====================

class ConnectionTokenManager:
    """基于 ``secrets`` 模块的连接令牌管理器。

    - 连接时生成不可伪造的随机令牌
    - 断线重连时验证令牌 (timing-safe comparison)
    - 令牌有过期时间
    """

    def __init__(self, expiry: float = TOKEN_EXPIRY):
        self._expiry = expiry
        # token -> (player_id, created_at)
        self._tokens: dict[str, tuple[int, float]] = {}
        # player_id -> token (反向索引，方便按玩家查找)
        self._player_tokens: dict[int, str] = {}

    def issue(self, player_id: int) -> str:
        """为玩家签发新令牌。"""
        token = secrets.token_urlsafe(TOKEN_BYTES)
        now = time.time()
        # 清除该玩家的旧令牌
        old = self._player_tokens.pop(player_id, None)
        if old:
            self._tokens.pop(old, None)
        self._tokens[token] = (player_id, now)
        self._player_tokens[player_id] = token
        return token

    def verify(self, token: str, expected_player_id: int) -> bool:
        """验证令牌是否属于指定玩家且未过期。

        使用 ``hmac.compare_digest`` 防止时序攻击。
        """
        record = self._tokens.get(token)
        if record is None:
            return False
        pid, created = record
        # 时序安全比较令牌值
        stored_token = self._player_tokens.get(expected_player_id, "")
        if not hmac.compare_digest(token, stored_token):
            return False
        # 检查过期
        if time.time() - created > self._expiry:
            self.revoke(player_id=expected_player_id)
            return False
        return pid == expected_player_id

    def revoke(self, *, player_id: int | None = None,
               token: str | None = None) -> None:
        """撤销令牌 (按玩家 ID 或按令牌)。"""
        if player_id is not None:
            tok = self._player_tokens.pop(player_id, None)
            if tok:
                self._tokens.pop(tok, None)
        if token is not None:
            record = self._tokens.pop(token, None)
            if record:
                self._player_tokens.pop(record[0], None)

    def cleanup_expired(self) -> int:
        """清理所有过期令牌，返回清理数量。"""
        now = time.time()
        expired = [
            tok for tok, (_, created) in self._tokens.items()
            if now - created > self._expiry
        ]
        for tok in expired:
            record = self._tokens.pop(tok, None)
            if record:
                self._player_tokens.pop(record[0], None)
        return len(expired)

    @property
    def active_count(self) -> int:
        return len(self._tokens)


# ==================== 输入净化 ====================

# 匹配 HTML 标签 (简单版，覆盖 <script>...</script> 等)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def sanitize_chat_message(text: str, max_length: int = 500) -> str:
    """净化聊天消息内容。

    1. 截断到最大长度
    2. 转义 HTML 特殊字符 (防 XSS)
    3. 移除残余 HTML 标签
    4. 去除首尾空白

    Returns:
        净化后的安全文本
    """
    # 截断
    text = text[:max_length]
    # HTML 转义
    text = html.escape(text, quote=True)
    # 移除残余标签 (理论上 html.escape 后已不含，但做双重保障)
    text = _HTML_TAG_RE.sub("", text)
    return text.strip()


# ==================== IP 连接计数 ====================

class IPConnectionTracker:
    """跟踪每个 IP 的活跃连接数。"""

    def __init__(self, max_per_ip: int = DEFAULT_MAX_CONNECTIONS_PER_IP):
        self._max_per_ip = max_per_ip
        self._counts: dict[str, int] = {}

    def can_connect(self, ip: str) -> bool:
        """检查该 IP 是否还能建立新连接。"""
        return self._counts.get(ip, 0) < self._max_per_ip

    def add(self, ip: str) -> None:
        self._counts[ip] = self._counts.get(ip, 0) + 1

    def remove(self, ip: str) -> None:
        count = self._counts.get(ip, 0)
        if count <= 1:
            self._counts.pop(ip, None)
        else:
            self._counts[ip] = count - 1

    def get_count(self, ip: str) -> int:
        return self._counts.get(ip, 0)
