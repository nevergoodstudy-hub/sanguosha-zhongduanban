"""伤害系统数据模型

提供伤害相关的数据结构 (DamageEvent / DamageResult) 和工具函数。

实际伤害处理逻辑位于 GameEngine.deal_damage (game/engine.py)。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DamageEvent:
    """伤害事件数据"""

    source: Player | None  # 伤害来源，None 表示系统伤害
    target: Player  # 伤害目标
    damage: int  # 伤害值
    damage_type: str = "normal"  # 伤害类型 ("normal", "fire", "thunder")
    is_chain: bool = False  # 是否为连环传导伤害


@dataclass(slots=True)
class DamageResult:
    """伤害结果"""

    actual_damage: int  # 实际造成的伤害
    target_died: bool  # 目标是否死亡
    chain_triggered: bool  # 是否触发了连环
    chain_targets: list[Player]  # 连环传导目标


# ==================== 辅助函数 ====================


def calculate_damage_with_modifiers(base_damage: int, modifiers: list[int]) -> int:
    """计算带修正的伤害

    Args:
        base_damage: 基础伤害
        modifiers: 伤害修正值列表

    Returns:
        最终伤害值（最小为0）
    """
    total = base_damage + sum(modifiers)
    return max(0, total)
