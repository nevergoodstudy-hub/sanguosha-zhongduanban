"""技能系统模块
负责所有武将技能的具体实现
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .hero import SkillType
from .skill_dsl import SkillDsl
from .skill_interpreter import SkillInterpreter
from .skills import get_all_skill_handlers

if TYPE_CHECKING:
    from .card import Card
    from .engine import GameEngine
    from .events import EventBus, GameEvent
    from .player import Player

logger = logging.getLogger(__name__)


class SkillSystem:
    """技能系统类
    负责管理和执行所有武将技能
    """

    def __init__(self, game_engine: GameEngine):
        """初始化技能系统

        Args:
            game_engine: 游戏引擎引用
        """
        self.engine = game_engine

        # M2-T02: DSL 解释器
        self._interpreter = SkillInterpreter(game_engine)
        self._dsl_registry: dict[str, SkillDsl] = {}
        self._load_dsl_definitions()

        # 技能处理器映射（从 skills 子包按势力加载）
        self._skill_handlers: dict[str, Callable[..., bool]] = get_all_skill_handlers()

    def __getattr__(self, name: str):
        """向后兼容：将 _handle_xxx 属性访问代理到 _skill_handlers['xxx']。"""
        if name.startswith("_handle_"):
            skill_id = name[len("_handle_") :]
            # 必须通过 __dict__ 访问避免无限递归
            handlers = self.__dict__.get("_skill_handlers", {})
            if skill_id in handlers:
                return handlers[skill_id]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def _load_dsl_definitions(self) -> None:
        """M2-T03: 从 data/skill_dsl.json 加载 DSL 定义"""
        dsl_path = Path(__file__).parent.parent / "data" / "skill_dsl.json"
        if not dsl_path.exists():
            logger.info("No skill_dsl.json found, DSL disabled")
            return
        try:
            with open(dsl_path, encoding="utf-8") as f:
                raw = json.load(f)
            for skill_id, dsl_data in raw.items():
                if skill_id.startswith("_"):
                    continue  # skip comments
                dsl = SkillDsl.from_dict(dsl_data)
                errors = dsl.validate()
                if errors:
                    logger.warning("DSL validation errors for %s: %s", skill_id, errors)
                else:
                    self._dsl_registry[skill_id] = dsl
            logger.info("Loaded %d skill DSL definitions", len(self._dsl_registry))
        except Exception as e:
            logger.error("Failed to load skill DSL: %s", e)

    def get_dsl(self, skill_id: str) -> SkillDsl | None:
        """获取技能的 DSL 定义（无则 None）"""
        return self._dsl_registry.get(skill_id)

    def can_use_skill(self, skill_id: str, player: Player) -> bool:
        """检查玩家是否可以使用指定技能

        Args:
            skill_id: 技能ID
            player: 玩家

        Returns:
            是否可以使用
        """
        skill = player.get_skill(skill_id)
        if not skill:
            return False

        # 检查使用次数限制
        if skill.limit_per_turn > 0:
            used = player.skill_used.get(skill_id, 0)
            if used >= skill.limit_per_turn:
                return False

        # 特定技能检查
        if skill_id == "rende" or skill_id == "zhiheng":
            return len(player.hand) > 0
        elif skill_id == "fanjian":
            return len(player.hand) > 0 and len(self.engine.get_other_players(player)) > 0

        return True

    def trigger_skill(
        self, skill_id: str, player: Player, game_engine: GameEngine, **kwargs
    ) -> bool:
        """触发技能

        优先使用 DSL 解释器执行，若 DSL 未定义或执行失败，
        回退到 Python handler。

        Args:
            skill_id: 技能ID
            player: 使用技能的玩家
            game_engine: 游戏引擎
            **kwargs: 额外参数

        Returns:
            是否成功触发
        """
        # DSL-first: 尝试通过解释器执行
        dsl = self._dsl_registry.get(skill_id)
        if dsl is not None:
            try:
                # 解析技能中文名（避免 DSL 日志显示拼音）
                skill_chinese_name = self._resolve_skill_name(skill_id, player)
                result = self._interpreter.execute(
                    dsl,
                    player,
                    skill_chinese_name,
                    targets=kwargs.get("targets"),
                    cards=kwargs.get("cards"),
                    source=kwargs.get("source"),
                    damage_card=kwargs.get("damage_card"),
                )
                if result:
                    return True
                # DSL 返回 False（条件不满足等），回退到 Python
            except Exception as e:
                logger.warning("DSL exec failed for %s, fallback: %s", skill_id, e)

        # Python fallback
        if skill_id not in self._skill_handlers:
            return False

        handler = self._skill_handlers[skill_id]
        return handler(player, game_engine, **kwargs)

    def use_skill(
        self,
        skill_id: str,
        player: Player,
        targets: list[Player] | None = None,
        cards: list[Card] | None = None,
    ) -> bool:
        """使用主动技能

        Args:
            skill_id: 技能ID
            player: 使用技能的玩家
            targets: 目标列表
            cards: 选择的卡牌列表

        Returns:
            是否成功使用
        """
        if not self.can_use_skill(skill_id, player):
            return False

        result = self.trigger_skill(skill_id, player, self.engine, targets=targets, cards=cards)

        if result:
            # 记录使用次数
            player.skill_used[skill_id] = player.skill_used.get(skill_id, 0) + 1

            skill = player.get_skill(skill_id)
            if skill:
                skill.use()

        return result

    def get_usable_skills(self, player: Player) -> list[str]:
        """获取玩家当前可以使用的技能列表

        Args:
            player: 玩家

        Returns:
            可用技能ID列表
        """
        usable = []
        if player.hero:
            for skill in player.hero.skills:
                if skill.skill_type == SkillType.ACTIVE and self.can_use_skill(skill.id, player):
                    usable.append(skill.id)
        return usable

    # ==================== M1-T04: EventBus 被动技能注册 ====================

    def register_event_handlers(self, event_bus: EventBus) -> None:
        """在 EventBus 上注册被动技能的事件处理器。

        被动技能（如奸雄、反馈、刚烈）通过监听语义事件自动触发，
        而非由引擎在代码中内联调用。
        """
        from .events import EventType

        event_bus.subscribe(EventType.DAMAGE_INFLICTED, self._on_damage_inflicted)

    def _on_damage_inflicted(self, event: GameEvent) -> None:
        """EventBus handler: 伤害结算后触发被动技能

        监听 DAMAGE_INFLICTED 事件，自动触发相关被动技能：
        - 奸雄：受到伤害后获得造成伤害的牌
        - 反馈：受到伤害后获取伤害来源一张牌
        - 刚烈：受到伤害后判定反击

        使用 DSL-first + Python fallback 策略。
        """
        from .constants import SkillId

        target = event.data.get("target")
        source = event.data.get("source")
        damage_card = event.data.get("card")

        if not target or not target.is_alive:
            return

        # 奸雄：受到伤害后可获得造成伤害的牌
        if target.has_skill(SkillId.JIANXIONG) and source:
            self._trigger_with_dsl_fallback(
                SkillId.JIANXIONG,
                target,
                damage_card=damage_card,
                _py_handler=self._skill_handlers["jianxiong"],
                _py_kwargs={"damage_card": damage_card},
            )

        # 反馈：受到伤害后获取来源一张牌
        if target.has_skill(SkillId.FANKUI) and source and source != target:
            self._trigger_with_dsl_fallback(
                SkillId.FANKUI,
                target,
                source=source,
                _py_handler=self._skill_handlers["fankui"],
                _py_kwargs={"source": source},
            )

        # 刚烈：受到伤害后判定反击
        if target.has_skill(SkillId.GANGLIE) and source and source != target:
            self._trigger_with_dsl_fallback(
                SkillId.GANGLIE,
                target,
                source=source,
                _py_handler=self._skill_handlers["ganglie"],
                _py_kwargs={"source": source},
            )

    def _trigger_with_dsl_fallback(
        self,
        skill_id: str,
        player: Player,
        *,
        _py_handler: Callable[..., bool],
        _py_kwargs: dict[str, Any] | None = None,
        **dsl_kwargs,
    ) -> bool:
        """内部辅助：DSL-first + Python fallback 触发被动技能。

        用于 _on_damage_inflicted 等 EventBus 处理器，
        它们直接调用具体 handler 而非经过 trigger_skill。
        """
        dsl = self._dsl_registry.get(skill_id)
        if dsl is not None:
            try:
                skill_chinese_name = self._resolve_skill_name(skill_id, player)
                result = self._interpreter.execute(dsl, player, skill_chinese_name, **dsl_kwargs)
                if result:
                    return True
            except Exception as e:
                logger.warning("DSL exec failed for %s, fallback: %s", skill_id, e)

        py_kw = _py_kwargs or {}
        return _py_handler(player, self.engine, **py_kw)

    def _resolve_skill_name(self, skill_id: str, player: Player) -> str:
        """将 skill_id（拼音）解析为中文技能名，用于日志显示"""
        # 优先从玩家武将的技能对象获取
        skill_obj = player.get_skill(skill_id)
        if skill_obj and skill_obj.name and skill_obj.name != skill_id:
            return skill_obj.name
        # 回退到 SKILL_DESCRIPTIONS 映射表
        desc = SKILL_DESCRIPTIONS.get(skill_id)
        if desc:
            return desc["name"]
        return skill_id


# 技能效果描述
SKILL_DESCRIPTIONS = {
    "rende": {
        "name": "仁德",
        "description": "出牌阶段，你可以将任意数量的手牌交给其他角色。每回合你以此法给出第二张牌时，回复1点体力。",
    },
    "jijiang": {
        "name": "激将",
        "description": "主公技。当你需要使用或打出【杀】时，你可以令其他蜀势力角色选择是否打出一张【杀】。",
    },
    "jianxiong": {"name": "奸雄", "description": "当你受到伤害后，你可以获得造成伤害的牌。"},
    "hujia": {
        "name": "护驾",
        "description": "主公技。当你需要使用或打出【闪】时，你可以令其他魏势力角色选择是否打出一张【闪】。",
    },
    "zhiheng": {
        "name": "制衡",
        "description": "出牌阶段限一次，你可以弃置任意数量的牌，然后摸等量的牌。",
    },
    "jiuyuan": {
        "name": "救援",
        "description": "主公技。锁定技。其他吴势力角色对你使用【桃】时，你额外回复1点体力。",
    },
    "wusheng": {"name": "武圣", "description": "你可以将一张红色牌当【杀】使用或打出。"},
    "paoxiao": {"name": "咆哮", "description": "锁定技。出牌阶段，你使用【杀】无次数限制。"},
    "guanxing": {
        "name": "观星",
        "description": "准备阶段，你可以观看牌堆顶的X张牌（X为存活角色数且至多为5），然后将这些牌以任意顺序放置于牌堆顶或牌堆底。",
    },
    "kongcheng": {
        "name": "空城",
        "description": "锁定技。若你没有手牌，你不是【杀】和【决斗】的合法目标。",
    },
    "yingzi": {"name": "英姿", "description": "摸牌阶段，你可以多摸一张牌。"},
    "fanjian": {
        "name": "反间",
        "description": "出牌阶段限一次，你可以选择一名其他角色并展示一张手牌，令其选择一种花色后获得此牌。若此牌花色与其所选花色不同，你对其造成1点伤害。",
    },
    "wushuang": {
        "name": "无双",
        "description": "锁定技。你使用【杀】指定目标后，目标角色需使用两张【闪】才能抵消此【杀】；你使用【决斗】指定目标后，或成为【决斗】的目标后，对方每次需打出两张【杀】。",
    },
}
