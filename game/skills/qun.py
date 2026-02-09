"""群雄武将技能处理器

包含以下武将技能：
  吕布 - 无双(wushuang)
  华佗 - 青囊(qingnang)、急救(jijiu)
  貂蝉 - 离间(lijian)、闭月(biyue)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from .registry import skill_handler

if TYPE_CHECKING:
    from ..card import Card
    from ..engine import GameEngine
    from ..player import Player


# ==================== 吕布 ====================

@skill_handler("wushuang")
def handle_wushuang(player: Player, engine: GameEngine, **kwargs) -> bool:
    """无双：锁定技，使用杀需要两张闪，决斗需要两张杀（此技能在杀/决斗结算时自动生效）"""
    return True


# ==================== 华佗 ====================

@skill_handler("qingnang")
def handle_qingnang(player: Player, engine: GameEngine,
                    target: Player = None, cards: list = None, **kwargs) -> bool:
    """青囊：出牌阶段限一次，弃置一张手牌，令一名角色回复1点体力"""
    if not cards or not target:
        return False

    card = cards[0]
    if card not in player.hand:
        return False

    player.remove_card(card)
    engine.deck.discard([card])

    healed = target.heal(1)
    engine.log_event("skill", _t("skill_msg.qingnang", name=player.name, target=target.name, healed=healed))
    return True


@skill_handler("jijiu")
def handle_jijiu(player: Player, engine: GameEngine,
                 card: Card = None, **kwargs) -> bool:
    """急救：回合外，可以将一张红色牌当【桃】使用（转化技能，在濒死求桃时检查）"""
    return True


# ==================== 貂蝉 ====================

@skill_handler("lijian")
def handle_lijian(player: Player, engine: GameEngine,
                  targets: list[Player] = None, card: Card = None, **kwargs) -> bool:
    """离间：出牌阶段限一次，弃一牌令两名男性角色决斗"""
    if not card or not targets or len(targets) < 2:
        return False

    player.remove_card(card)
    engine.deck.discard([card])

    target1, target2 = targets[0], targets[1]
    engine.log_event("skill", _t("skill_msg.lijian", name=player.name, target1=target1.name, target2=target2.name))

    engine._use_juedou_forced(target1, target2)
    return True


@skill_handler("biyue")
def handle_biyue(player: Player, engine: GameEngine, **kwargs) -> bool:
    """闭月：结束阶段摸一张牌"""
    cards = engine.deck.draw(1)
    player.draw_cards(cards)
    engine.log_event("skill", _t("skill_msg.biyue", name=player.name))
    return True


# ==================== 导出 ====================

QUN_HANDLERS: dict[str, Callable[..., bool]] = {
    "wushuang": handle_wushuang,
    "qingnang": handle_qingnang,
    "jijiu": handle_jijiu,
    "lijian": handle_lijian,
    "biyue": handle_biyue,
}
