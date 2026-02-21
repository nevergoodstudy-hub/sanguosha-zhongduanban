"""技能 DSL (Domain-Specific Language) 定义模块

M2-T01: 定义技能 DSL 的数据结构和 Schema。
技能逻辑通过 JSON 声明式描述，由 SkillInterpreter 执行。

DSL 结构:
{
    "trigger": "active" | "after_damaged" | "phase_draw" | "phase_end" | ...,
    "phase": "play",           # 主动技触发阶段
    "limit": 1,                # 每回合使用次数限制
    "condition": [...],        # 前置条件列表
    "cost": [...],             # 代价列表
    "target": {...},           # 目标选择规则
    "steps": [...]             # 执行步骤列表
}

步骤 (steps) 支持的原子操作:
    draw       - 摸牌          {"draw": N}
    discard    - 弃牌          {"discard": {"from": "hand", "count": N}}
    heal       - 回复体力       {"heal": {"target": "self"|"target", "amount": N}}
    damage     - 造成伤害       {"damage": {"target": "source"|"target", "amount": N}}
    lose_hp    - 失去体力       {"lose_hp": N}
    transfer   - 转移牌        {"transfer": {"from": "hand", "to": "target.hand", "cards": "selected"}}
    judge      - 判定          {"judge": {"success": {...}, "fail": {...}}}
    get_card   - 获取牌        {"get_card": {"from": "discard_pile"|"source", ...}}
    flip       - 翻面          {"flip": true}
    log        - 日志          {"log": "..."}
    if         - 条件分支       {"if": {...}, "then": [...], "else": [...]}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DslTrigger(str, Enum):
    """DSL 触发类型"""

    ACTIVE = "active"  # 主动使用
    AFTER_DAMAGED = "after_damaged"  # 受到伤害后
    AFTER_DAMAGE_DEALT = "after_damage_dealt"  # 造成伤害后
    PHASE_PREPARE = "phase_prepare"  # 准备阶段开始
    PHASE_DRAW = "phase_draw"  # 摸牌阶段
    PHASE_END = "phase_end"  # 结束阶段
    PHASE_DISCARD = "phase_discard"  # 弃牌阶段
    ON_LOSE_EQUIP = "on_lose_equip"  # 失去装备后
    ON_USE_SHA = "on_use_sha"  # 使用杀后
    PASSIVE = "passive"  # 被动/锁定技（规则层面生效）


# ---------- 条件节点 ----------

VALID_CONDITIONS = {
    "has_hand_cards",  # 有手牌 (min)
    "hp_below_max",  # 体力未满
    "hp_above",  # 体力 >= value
    "target_has_cards",  # 目标有牌
    "no_sha_used",  # 本回合未使用杀
    "distance_le",  # 与目标距离 <= value
    "target_hand_ge_hp",  # 目标手牌 >= 自己体力
    "target_hand_le_range",  # 目标手牌 <= 自己攻击范围
}


# ---------- 代价节点 ----------

VALID_COSTS = {
    "discard",  # 弃牌 {from, count, filter?}
    "lose_hp",  # 失去体力
}


# ---------- 步骤节点 ----------

VALID_STEPS = {
    "draw",  # 摸牌 N
    "discard",  # 弃牌
    "heal",  # 回血
    "damage",  # 造伤害
    "lose_hp",  # 失去体力
    "transfer",  # 转移牌
    "judge",  # 判定
    "get_card",  # 获取牌
    "flip",  # 翻面
    "log",  # 日志
    "if",  # 条件分支
    "skip_phase",  # 跳过阶段
}


@dataclass
class SkillDsl:
    """技能 DSL 数据对象

    从 heroes.json 中 skill 条目的 "dsl" 字段解析而来。
    """

    trigger: str
    steps: list[dict[str, Any]]
    phase: str | None = None
    limit: int = 0
    condition: list[dict[str, Any]] = field(default_factory=list)
    cost: list[dict[str, Any]] = field(default_factory=list)
    target: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillDsl:
        """从字典构建 SkillDsl"""
        return cls(
            trigger=data.get("trigger", "active"),
            steps=data.get("steps", []),
            phase=data.get("phase"),
            limit=data.get("limit", 0),
            condition=data.get("condition", []),
            cost=data.get("cost", []),
            target=data.get("target"),
        )

    def validate(self) -> list[str]:
        """验证 DSL 合法性

        Returns:
            错误信息列表（空 = 合法）
        """
        errors: list[str] = []

        # 触发类型
        valid_triggers = {t.value for t in DslTrigger}
        if self.trigger not in valid_triggers:
            errors.append(f"unknown trigger: {self.trigger}")

        # 步骤
        for i, step in enumerate(self.steps):
            step_keys = set(step.keys()) - {"then", "else"}  # if 分支的子键
            unknown = step_keys - VALID_STEPS
            if unknown:
                errors.append(f"step[{i}]: unknown keys {unknown}")

        return errors
