"""玩家管理器 (P0-4: 引擎分解 Step 1)

从 GameEngine 提取的玩家管理逻辑:
- 玩家列表管理
- 座位顺序与回合推进
- 距离计算 (含马匹修正)
- 攻击范围查询

GameEngine 通过委托调用此类, 保持向后兼容。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Identity, Player

logger = logging.getLogger(__name__)


class PlayerManager:
    """玩家管理器 — 管理玩家集合、座位顺序和距离计算。"""

    def __init__(self) -> None:
        self.players: list[Player] = []
        self.current_player_index: int = 0
        self.human_player: Player | None = None

    # ==================== 查询 ====================

    @property
    def current_player(self) -> Player:
        """获取当前回合玩家。"""
        return self.players[self.current_player_index]

    def get_player_by_id(self, player_id: int) -> Player | None:
        """根据 ID 获取玩家。"""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def get_alive_players(self) -> list[Player]:
        """获取所有存活玩家。"""
        return [p for p in self.players if p.is_alive]

    def get_other_players(self, player: Player) -> list[Player]:
        """获取除指定玩家外的其他存活玩家。"""
        return [p for p in self.players if p.is_alive and p != player]

    def get_all_other_players(self, player: Player) -> list[Player]:
        """获取除指定玩家外的所有其他玩家（含已死亡），用于 UI 显示。"""
        return [p for p in self.players if p != player]

    def get_next_player(self, player: Player | None = None) -> Player:
        """获取下一个存活玩家（座位顺序）。"""
        if player is None:
            player = self.current_player

        start_index = self.players.index(player)
        for i in range(1, len(self.players) + 1):
            next_index = (start_index + i) % len(self.players)
            if self.players[next_index].is_alive:
                return self.players[next_index]

        return player  # 如果只剩一个玩家

    @property
    def lord_player(self) -> Player | None:
        """获取主公玩家。"""
        from .player import Identity

        for p in self.players:
            if p.identity == Identity.LORD:
                return p
        return None

    @property
    def lord_player_index(self) -> int:
        """获取主公玩家的座位索引。"""
        from .player import Identity

        for i, p in enumerate(self.players):
            if p.identity == Identity.LORD:
                return i
        return 0

    # ==================== 距离与范围 ====================

    def calculate_distance(self, from_player: Player, to_player: Player) -> int:
        """计算两个玩家之间的距离（含马匹修正）。"""
        if from_player == to_player:
            return 0

        alive_players = self.get_alive_players()
        if len(alive_players) <= 1:
            return 0

        try:
            from_index = alive_players.index(from_player)
            to_index = alive_players.index(to_player)
        except ValueError:
            return 999  # 其中一个玩家已死亡

        n = len(alive_players)
        clockwise = (to_index - from_index) % n
        counter_clockwise = (from_index - to_index) % n
        base_distance = min(clockwise, counter_clockwise)

        # 马匹修正
        distance_modifier = from_player.equipment.distance_to_others
        distance_modifier += to_player.equipment.distance_from_others

        return max(1, base_distance + distance_modifier)

    def is_in_attack_range(self, attacker: Player, target: Player) -> bool:
        """检查目标是否在攻击范围内。"""
        distance = self.calculate_distance(attacker, target)
        attack_range = attacker.equipment.attack_range
        return distance <= attack_range

    def get_targets_in_range(self, player: Player) -> list[Player]:
        """获取攻击范围内的所有目标。"""
        return [
            other
            for other in self.get_other_players(player)
            if self.is_in_attack_range(player, other)
        ]

    # ==================== 回合推进 ====================

    def advance_turn(self) -> None:
        """推进到下一个存活玩家的回合。"""
        for i in range(1, len(self.players) + 1):
            next_index = (self.current_player_index + i) % len(self.players)
            if self.players[next_index].is_alive:
                self.current_player_index = next_index
                break
