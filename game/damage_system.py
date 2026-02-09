"""伤害系统模块
负责伤害计算、濒死处理、死亡处理和铁索连环传导

本模块将伤害相关逻辑从 GameEngine 中解耦，
使得伤害系统可以独立测试和扩展。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from i18n import t as _t

from .card import CardName, DamageType
from .constants import SkillId
from .events import EventType
from .hero import Kingdom

if TYPE_CHECKING:
    from .engine import GameEngine
    from .player import Player

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DamageEvent:
    """伤害事件数据"""
    source: Player | None  # 伤害来源，None 表示系统伤害
    target: Player           # 伤害目标
    damage: int                # 伤害值
    damage_type: DamageType    # 伤害类型
    is_chain: bool = False     # 是否为连环传导伤害


@dataclass(slots=True)
class DamageResult:
    """伤害结果"""
    actual_damage: int          # 实际造成的伤害
    target_died: bool           # 目标是否死亡
    chain_triggered: bool       # 是否触发了连环
    chain_targets: list[Player]  # 连环传导目标


class DamageSystem:
    """伤害系统

    负责处理所有伤害相关的逻辑：
    - 伤害计算（含装备效果）
    - 濒死救援
    - 死亡处理
    - 铁索连环传导
    """

    def __init__(self, engine: GameEngine):
        """初始化伤害系统

        Args:
            engine: 游戏引擎引用
        """
        self.engine = engine

    def deal_damage(
        self,
        source: Player | None,
        target: Player,
        damage: int,
        damage_type: str = "normal",
        is_chain: bool = False
    ) -> DamageResult:
        """造成伤害

        Args:
            source: 伤害来源，None 表示系统伤害
            target: 目标玩家
            damage: 伤害值
            damage_type: 伤害类型 ("normal", "fire", "thunder")
            is_chain: 是否为连环传导伤害

        Returns:
            DamageResult: 伤害结果
        """
        # 输入验证
        if damage <= 0:
            logger.warning(f"deal_damage called with invalid damage={damage}")
            return DamageResult(0, False, False, [])

        if not target or not target.is_alive:
            logger.warning("deal_damage called with invalid target")
            return DamageResult(0, False, False, [])

        source_name = source.name if source else _t("game.damage_system")
        old_hp = target.hp

        # 计算实际伤害（应用装备效果）
        actual_damage = self._calculate_actual_damage(target, damage, damage_type)

        # 应用伤害
        target.take_damage(actual_damage, source)

        # 记录伤害日志
        self._log_damage(source_name, target, actual_damage, damage_type, old_hp)

        # M1-T04: 发布 DAMAGE_INFLICTED 语义事件
        self.engine.event_bus.emit(
            EventType.DAMAGE_INFLICTED,
            source=source,
            target=target,
            damage=actual_damage,
            damage_type=damage_type,
        )

        # 处理铁索连环传导
        chain_targets = []
        chain_triggered = False
        if damage_type in ["fire", "thunder"] and target.is_chained and not is_chain:
            chain_triggered = True
            chain_targets = self._handle_chain_damage(
                source, target, actual_damage, damage_type
            )

        # 检查濒死
        target_died = False
        if target.is_dying:
            saved = self._handle_dying(target)
            if not saved:
                self._handle_death(target)
                target_died = True

        return DamageResult(
            actual_damage=actual_damage,
            target_died=target_died,
            chain_triggered=chain_triggered,
            chain_targets=chain_targets
        )

    def _calculate_actual_damage(
        self,
        target: Player,
        base_damage: int,
        damage_type: str
    ) -> int:
        """计算实际伤害（应用装备效果）

        Args:
            target: 目标玩家
            base_damage: 基础伤害
            damage_type: 伤害类型

        Returns:
            实际伤害值
        """
        actual_damage = base_damage

        # 藤甲效果：火焰伤害+1
        if damage_type == "fire" and target.equipment.armor:
            if target.equipment.armor.name == CardName.TENGJIA:
                actual_damage += 1
                self.engine.log_event(
                    "equipment",
                    _t("damage.tengjia_fire", name=target.name)
                )

        # 白银狮子效果：受到大于1点伤害时，防止多余的伤害
        if target.equipment.armor and target.equipment.armor.name == CardName.BAIYINSHIZI:
            if actual_damage > 1:
                original_damage = actual_damage
                actual_damage = 1
                self.engine.log_event(
                    "equipment",
                    _t("damage.baiyinshizi_prevent", name=target.name, prevented=original_damage - 1)
                )

        return actual_damage

    def _log_damage(
        self,
        source_name: str,
        target: Player,
        damage: int,
        damage_type: str,
        old_hp: int
    ) -> None:
        """记录伤害日志"""
        damage_type_display = {
            "normal": "",
            "fire": _t("game.damage_fire"),
            "thunder": _t("game.damage_thunder")
        }.get(damage_type, "")

        self.engine.log_event(
            "damage",
            _t("game.damage", target=target.name, source=source_name,
               damage=damage, type=damage_type_display,
               old_hp=old_hp, new_hp=target.hp, max_hp=target.max_hp)
        )

    def _handle_chain_damage(
        self,
        source: Player | None,
        original_target: Player,
        damage: int,
        damage_type: str
    ) -> list[Player]:
        """处理铁索连环传导伤害

        Args:
            source: 伤害来源
            original_target: 原始目标
            damage: 伤害值
            damage_type: 伤害类型

        Returns:
            受到传导伤害的玩家列表
        """
        # 解除原始目标的连环状态
        original_target.break_chain()
        self.engine.log_event(
            "chain",
            _t("game.chain_trigger", player=original_target.name)
        )

        chain_targets = []

        # 按座位顺序传导给其他被连环的角色
        for player in self.engine.players:
            if player.is_alive and player != original_target and player.is_chained:
                self.engine.log_event("chain", _t("game.chain_propagate", player=player.name))
                player.break_chain()  # 解除连环状态
                chain_targets.append(player)

                # 递归造成伤害（标记为连环传导）
                self.deal_damage(source, player, damage, damage_type, is_chain=True)

        return chain_targets

    def _handle_dying(self, player: Player) -> bool:
        """处理濒死状态

        Args:
            player: 濒死的玩家

        Returns:
            是否被救活
        """
        from .player import Identity

        hero_name = player.hero.name if player.hero else '???'
        self.engine.log_event(
            "dying",
            _t("game.dying", player=player.name, hero=hero_name, hp=player.hp)
        )

        # 从当前玩家开始按座位顺序请求救援
        start_index = self.engine.players.index(player)

        for i in range(len(self.engine.players)):
            current_index = (start_index + i) % len(self.engine.players)
            savior = self.engine.players[current_index]

            if not savior.is_alive:
                continue

            while player.hp <= 0:
                tao_cards = savior.get_cards_by_name(CardName.TAO)
                if not tao_cards:
                    break

                if savior.is_ai:
                    should_save = self._ai_should_save(savior, player)
                    if should_save:
                        card = tao_cards[0]
                        savior.remove_card(card)
                        player.heal(1)
                        self.engine.deck.discard([card])
                        self.engine.log_event(
                            "save",
                            _t("game.save", savior=savior.name, player=player.name)
                        )

                        # 救援技能（孙权）
                        if (player.has_skill(SkillId.JIUYUAN) and
                            player.identity == Identity.LORD and
                            savior.hero and
                            savior.hero.kingdom == Kingdom.WU):
                            player.heal(1)
                            self.engine.log_event(
                                "skill",
                                _t("game.jiuyuan", player=player.name)
                            )
                    else:
                        break
                else:
                    # 人类玩家选择 — 通过 request_handler 路由
                    result = self.engine.request_handler.request_tao(savior, player)
                    if result:
                        savior.remove_card(result)
                        player.heal(1)
                        self.engine.deck.discard([result])
                        self.engine.log_event(
                            "save",
                            _t("game.save", savior=savior.name, player=player.name)
                        )
                    else:
                        break

            if player.hp > 0:
                return True

        return player.hp > 0

    def _ai_should_save(self, savior: Player, dying: Player) -> bool:
        """AI决定是否救援"""
        from .player import Identity

        # 同阵营救援
        if savior.identity == dying.identity:
            return True
        if savior.identity == Identity.LOYALIST and dying.identity == Identity.LORD:
            return True
        if dying.identity == Identity.LORD:
            # 内奸在最后阶段可能不救主公
            if savior.identity == Identity.SPY:
                alive_count = len(self.engine.get_alive_players())
                if alive_count <= 2:
                    return False
            return True
        return False

    def _handle_death(self, player: Player) -> None:
        """处理死亡"""
        player.die()
        self.engine.log_event(
            "death",
            _t("game.death", player=player.name, identity=player.identity.chinese_name)
        )

        # 弃置所有牌
        all_cards = player.get_all_cards()
        player.hand.clear()
        player.equipment = type(player.equipment)()
        self.engine.deck.discard(all_cards)

        # 处理奖惩
        self._handle_rewards_and_penalties(player)

        # 检查游戏是否结束
        self.engine.check_game_over()

    def _handle_rewards_and_penalties(self, dead_player: Player) -> None:
        """处理击杀奖惩"""
        from .player import Identity

        if not self.engine.current_player.is_alive:
            return

        killer = self.engine.current_player

        # 杀死反贼，摸三张牌
        if dead_player.identity == Identity.REBEL:
            cards = self.engine.deck.draw(3)
            killer.draw_cards(cards)
            self.engine.log_event(
                "reward",
                _t("game.reward_rebel", killer=killer.name)
            )

        # 主公杀死忠臣，弃置所有牌
        if (killer.identity == Identity.LORD and
            dead_player.identity == Identity.LOYALIST):
            discard_cards = killer.get_all_cards()
            killer.hand.clear()
            killer.equipment = type(killer.equipment)()
            self.engine.deck.discard(discard_cards)
            self.engine.log_event(
                "penalty",
                _t("game.penalty_loyalist", killer=killer.name)
            )


# ==================== 辅助函数 ====================


def calculate_damage_with_modifiers(
    base_damage: int,
    modifiers: list[int]
) -> int:
    """计算带修正的伤害

    Args:
        base_damage: 基础伤害
        modifiers: 伤害修正值列表

    Returns:
        最终伤害值（最小为0）
    """
    total = base_damage + sum(modifiers)
    return max(0, total)
