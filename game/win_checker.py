"""胜利条件检查器模块
负责判定游戏结束条件和确定获胜方

本模块将胜利判定逻辑从 GameEngine 中解耦，
使得胜利条件可以独立测试和扩展。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from i18n import t as _t

if TYPE_CHECKING:
    from .engine import GameEngine
    from .player import Player


class WinResult(Enum):
    """胜利结果"""

    NOT_FINISHED = "not_finished"
    LORD_WIN = "lord_win"  # 主公和忠臣获胜
    REBEL_WIN = "rebel_win"  # 反贼获胜
    SPY_WIN = "spy_win"  # 内奸获胜


@dataclass(slots=True)
class GameOverInfo:
    """游戏结束信息"""

    is_over: bool
    result: WinResult
    winner_identity: str | None
    message: str


class WinConditionChecker:
    """胜利条件检查器

    负责检查各种胜利条件：
    - 主公死亡 → 反贼或内奸获胜
    - 反贼和内奸全灭 → 主公获胜
    """

    def __init__(self, engine: GameEngine):
        """初始化胜利条件检查器

        Args:
            engine: 游戏引擎引用
        """
        self.engine = engine

    def check_game_over(self) -> GameOverInfo:
        """检查游戏是否结束

        Returns:
            GameOverInfo: 游戏结束信息
        """
        from .player import Identity

        players = self.engine.players
        alive_players = [p for p in players if p.is_alive]

        # 找到主公
        lord = self._find_lord(players)

        # 情况1：主公死亡
        if lord and not lord.is_alive:
            return self._check_lord_dead(alive_players)

        # 情况2：检查反贼和内奸是否全灭
        rebel_alive = any(p.identity == Identity.REBEL and p.is_alive for p in players)
        spy_alive = any(p.identity == Identity.SPY and p.is_alive for p in players)

        if not rebel_alive and not spy_alive:
            return GameOverInfo(
                is_over=True,
                result=WinResult.LORD_WIN,
                winner_identity=Identity.LORD.value,
                message=_t("game.over_lord_wins"),
            )

        # 游戏继续
        return GameOverInfo(
            is_over=False, result=WinResult.NOT_FINISHED, winner_identity=None, message=""
        )

    def _find_lord(self, players: list[Player]) -> Player | None:
        """查找主公"""
        from .player import Identity

        for p in players:
            if p.identity == Identity.LORD:
                return p
        return None

    def _check_lord_dead(self, alive_players: list[Player]) -> GameOverInfo:
        """检查主公死亡时的胜利条件

        Args:
            alive_players: 存活玩家列表

        Returns:
            GameOverInfo: 游戏结束信息
        """
        from .player import Identity

        # 检查是否只剩内奸
        spy_count = sum(1 for p in alive_players if p.identity == Identity.SPY)

        if len(alive_players) == spy_count and spy_count > 0:
            # 只剩内奸，内奸获胜
            return GameOverInfo(
                is_over=True,
                result=WinResult.SPY_WIN,
                winner_identity=Identity.SPY.value,
                message=_t("game.over_spy_wins"),
            )
        else:
            # 反贼获胜
            return GameOverInfo(
                is_over=True,
                result=WinResult.REBEL_WIN,
                winner_identity=Identity.REBEL.value,
                message=_t("game.over_rebel_wins"),
            )

    def get_winner_message(self) -> str:
        """获取胜利消息"""
        info = self.check_game_over()
        return info.message if info.is_over else _t("game.in_progress")

    def is_game_over(self) -> bool:
        """检查游戏是否结束"""
        return self.check_game_over().is_over


# ==================== 辅助函数 ====================


def get_identity_win_condition(identity_value: str) -> str:
    """获取身份的胜利条件描述

    Args:
        identity_value: 身份值

    Returns:
        胜利条件描述
    """
    conditions = {
        "lord": _t("win.lord"),
        "loyalist": _t("win.loyalist"),
        "rebel": _t("win.rebel"),
        "spy": _t("win.spy"),
    }
    return conditions.get(identity_value, _t("win.unknown"))


def check_team_win(alive_players: list[Player], team_identities: list[str]) -> bool:
    """检查某一阵营是否获胜

    Args:
        alive_players: 存活玩家列表
        team_identities: 阵营身份列表

    Returns:
        该阵营是否获胜
    """
    # 检查所有存活玩家是否都属于指定阵营
    for p in alive_players:
        if p.identity.value not in team_identities:
            return False
    return True
