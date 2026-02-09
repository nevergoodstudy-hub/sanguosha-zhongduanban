"""AI机器人模块 — 薄协调器

AIBot 通过策略模式委托给具体策略实现 (EasyStrategy / NormalStrategy / HardStrategy)，
消除了原来的 `if difficulty == ...` 分支。

公共 API 保持向后兼容：
  - play_phase(player, engine)
  - choose_discard(player, count, engine)
  - should_use_qinglong(player, target, engine)
  - evaluate_game_state(engine)       # 仅 HARD 模式有效
  - infer_identity(target, engine)    # 仅 HARD 模式有效
  - record_behavior(actor, action_type, target)  # 仅 HARD 模式有效
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from .easy_strategy import EasyStrategy
from .hard_strategy import HardStrategy
from .normal_strategy import NormalStrategy
from .strategy import AIStrategy

if TYPE_CHECKING:
    from game.card import Card
    from game.engine import GameEngine
    from game.player import Player


class AIDifficulty(Enum):
    """AI难度枚举"""
    EASY = "easy"       # 简单：随机出牌
    NORMAL = "normal"   # 普通：基础策略
    HARD = "hard"       # 困难：深度策略 + 嘲讽值系统


def _create_strategy(player: Player, difficulty: AIDifficulty) -> AIStrategy:
    """工厂函数：根据难度创建对应策略实例"""
    if difficulty == AIDifficulty.EASY:
        return EasyStrategy()
    elif difficulty == AIDifficulty.HARD:
        return HardStrategy(player)
    else:
        return NormalStrategy()


class AIBot:
    """AI机器人类 — 薄协调器

    通过策略模式委托决策逻辑，自身不包含任何出牌算法。
    """

    def __init__(self, player: Player,
                 difficulty: AIDifficulty = AIDifficulty.NORMAL):
        """初始化AI机器人

        Args:
            player: 关联的玩家
            difficulty: AI难度
        """
        self.player = player
        self.difficulty = difficulty
        self._strategy: AIStrategy = _create_strategy(player, difficulty)

    @property
    def strategy(self) -> AIStrategy:
        """当前策略实例（只读）"""
        return self._strategy

    # ==================== 公共委托接口 ====================

    def play_phase(self, player: Player, engine: GameEngine) -> None:
        """出牌阶段决策 — 委托给策略"""
        self._strategy.play_phase(player, engine)

    def choose_discard(self, player: Player, count: int,
                       engine: GameEngine) -> list[Card]:
        """选择弃牌 — 委托给策略"""
        if not player.hand:
            return []
        return self._strategy.choose_discard(player, count, engine)

    def should_use_qinglong(self, player: Player, target: Player,
                            engine: GameEngine) -> bool:
        """决定是否使用青龙偃月刀继续攻击 — 委托给策略"""
        return self._strategy.should_use_qinglong(player, target, engine)

    # ==================== HARD 模式专属接口 ====================

    def evaluate_game_state(self, engine: GameEngine) -> dict[str, float]:
        """评估当前局势（仅 HARD 模式有效）

        Returns:
            各阵营的综合评分和关键指标
        """
        if isinstance(self._strategy, HardStrategy):
            return self._strategy.evaluate_game_state(engine)
        # 非 HARD 模式返回空状态
        return {
            'lord_advantage': 0.0, 'rebel_advantage': 0.0,
            'spy_advantage': 0.0, 'lord_alive': False,
            'rebel_count': 0, 'loyalist_count': 0, 'spy_count': 0,
            'my_power': 0.0, 'danger_level': 0.0
        }

    def infer_identity(self, target: Player,
                       engine: GameEngine) -> dict[str, float]:
        """基于行为推断目标身份概率（仅 HARD 模式有效）

        Returns:
            各身份的概率字典
        """
        if isinstance(self._strategy, HardStrategy):
            return self._strategy.identity_predictor.infer_identity(target, engine)
        return {'lord': 0.0, 'loyalist': 0.25, 'rebel': 0.50, 'spy': 0.25}

    def record_behavior(self, actor: Player, action_type: str,
                        target: Player | None = None) -> None:
        """记录玩家行为用于身份推断（仅 HARD 模式有效）

        Args:
            actor: 行为发起者
            action_type: 行为类型 ('attack', 'save', 'help', 'harm')
            target: 行为目标
        """
        if isinstance(self._strategy, HardStrategy):
            self._strategy.identity_predictor.record_behavior(
                actor, action_type, target)

    def get_highest_threat_enemy(self, player: Player,
                                 engine: GameEngine) -> Player | None:
        """获取威胁值最高的敌人（仅 HARD 模式有效）"""
        if isinstance(self._strategy, HardStrategy):
            return self._strategy.threat_evaluator.get_highest_threat_enemy(
                player, engine)
        return None

    # ==================== 向后兼容属性 ====================

    @property
    def threat_values(self) -> dict[int, float]:
        """嘲讽值字典（向后兼容）"""
        if isinstance(self._strategy, HardStrategy):
            return self._strategy.threat_evaluator.threat_values
        return {}

    @property
    def identity_guess(self) -> dict[int, str]:
        """身份推测字典（向后兼容）"""
        if isinstance(self._strategy, HardStrategy):
            return self._strategy.identity_predictor.identity_guess
        return {}
