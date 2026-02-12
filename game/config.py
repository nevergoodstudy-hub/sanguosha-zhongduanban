"""游戏配置中心 (SSOT - 单一事实来源)

所有可配置的游戏参数应在此定义，支持从环境变量覆盖。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _get_env_float(key: str, default: float) -> float:
    """从环境变量获取浮点数配置"""
    value = os.environ.get(key)
    if value is not None:
        try:
            return float(value)
        except ValueError:
            pass
    return default


def _get_env_int(key: str, default: int) -> int:
    """从环境变量获取整数配置"""
    value = os.environ.get(key)
    if value is not None:
        try:
            return int(value)
        except ValueError:
            pass
    return default


def _get_env_bool(key: str, default: bool) -> bool:
    """从环境变量获取布尔配置"""
    value = os.environ.get(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    return default


@dataclass(frozen=True)
class GameConfig:
    """游戏配置类 (不可变)
    
    所有配置项支持通过环境变量覆盖：
    - SANGUOSHA_AI_DELAY: AI 回合延迟秒数
    - SANGUOSHA_PLAY_TIMEOUT: 出牌阶段超时秒数
    - SANGUOSHA_MAX_ACTIONS: AI 单回合最大动作数
    - SANGUOSHA_COVERAGE_THRESHOLD: 测试覆盖率阈值
    """
    # ==================== 玩家与游戏规模 ====================
    min_players: int = 2
    max_players: int = 8
    initial_hand_size: int = 4
    default_draw_count: int = 2
    default_sha_limit: int = 1

    # ==================== 时间与延迟 ====================
    ai_turn_delay: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_AI_DELAY", 0.3)
    )
    play_phase_timeout: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_PLAY_TIMEOUT", 30)
    )
    request_timeout: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_REQUEST_TIMEOUT", 15.0)
    )

    # ==================== AI 配置 ====================
    ai_max_actions: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_MAX_ACTIONS", 10)
    )
    ai_think_delay: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_AI_THINK_DELAY", 0.5)
    )

    # ==================== 网络配置 ====================
    websocket_port: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_WS_PORT", 8765)
    )
    heartbeat_interval: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_HEARTBEAT", 15.0)
    )
    reconnect_delay: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_RECONNECT_DELAY", 2.0)
    )
    max_reconnect_attempts: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_MAX_RECONNECT", 5)
    )

    # ==================== 网络安全 ====================
    ws_max_message_size: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_WS_MAX_MSG_SIZE", 65_536)
    )
    ws_max_connections: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_WS_MAX_CONN", 200)
    )
    ws_max_connections_per_ip: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_WS_MAX_CONN_PER_IP", 8)
    )
    ws_heartbeat_timeout: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_WS_HB_TIMEOUT", 60.0)
    )
    ws_rate_limit_window: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_WS_RATE_WINDOW", 1.0)
    )
    ws_rate_limit_max_msgs: int = field(
        default_factory=lambda: _get_env_int("SANGUOSHA_WS_RATE_MAX", 30)
    )

    # TLS 配置
    ws_ssl_cert: str = field(
        default_factory=lambda: os.environ.get("SANGUOSHA_WS_SSL_CERT", "")
    )
    ws_ssl_key: str = field(
        default_factory=lambda: os.environ.get("SANGUOSHA_WS_SSL_KEY", "")
    )

    # Origin 白名单 (逗号分隔，空表示允许所有)
    ws_allowed_origins: str = field(
        default_factory=lambda: os.environ.get("SANGUOSHA_WS_ALLOWED_ORIGINS", "")
    )

    # ==================== 日志与调试 ====================
    log_level: str = field(
        default_factory=lambda: os.environ.get("SANGUOSHA_LOG_LEVEL", "INFO")
    )
    debug_mode: bool = field(
        default_factory=lambda: _get_env_bool("SANGUOSHA_DEBUG", False)
    )

    # ==================== 测试配置 ====================
    coverage_threshold: float = field(
        default_factory=lambda: _get_env_float("SANGUOSHA_COVERAGE", 0.50)
    )

    @classmethod
    def from_env(cls) -> GameConfig:
        """从环境变量创建配置实例"""
        return cls()

    def get(self, key: str, default: any | None = None) -> any:
        """字典风格的访问方法（兼容旧代码）"""
        return getattr(self, key, default)


# 全局配置单例
_config: GameConfig | None = None


def get_config() -> GameConfig:
    """获取全局配置实例（懒加载）"""
    global _config
    if _config is None:
        _config = GameConfig.from_env()
    return _config


def reset_config() -> None:
    """重置配置（用于测试）"""
    global _config
    _config = None


# 便捷访问 - 直接导出常用配置
config = get_config()
