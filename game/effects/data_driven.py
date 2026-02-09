"""数据驱动卡牌效果（M2-T04）

通过 data/card_effects.json 中的声明式配置执行简单卡牌效果，
与手写 Effect 子类共存（手写优先、数据驱动补充）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from i18n import t as _t

from .base import CardEffect

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DataDrivenCardEffect(CardEffect):
    """从 JSON 配置驱动的卡牌效果。

    支持简单卡牌（桃、无中生有、桃园结义等），
    复杂卡牌（杀、决斗、南蛮等）仍使用手写子类。
    """

    def __init__(self, card_name: str, config: dict[str, Any]):
        self._card_name = card_name
        self._config = config
        self._display_name = config.get("display_name", card_name)

    @property
    def needs_target(self) -> bool:
        return self._config.get("needs_target", False)

    def can_use(self, engine, player, card, targets):
        cond = self._config.get("condition")
        if cond:
            if not self._check_condition(cond, engine, player, targets):
                msg = self._config.get("condition_fail_msg", _t("effect.condition_fail"))
                return False, msg
        return True, ""

    def resolve(self, engine, player, card, targets):
        # 条件检查
        cond = self._config.get("condition")
        if cond:
            if not self._check_condition(cond, engine, player, targets):
                fail_action = self._config.get("condition_fail_action", "")
                if fail_action == "return_card":
                    engine.log_event(
                        "error",
                        self._config.get("condition_fail_msg", _t("effect.condition_fail")),
                    )
                    player.draw_cards([card])
                return False

        scope = self._config.get("scope")
        use_wuxie = self._config.get("wuxie", False)

        # 日志：使用卡牌
        engine.log_event(
            "use_card",
            _t("effect.use_card", name=player.name, card=self._display_name),
            source=player, card=card,
        )

        if scope == "all_alive_from_player":
            # 桃园结义模式：遍历所有存活角色
            self._resolve_all_alive(engine, player, card)
        else:
            # 单体/自身效果
            if use_wuxie:
                wuxie_target_str = self._config.get("wuxie_target", "self")
                wuxie_target = player if wuxie_target_str == "self" else (
                    targets[0] if targets else player
                )
                if engine._request_wuxie(card, player, wuxie_target):
                    engine.log_event(
                        "effect",
                        _t("effect.nullified", card=self._display_name),
                    )
                    engine.deck.discard([card])
                    return True

            self._execute_steps(engine, player, player)

        if self._config.get("discard_after", True):
            engine.deck.discard([card])

        return True

    # ==================== 内部 ====================

    def _resolve_all_alive(self, engine, player, card):
        """桃园结义类：遍历所有存活角色"""
        wuxie_per_target = self._config.get("wuxie_per_target", False)

        start_index = engine.players.index(player)
        for i in range(len(engine.players)):
            current_index = (start_index + i) % len(engine.players)
            p = engine.players[current_index]
            if not p.is_alive:
                continue

            if wuxie_per_target:
                if engine._request_wuxie(card, player, p):
                    engine.log_event(
                        "effect",
                        _t("effect.nullified_for", card=self._display_name, name=p.name),
                    )
                    continue

            self._execute_steps(engine, player, p)

    def _execute_steps(self, engine, source_player, current_target):
        """执行步骤列表"""
        for step in self._config.get("steps", []):
            self._exec_step(step, engine, source_player, current_target)

    def _exec_step(self, step, engine, player, target):
        """执行单个步骤"""
        # draw
        if "draw" in step:
            info = step["draw"]
            if isinstance(info, int):
                count = info
                recipient = player
            else:
                count = info.get("count", 1)
                target_str = info.get("target", "self")
                recipient = self._resolve_player(target_str, player, target)

            cards = engine.deck.draw(count)
            if cards:
                recipient.draw_cards(cards)

        # heal
        elif "heal" in step:
            info = step["heal"]
            if isinstance(info, int):
                player.heal(info)
            else:
                amount = info.get("amount", 1)
                target_str = info.get("target", "self")
                recipient = self._resolve_player(target_str, player, target)
                if_wounded = info.get("if_wounded", False)

                if if_wounded and recipient.hp >= recipient.max_hp:
                    return  # 不需要回血
                healed = recipient.heal(amount)

        # log
        elif "log" in step:
            msg = step["log"]
            msg = msg.replace("{player}", player.name)
            if target:
                msg = msg.replace("{target}", target.name)
            engine.log_event("effect", msg)

        # log_if_healed — 仅当目标体力有变化时记录
        elif "log_if_healed" in step:
            if target and target.hp < target.max_hp:
                msg = step["log_if_healed"]
                msg = msg.replace("{player}", player.name)
                msg = msg.replace("{target}", target.name)
                engine.log_event("effect", msg)

    def _check_condition(self, cond, engine, player, targets):
        """检查条件"""
        check = cond.get("check", "")
        if check == "hp_below_max":
            return player.hp < player.max_hp
        if check == "has_target_cards":
            return targets and targets[0].has_any_card()
        return True

    def _resolve_player(self, ref, player, target):
        """解析玩家引用"""
        if ref == "self":
            return player
        if ref == "target":
            return target or player
        if ref == "current":
            return target or player
        return player


def load_card_effects_config() -> dict[str, dict[str, Any]]:
    """从 data/card_effects.json 加载卡牌效果配置

    Returns:
        card_name -> config 映射
    """
    config_path = Path(__file__).parent.parent.parent / "data" / "card_effects.json"
    if not config_path.exists():
        logger.info("No card_effects.json found")
        return {}

    try:
        with open(config_path, encoding="utf-8") as f:
            raw = json.load(f)
        # 过滤注释键
        return {k: v for k, v in raw.items() if not k.startswith("_")}
    except Exception as e:
        logger.error("Failed to load card_effects.json: %s", e)
        return {}
