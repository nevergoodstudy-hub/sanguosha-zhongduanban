"""普通 AI 策略 — 基础策略出牌.

实现 AIStrategy 协议，用于 NORMAL 难度。
包含目标选择、技能使用、弃牌优先级等基础决策逻辑。
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from game.card import CardName, CardSubtype, CardSuit, CardType
from game.constants import SkillId

from .strategy import (
    count_useless_cards,
    execute_play_card_action,
    execute_use_skill_action,
    get_friends,
    is_enemy,
    pick_least_valuable,
    smart_discard,
)

if TYPE_CHECKING:
    from game.card import Card
    from game.engine import GameEngine
    from game.player import Player


class NormalStrategy:
    """普通模式策略：基础优先级出牌."""

    def play_phase(self, player: Player, engine: GameEngine) -> None:
        """普通模式：基础策略."""
        # 优先级：装备 > 无中生有 > 杀 > 其他锦囊 > 技能

        played = True
        while played:
            played = False
            # 1. 先响应厌粱，换取酒状态再继续进攻
            if self._try_use_yanliang(player, engine):
                played = True
                continue

            # 2. 使用装备
            # 1. 使用装备
            for card in list(player.hand):
                if card.card_type == CardType.EQUIPMENT and execute_play_card_action(engine, player, card):
                    played = True
                    break

            if played:
                continue

            # 3. 使用无中生有
            wuzhong = player.get_cards_by_name(CardName.WUZHONG)
            if wuzhong and engine.use_card(player, wuzhong[0]):
                played = True
                continue
            # 4. 使用桃回复体力
            # 3. 使用桃回复体力
            if player.hp < player.max_hp - 1:  # 保留一些桃用于濒死
                tao = player.get_cards_by_name(CardName.TAO)
                if tao and player.hp <= 2 and engine.use_card(player, tao[0]):
                    played = True
                    continue
            # 5. 使用杀
            # 4. 使用杀
            if player.can_use_sha():
                sha = player.get_cards_by_name(CardName.SHA)
                # 武圣可以用红牌当杀
                if player.has_skill(SkillId.WUSHENG) and not sha:
                    sha = player.get_red_cards()

                if sha:
                    targets = self._get_attack_targets(player, engine)
                    if targets:
                        target = self.choose_best_target(player, targets, engine)
                        if engine.use_card(player, sha[0], [target]):
                            played = True
                            continue

            # 6. 使用控制锦囊
            for card in list(player.hand):
                if card.name == CardName.GUOHE:
                    target = self._choose_dismount_target(player, engine)
                    if target and engine.use_card(player, card, [target]):
                        played = True
                        break

                elif card.name == CardName.SHUNSHOU:
                    target = self._choose_steal_target(player, engine)
                    if target and engine.use_card(player, card, [target]):
                        played = True
                        break

                elif card.name == CardName.JUEDOU:
                    target = self._choose_duel_target(player, engine)
                    if target and engine.use_card(player, card, [target]):
                        played = True
                        break

                elif card.name == CardName.JIEDAO:
                    targets = self._choose_jiedao_targets(player, engine)
                    if targets and engine.use_card(player, card, targets):
                        played = True
                        break

                elif card.name == CardName.LEBUSISHU:
                    target = self._choose_lebusishu_target(player, engine)
                    if target and engine.use_card(player, card, [target]):
                        played = True
                        break

                elif card.name == CardName.BINGLIANG:
                    target = self._choose_bingliang_target(player, engine)
                    if target and engine.use_card(player, card, [target]):
                        played = True
                        break

                elif card.name == CardName.HUOGONG:
                    target = self._choose_huogong_target(player, engine)
                    if target and engine.use_card(player, card, [target]):
                        played = True
                        break

                elif card.name == CardName.TIESUO:
                    targets = self._choose_tiesuo_targets(player, engine)
                    if targets is not None and engine.use_card(player, card, targets):
                        played = True
                        break

            if played:
                continue

            # 7. 使用AOE锦囊（如果大部分目标是敌人）
            for card in list(player.hand):
                if (
                    card.name in [CardName.NANMAN, CardName.WANJIAN]
                    and self._should_use_aoe(player, engine)
                    and engine.use_card(player, card)
                ):
                    played = True
                    break

            if played:
                continue

            # 7.5 使用闪电（放在自己判定区）
            for card in list(player.hand):
                if card.name == CardName.SHANDIAN:
                    # 如果判定区没有闪电，尝试使用
                    has_shandian = any(c.name == CardName.SHANDIAN for c in player.judge_area)
                    if not has_shandian and engine.use_card(player, card):
                        played = True
                        break

            if played:
                continue

            # 7.6 使用酒（配合杀使用）
            if player.can_use_sha() and not player.alcohol_used:

                jiu_cards = [c for c in player.hand if c.subtype == CardSubtype.ALCOHOL]
                sha_cards = player.get_cards_by_name(CardName.SHA)
                if jiu_cards and sha_cards:
                    targets = self._get_attack_targets(player, engine)
                    if targets and engine.use_card(player, jiu_cards[0]):
                        played = True
                        continue

            # 8. 使用主动技能
            if engine.skill_system:
                usable_skills = engine.skill_system.get_usable_skills(player)
                for skill_id in usable_skills:
                    if self._should_use_skill(player, skill_id, engine) and self._use_skill_with_ai(
                        player, skill_id, engine
                    ):
                        played = True
                        break

            # 无法行动则结束
            if not played:
                break

    def choose_discard(self, player: Player, count: int, engine: GameEngine) -> list[Card]:
        """智能弃牌."""
        return smart_discard(player, count)

    def should_use_qinglong(self, player: Player, target: Player, engine: GameEngine) -> bool:
        """有杀且是敌人就继续."""
        sha_count = len(player.get_cards_by_name(CardName.SHA))
        if sha_count > 1:
            return is_enemy(player, target)
        return False

    # ==================== 目标选择 ====================

    def _get_attack_targets(self, player: Player, engine: GameEngine) -> list[Player]:
        """获取可攻击的敌方目标."""
        targets = engine.get_targets_in_range(player)
        return [t for t in targets if is_enemy(player, t)]

    def choose_best_target(
        self, player: Player, targets: list[Player], engine: GameEngine
    ) -> Player:
        """选择最佳攻击目标（普通模式）.

        优先攻击体力低的敌人。
        """
        if not targets:
            return None
        targets.sort(key=lambda t: (t.hp, t.hand_count))
        return targets[0]

    def _choose_dismount_target(self, player: Player, engine: GameEngine) -> Player | None:
        """选择过河拆桥的目标."""
        others = engine.get_other_players(player)
        enemies = [t for t in others if is_enemy(player, t) and t.has_any_card()]

        if enemies:
            with_equip = [t for t in enemies if t.equipment.has_equipment()]
            if with_equip:
                return random.choice(with_equip)
            return random.choice(enemies)
        return None

    def _choose_steal_target(self, player: Player, engine: GameEngine) -> Player | None:
        """选择顺手牵羊的目标."""
        others = engine.get_other_players(player)
        valid = [
            t for t in others if engine.calculate_distance(player, t) <= 1 and t.has_any_card()
        ]
        enemies = [t for t in valid if is_enemy(player, t)]

        if enemies:
            return random.choice(enemies)
        return None

    def _choose_duel_target(self, player: Player, engine: GameEngine) -> Player | None:
        """选择决斗的目标."""
        others = engine.get_other_players(player)
        enemies = [t for t in others if is_enemy(player, t)]

        if enemies:
            enemies.sort(key=lambda t: t.hand_count)
            return enemies[0]
        return None

    def _choose_jiedao_targets(self, player: Player, engine: GameEngine) -> list[Player] | None:
        """选择借刀杀人的目标 — 返回 [wielder, sha_target]."""
        others = engine.get_other_players(player)
        with_weapon = [t for t in others if t.equipment.weapon and t.is_alive]
        if not with_weapon:
            return None
        # 优先让友方持武器者去杀敌人，其次让敌方持武器者去杀敌人
        best_pair = None
        for wielder in with_weapon:
            sha_targets = [
                t
                for t in engine.players
                if t.is_alive
                and t != wielder
                and t != player
                and engine.is_in_attack_range(wielder, t)
            ]
            enemy_targets = [t for t in sha_targets if is_enemy(player, t)]
            if enemy_targets:
                target = min(enemy_targets, key=lambda t: t.hp)
                if not is_enemy(player, wielder):
                    return [wielder, target]  # 友方借刀杀敌人，最优
                if best_pair is None:
                    best_pair = [wielder, target]
        return best_pair

    def _choose_lebusishu_target(self, player: Player, engine: GameEngine) -> Player | None:
        """选择乐不思蜀的目标 — 优先手牌多的敌人."""
        others = engine.get_other_players(player)
        enemies = [
            t
            for t in others
            if is_enemy(player, t)
            and t.is_alive
            and not any(c.name == CardName.LEBUSISHU for c in t.judge_area)
        ]
        if not enemies:
            return None
        # 优先乐手牌多、体力高的敌人
        enemies.sort(key=lambda t: t.hand_count + t.hp, reverse=True)
        return enemies[0]

    def _choose_bingliang_target(self, player: Player, engine: GameEngine) -> Player | None:
        """选择兵粮寸断的目标 — 距离≤1的敌人."""
        others = engine.get_other_players(player)
        enemies = [
            t
            for t in others
            if is_enemy(player, t)
            and t.is_alive
            and engine.calculate_distance(player, t) <= 1
            and not any(c.name == CardName.BINGLIANG for c in t.judge_area)
        ]
        if not enemies:
            return None
        enemies.sort(key=lambda t: t.hand_count + t.hp, reverse=True)
        return enemies[0]

    def _choose_huogong_target(self, player: Player, engine: GameEngine) -> Player | None:
        """选择火攻的目标 — 有手牌的敌人."""
        others = engine.get_other_players(player)
        enemies = [t for t in others if is_enemy(player, t) and t.is_alive and t.hand_count > 0]
        if not enemies:
            return None
        enemies.sort(key=lambda t: t.hp)
        return enemies[0]

    def _choose_tiesuo_targets(self, player: Player, engine: GameEngine) -> list[Player] | None:
        """选择铁索连环的目标 — 1-2个敌人，无合适敌人则重铸."""
        others = engine.get_other_players(player)
        enemies = [t for t in others if is_enemy(player, t) and t.is_alive and not t.is_chained]
        if not enemies:
            return []  # 重铸
        # 选择1-2个敌人
        targets = enemies[: min(2, len(enemies))]
        return targets

    def _should_use_aoe(self, player: Player, engine: GameEngine) -> bool:
        """判断是否应该使用AOE."""
        others = engine.get_other_players(player)
        enemies = [t for t in others if is_enemy(player, t)]
        friends = [t for t in others if not is_enemy(player, t)]
        return len(enemies) > len(friends)

    # ==================== 技能决策 ====================

    def _should_use_skill(self, player: Player, skill_id: str, engine: GameEngine) -> bool:
        """判断是否应该使用技能."""
        if skill_id == SkillId.ZHIHENG:
            useless = count_useless_cards(player, engine)
            return useless >= 2

        elif skill_id == SkillId.RENDE:
            if player.hand_count > 4:
                friends = get_friends(player, engine)
                return len(friends) > 0

        elif skill_id == SkillId.FANJIAN:
            enemies = [p for p in engine.get_other_players(player) if is_enemy(player, p)]
            return player.hand_count > 0 and len(enemies) > 0

        elif skill_id == SkillId.GUOSE:
            diamond_cards = [c for c in player.hand if c.suit == CardSuit.DIAMOND]
            enemies = [
                p for p in engine.get_other_players(player) if is_enemy(player, p) and p.is_alive
            ]
            return len(diamond_cards) > 0 and len(enemies) > 0

        elif skill_id == SkillId.DUANLIANG:
            black_cards = [
                c
                for c in player.hand
                if c.suit.is_black and c.card_type in (CardType.BASIC, CardType.EQUIPMENT)
            ]
            enemies = [
                p
                for p in engine.get_other_players(player)
                if is_enemy(player, p) and p.is_alive and engine.calculate_distance(player, p) <= 2
            ]
            return len(black_cards) > 0 and len(enemies) > 0

        elif skill_id == SkillId.QIXI:
            black_cards = [c for c in player.hand if c.suit.is_black]
            enemies = [
                p
                for p in engine.get_other_players(player)
                if is_enemy(player, p) and p.is_alive and p.has_any_card()
            ]
            return len(black_cards) > 0 and len(enemies) > 0

        elif skill_id == SkillId.KUROU:
            return player.hp >= 2 and player.hand_count <= 2

        elif skill_id == SkillId.SHENSU:
            enemies = [
                p for p in engine.get_other_players(player) if is_enemy(player, p) and p.is_alive
            ]
            return len(enemies) > 0

        elif skill_id == SkillId.MUZHEN:
            return engine.skill_system is not None and engine.skill_system.can_use_skill(skill_id, player)

        return False

    def _use_skill_with_ai(self, player: Player, skill_id: str, engine: GameEngine) -> bool:
        """AI使用技能."""
        if not engine.skill_system:
            return False

        if skill_id == SkillId.ZHIHENG:
            cards_to_discard = smart_discard(player, min(3, player.hand_count))
            return execute_use_skill_action(engine, skill_id, player, cards=cards_to_discard)

        elif skill_id == SkillId.RENDE:
            friends = get_friends(player, engine)
            if friends and player.hand_count > 2:
                target = random.choice(friends)
                cards = [player.hand[0]]
                return execute_use_skill_action(engine, 
                    skill_id, player, targets=[target], cards=cards
                )

        elif skill_id == SkillId.FANJIAN:
            enemies = [p for p in engine.get_other_players(player) if is_enemy(player, p)]
            if enemies and player.hand:
                target = random.choice(enemies)
                card = random.choice(player.hand)
                return engine.skill_system.use_skill(
                    skill_id, player, targets=[target], cards=[card]
                )

        elif skill_id == SkillId.GUOSE:
            diamond_cards = [c for c in player.hand if c.suit == CardSuit.DIAMOND]
            enemies = [
                p for p in engine.get_other_players(player) if is_enemy(player, p) and p.is_alive
            ]
            if diamond_cards and enemies:
                card = diamond_cards[0]
                target = self._choose_control_target(enemies)
                return engine.skill_system.use_skill(
                    skill_id, player, targets=[target], cards=[card]
                )

        elif skill_id == SkillId.DUANLIANG:
            black_cards = [
                c
                for c in player.hand
                if c.suit.is_black and c.card_type in (CardType.BASIC, CardType.EQUIPMENT)
            ]
            enemies = [
                p
                for p in engine.get_other_players(player)
                if is_enemy(player, p) and p.is_alive and engine.calculate_distance(player, p) <= 2
            ]
            if black_cards and enemies:
                card = pick_least_valuable(black_cards, player)
                target = self._choose_control_target(enemies)
                return engine.skill_system.use_skill(
                    skill_id, player, targets=[target], cards=[card]
                )

        elif skill_id == SkillId.QIXI:
            black_cards = [c for c in player.hand if c.suit.is_black]
            enemies = [
                p
                for p in engine.get_other_players(player)
                if is_enemy(player, p) and p.is_alive and p.has_any_card()
            ]
            if black_cards and enemies:
                card = pick_least_valuable(black_cards, player)
                target = self._choose_dismount_target_from(enemies)
                if target:
                    return engine.skill_system.use_skill(
                        skill_id, player, targets=[target], cards=[card]
                    )

        elif skill_id == SkillId.KUROU:
            return engine.skill_system.use_skill(skill_id, player)

        elif skill_id == SkillId.SHENSU:
            enemies = [
                p for p in engine.get_other_players(player) if is_enemy(player, p) and p.is_alive
            ]
            if enemies:
                target = self.choose_best_target(player, enemies, engine)
                if target:
                    return engine.skill_system.use_skill(skill_id, player, targets=[target])

        elif skill_id == SkillId.MUZHEN:
            state = player.get_skill_state(SkillId.MUZHEN)
            others = engine.get_other_players(player)

            if not state.get("option_one_used", False) and player.hand_count >= 2:
                option_one_targets = [
                    other
                    for other in others
                    if other.is_alive and other.equipment.has_equipment() and is_enemy(player, other)
                ]
                if not option_one_targets:
                    option_one_targets = [
                        other for other in others if other.is_alive and other.equipment.has_equipment()
                    ]
                if option_one_targets:
                    target = max(option_one_targets, key=lambda other: (other.equipment.count, other.hand_count))
                    cards = self._pick_least_valuable_cards(player, 2)
                    equipment_cards = target.equipment.get_all_cards()
                    if cards and equipment_cards:
                        return engine.skill_system.use_skill(
                            skill_id,
                            player,
                            targets=[target],
                            cards=cards,
                            option=1,
                            equip_card=equipment_cards[0],
                        )

            if state.get("option_two_used", False):
                return False

            option_two_choices = []
            equipment_cards = [card for card in player.hand if card.card_type == CardType.EQUIPMENT]
            for target in others:
                if not target.is_alive or target.hand_count <= 0 or not is_enemy(player, target):
                    continue
                for equipment_card in equipment_cards:
                    slot_name = self._equipment_slot_name(equipment_card)
                    if slot_name and getattr(target.equipment, slot_name) is None:
                        subtype_score = 0 if equipment_card.subtype == CardSubtype.WEAPON else 1
                        option_two_choices.append(
                            (subtype_score, target.hand_count, -target.hp, target, equipment_card)
                        )

            if option_two_choices:
                _, _, _, target, equipment_card = max(option_two_choices)
                return engine.skill_system.use_skill(
                    skill_id,
                    player,
                    targets=[target],
                    cards=[equipment_card],
                    option=2,
                    stolen_card=target.hand[0],
                )

        return False

    # ==================== 辅助方法 ====================

    def _pick_least_valuable_cards(self, player: Player, count: int) -> list[Card]:
        """选择若干张价值最低的手牌."""
        selected = []
        candidates = list(player.hand)
        for _ in range(min(count, len(candidates))):
            card = pick_least_valuable(candidates, player)
            selected.append(card)
            candidates.remove(card)
        return selected

    def _equipment_slot_name(self, card: Card) -> str | None:
        """根据装备牌子类型映射到装备槽名."""
        return {
            CardSubtype.WEAPON: "weapon",
            CardSubtype.ARMOR: "armor",
            CardSubtype.HORSE_MINUS: "horse_minus",
            CardSubtype.HORSE_PLUS: "horse_plus",
        }.get(card.subtype)

    def _try_use_yanliang(self, player: Player, engine: GameEngine) -> bool:
        """判断并尝试在出牌阶段发动厌粱."""
        lord = engine.lord_player
        if (
            engine.skill_system is None
            or lord is None
            or lord == player
            or not lord.is_alive
            or not lord.has_skill(SkillId.YANLIANG)
            or not player.hero
            or player.hero.kingdom.value != "qun"
            or player.get_turn_flag("yanliang_used", False)
            or player.alcohol_used
        ):
            return False

        equipment_cards = [card for card in player.hand if card.card_type == CardType.EQUIPMENT]
        if not equipment_cards:
            return False

        has_attack_card = bool(player.get_cards_by_name(CardName.SHA))
        if player.has_skill(SkillId.WUSHENG) and not has_attack_card:
            has_attack_card = bool(player.get_red_cards())
        if not has_attack_card or not self._get_attack_targets(player, engine):
            return False

        card = pick_least_valuable(equipment_cards, player)
        return engine.skill_system.trigger_skill(
            SkillId.YANLIANG,
            lord,
            engine,
            donor=player,
            card=card,
        )

    def _choose_control_target(self, enemies: list[Player]) -> Player:
        """选择控制类技能（国色/断粮）的最佳目标."""
        enemies.sort(key=lambda t: t.hand_count + t.hp, reverse=True)
        return enemies[0]

    def _choose_dismount_target_from(self, enemies: list[Player]) -> Player | None:
        """从敌人列表选择过河拆桥/奇袭目标."""
        with_equip = [t for t in enemies if t.equipment.has_equipment()]
        if with_equip:
            return random.choice(with_equip)
        return random.choice(enemies) if enemies else None
