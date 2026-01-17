# -*- coding: utf-8 -*-
"""
技能系统模块
负责所有武将技能的具体实现
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass
import random

if TYPE_CHECKING:
    from .player import Player
    from .engine import GameEngine
    from .card import Card
    from .hero import Skill


class SkillSystem:
    """
    技能系统类
    负责管理和执行所有武将技能
    """

    def __init__(self, game_engine: 'GameEngine'):
        """
        初始化技能系统
        
        Args:
            game_engine: 游戏引擎引用
        """
        self.engine = game_engine

        # 技能处理器映射
        self._skill_handlers: Dict[str, Callable] = {
            # 蜀国武将
            "rende": self._handle_rende,       # 刘备-仁德
            "jijiang": self._handle_jijiang,   # 刘备-激将
            "wusheng": self._handle_wusheng,   # 关羽-武圣
            "paoxiao": self._handle_paoxiao,   # 张飞-咆哮
            "guanxing": self._handle_guanxing, # 诸葛亮-观星
            "kongcheng": self._handle_kongcheng,  # 诸葛亮-空城
            "longdan": self._handle_longdan,   # 赵云-龙胆
            "mashu": self._handle_mashu,       # 马超-马术
            "tieji": self._handle_tieji,       # 马超-铁骑
            "jizhi": self._handle_jizhi,       # 黄月英-集智
            "qicai": self._handle_qicai,       # 黄月英-奇才
            # 魏国武将
            "jianxiong": self._handle_jianxiong,  # 曹操-奸雄
            "hujia": self._handle_hujia,       # 曹操-护驾
            "fankui": self._handle_fankui,     # 司马懿-反馈
            "guicai": self._handle_guicai,     # 司马懿-鬼才
            "ganglie": self._handle_ganglie,   # 夏侯惇-刚烈
            "tuxi": self._handle_tuxi,         # 张辽-突袭
            # 吴国武将
            "zhiheng": self._handle_zhiheng,   # 孙权-制衡
            "jiuyuan": self._handle_jiuyuan,   # 孙权-救援
            "yingzi": self._handle_yingzi,     # 周瑜-英姿
            "fanjian": self._handle_fanjian,   # 周瑜-反间
            "guose": self._handle_guose,       # 大乔-国色
            "liuli": self._handle_liuli,       # 大乔-流离
            # 群雄武将
            "wushuang": self._handle_wushuang, # 吕布-无双
            "qingnang": self._handle_qingnang, # 华佗-青囊
            "jijiu": self._handle_jijiu,       # 华佗-急救
            "lijian": self._handle_lijian,     # 貂蝉-离间
            "biyue": self._handle_biyue,       # 貂蝉-闭月
            # 新武将
            "liegong": self._handle_liegong,   # 黄忠-烈弓
            "kuanggu": self._handle_kuanggu,   # 魏延-狂骨
            "duanliang": self._handle_duanliang, # 徐晃-断粮
            "jushou": self._handle_jushou,     # 曹仁-据守
            "qixi": self._handle_qixi,         # 甘宁-奇袭
            "keji": self._handle_keji,         # 吕蒙-克己
            "kurou": self._handle_kurou,       # 黄盖-苦肉
            "shensu": self._handle_shensu,     # 夏侯渊-神速
            "jieyin": self._handle_jieyin,     # 孙尚香-结姻
            "xiaoji": self._handle_xiaoji,     # 孙尚香-枭姬
        }

    def can_use_skill(self, skill_id: str, player: 'Player') -> bool:
        """
        检查玩家是否可以使用指定技能
        
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
        if skill_id == "rende":
            return len(player.hand) > 0
        elif skill_id == "zhiheng":
            return len(player.hand) > 0
        elif skill_id == "fanjian":
            return len(player.hand) > 0 and len(self.engine.get_other_players(player)) > 0

        return True

    def trigger_skill(self, skill_id: str, player: 'Player',
                     game_engine: 'GameEngine', **kwargs) -> bool:
        """
        触发技能
        
        Args:
            skill_id: 技能ID
            player: 使用技能的玩家
            game_engine: 游戏引擎
            **kwargs: 额外参数
            
        Returns:
            是否成功触发
        """
        if skill_id not in self._skill_handlers:
            return False

        handler = self._skill_handlers[skill_id]
        return handler(player, game_engine, **kwargs)

    def use_skill(self, skill_id: str, player: 'Player',
                  targets: Optional[List['Player']] = None,
                  cards: Optional[List['Card']] = None) -> bool:
        """
        使用主动技能
        
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

        result = self.trigger_skill(skill_id, player, self.engine,
                                   targets=targets, cards=cards)

        if result:
            # 记录使用次数
            player.skill_used[skill_id] = player.skill_used.get(skill_id, 0) + 1

            skill = player.get_skill(skill_id)
            if skill:
                skill.use()

        return result

    def get_usable_skills(self, player: 'Player') -> List[str]:
        """
        获取玩家当前可以使用的技能列表
        
        Args:
            player: 玩家
            
        Returns:
            可用技能ID列表
        """
        usable = []
        if player.hero:
            for skill in player.hero.skills:
                if skill.skill_type.value == "active" and self.can_use_skill(skill.id, player):
                    usable.append(skill.id)
        return usable

    # ==================== 技能处理器 ====================

    def _handle_rende(self, player: 'Player', engine: 'GameEngine',
                      targets: Optional[List['Player']] = None,
                      cards: Optional[List['Card']] = None, **kwargs) -> bool:
        """
        仁德：将任意数量的手牌交给其他角色，每回合给出第二张牌时回复1点体力
        """
        if not targets or not cards:
            return False

        target = targets[0]

        # 移除并转移卡牌
        transferred_cards = []
        for card in cards:
            if card in player.hand:
                player.remove_card(card)
                transferred_cards.append(card)

        if not transferred_cards:
            return False

        target.draw_cards(transferred_cards)

        cards_str = ", ".join(c.display_name for c in transferred_cards)
        engine.log_event("skill", f"{player.name} 发动【仁德】，将 {cards_str} 交给了 {target.name}")

        # 检查是否回复体力（本回合给出的第二张牌）
        rende_count = player.skill_used.get("rende_cards", 0)
        for card in transferred_cards:
            rende_count += 1
            if rende_count == 2 and player.hp < player.max_hp:
                player.heal(1)
                engine.log_event("skill", f"{player.name} 因【仁德】回复1点体力")

        player.skill_used["rende_cards"] = rende_count

        return True

    def _handle_jijiang(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        激将：主公技，让其他蜀势力角色代替出杀
        """
        if player.identity.value != "lord":
            return False

        from .hero import Kingdom

        # 寻找蜀势力角色
        for other in engine.get_other_players(player):
            if other.hero and other.hero.kingdom == Kingdom.SHU:
                sha_cards = other.get_cards_by_name("杀")
                if sha_cards:
                    # AI自动响应
                    if other.is_ai:
                        card = sha_cards[0]
                        other.remove_card(card)
                        engine.deck.discard([card])
                        engine.log_event("skill", f"{other.name} 响应【激将】，打出了【杀】")
                        return True
                    else:
                        # 人类玩家需要UI确认
                        if engine.ui:
                            result = engine.ui.ask_for_jijiang(other)
                            if result:
                                other.remove_card(result)
                                engine.deck.discard([result])
                                engine.log_event("skill", f"{other.name} 响应【激将】，打出了【杀】")
                                return True

        return False

    def _handle_jianxiong(self, player: 'Player', engine: 'GameEngine',
                          damage_card: Optional['Card'] = None, **kwargs) -> bool:
        """
        奸雄：受到伤害后，可以获得造成伤害的牌
        """
        if damage_card:
            # 从弃牌堆取回
            if damage_card in engine.deck.discard_pile:
                engine.deck.discard_pile.remove(damage_card)
                player.draw_cards([damage_card])
                engine.log_event("skill", f"{player.name} 发动【奸雄】，获得了 {damage_card.display_name}")
                return True
        return False

    def _handle_hujia(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        护驾：主公技，让其他魏势力角色代替出闪
        """
        if player.identity.value != "lord":
            return False

        from .hero import Kingdom

        for other in engine.get_other_players(player):
            if other.hero and other.hero.kingdom == Kingdom.WEI:
                shan_cards = other.get_cards_by_name("闪")
                if shan_cards:
                    if other.is_ai:
                        card = shan_cards[0]
                        other.remove_card(card)
                        engine.deck.discard([card])
                        engine.log_event("skill", f"{other.name} 响应【护驾】，打出了【闪】")
                        return True
                    else:
                        if engine.ui:
                            result = engine.ui.ask_for_hujia(other)
                            if result:
                                other.remove_card(result)
                                engine.deck.discard([result])
                                engine.log_event("skill", f"{other.name} 响应【护驾】，打出了【闪】")
                                return True

        return False

    def _handle_zhiheng(self, player: 'Player', engine: 'GameEngine',
                        cards: Optional[List['Card']] = None, **kwargs) -> bool:
        """
        制衡：弃置任意数量的牌，然后摸等量的牌
        """
        if not cards:
            return False

        discard_count = len(cards)

        # 弃置选择的牌
        for card in cards:
            if card in player.hand:
                player.remove_card(card)
                engine.deck.discard([card])

        # 摸等量的牌
        new_cards = engine.deck.draw(discard_count)
        player.draw_cards(new_cards)

        engine.log_event("skill", f"{player.name} 发动【制衡】，弃置 {discard_count} 张牌，摸 {len(new_cards)} 张牌")
        return True

    def _handle_jiuyuan(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        救援：锁定技，其他吴势力角色对你使用桃时，额外回复1点体力
        （此技能在使用桃时自动触发，这里只是标记）
        """
        return True

    def _handle_wusheng(self, player: 'Player', engine: 'GameEngine',
                        card: Optional['Card'] = None, **kwargs) -> bool:
        """
        武圣：可以将红色牌当杀使用或打出
        （此技能主要在请求杀/闪时自动检查）
        """
        return True

    def _handle_paoxiao(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        咆哮：锁定技，出牌阶段使用杀无次数限制
        （此技能在can_use_sha中自动检查）
        """
        return True

    def _handle_guanxing(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        观星：准备阶段，观看牌堆顶X张牌（X为存活角色数，最多5张）
        """
        alive_count = len(engine.get_alive_players())
        look_count = min(5, alive_count)

        # 查看牌堆顶的牌
        cards = engine.deck.peek(look_count)

        if not cards:
            return False

        engine.log_event("skill", f"{player.name} 发动【观星】，观看牌堆顶 {len(cards)} 张牌")

        if player.is_ai:
            # AI策略：把好牌放顶部
            # 简单逻辑：优先级 桃 > 闪 > 杀 > 其他
            def card_priority(c: 'Card') -> int:
                if c.name == "桃":
                    return 0
                elif c.name == "闪":
                    return 1
                elif c.name == "杀":
                    return 2
                elif c.name == "无中生有":
                    return 3
                return 10

            sorted_cards = sorted(cards, key=card_priority)

            # 取出这些牌
            for _ in range(len(cards)):
                engine.deck.draw_pile.pop()

            # 一半放顶部，一半放底部
            half = len(sorted_cards) // 2
            top_cards = sorted_cards[:half+1]
            bottom_cards = sorted_cards[half+1:]

            engine.deck.put_on_top(top_cards)
            engine.deck.put_on_bottom(bottom_cards)
        else:
            # 人类玩家需要UI交互
            if engine.ui:
                top_cards, bottom_cards = engine.ui.guanxing_selection(player, cards)

                # 取出这些牌
                for _ in range(len(cards)):
                    engine.deck.draw_pile.pop()

                engine.deck.put_on_top(list(reversed(top_cards)))
                engine.deck.put_on_bottom(bottom_cards)

        return True

    def _handle_kongcheng(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        空城：锁定技，若没有手牌，不是杀和决斗的合法目标
        （此技能在使用杀/决斗时自动检查）
        """
        return player.hand_count == 0

    def _handle_yingzi(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        英姿：摸牌阶段多摸一张牌
        （此技能在摸牌阶段自动触发）
        """
        return True

    def _handle_fanjian(self, player: 'Player', engine: 'GameEngine',
                        targets: Optional[List['Player']] = None,
                        cards: Optional[List['Card']] = None, **kwargs) -> bool:
        """
        反间：选择一名角色，展示一张手牌，让其猜花色
        """
        if not targets or not cards:
            return False

        target = targets[0]
        card = cards[0]

        if card not in player.hand:
            return False

        engine.log_event("skill", f"{player.name} 对 {target.name} 发动【反间】")

        # 让目标选择花色
        if target.is_ai:
            # AI随机选择
            from .card import CardSuit
            guessed_suit = random.choice(list(CardSuit))
        else:
            if engine.ui:
                guessed_suit = engine.ui.choose_suit(target)
            else:
                from .card import CardSuit
                guessed_suit = random.choice(list(CardSuit))

        engine.log_event("skill", f"{target.name} 猜测花色为 {guessed_suit.symbol}")

        # 移除卡牌并给目标
        player.remove_card(card)
        target.draw_cards([card])

        engine.log_event("skill", f"展示的牌是 {card.display_name}")

        # 判断是否造成伤害
        if card.suit != guessed_suit:
            engine.log_event("skill", f"花色不同，{target.name} 受到1点伤害")
            engine.deal_damage(player, target, 1)
        else:
            engine.log_event("skill", f"花色相同，{target.name} 躲过一劫")

        return True

    def _handle_wushuang(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        无双：锁定技，使用杀需要两张闪，决斗需要两张杀
        （此技能在杀/决斗结算时自动生效）
        """
        return True

    # ==================== 新武将技能 ====================

    def _handle_longdan(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        龙胆：可以将杀当闪使用或打出，或将闪当杀使用或打出
        （转化技能，在需要杀/闪时自动检查）
        """
        return True

    def _handle_mashu(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        马术：锁定技，计算与其他角色的距离-1
        （在距离计算时自动生效）
        """
        return True

    def _handle_tieji(self, player: 'Player', engine: 'GameEngine',
                      target: 'Player' = None, **kwargs) -> bool:
        """
        铁骑：使用杀指定目标后，可以进行判定，若结果为红色，目标不能使用闪
        """
        if target is None:
            return False

        # 进行判定
        judge_card = engine.deck.draw(1)[0]
        engine.log_event("skill", f"{player.name} 发动【铁骑】，判定结果: {judge_card.display_name}")
        engine.deck.discard([judge_card])

        if judge_card.is_red:
            engine.log_event("skill", f"判定为红色，{target.name} 不能使用【闪】响应此【杀】")
            return True  # 返回True表示目标不能出闪

        return False

    def _handle_jizhi(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        集智：使用非延时锦囊牌时，可以摸一张牌
        （在使用锦囊牌后触发）
        """
        cards = engine.deck.draw(1)
        player.draw_cards(cards)
        engine.log_event("skill", f"{player.name} 发动【集智】，摸了1张牌")
        return True

    def _handle_qicai(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        奇才：锁定技，使用锦囊牌无距离限制
        （在使用锦囊牌时自动生效）
        """
        return True

    def _handle_fankui(self, player: 'Player', engine: 'GameEngine',
                       source: 'Player' = None, **kwargs) -> bool:
        """
        反馈：受到伤害后，可以获得伤害来源的一张牌
        """
        if source is None or source == player:
            return False

        if not source.has_any_card():
            return False

        # 获取来源的一张牌
        all_cards = source.get_all_cards()
        if all_cards:
            card = random.choice(all_cards)
            if card in source.hand:
                source.remove_card(card)
            else:
                # 从装备区移除（使用 unequip_card 辅助方法）
                source.equipment.unequip_card(card)
            player.draw_cards([card])
            engine.log_event("skill", f"{player.name} 发动【反馈】，获得了 {source.name} 的一张牌")
            return True

        return False

    def _handle_guicai(self, player: 'Player', engine: 'GameEngine',
                       judge_card: 'Card' = None, **kwargs) -> bool:
        """
        鬼才：在判定牌生效前，可以打出一张手牌代替之
        """
        if not player.hand:
            return False

        # AI自动选择或玩家选择
        if player.is_ai:
            # AI策略：如果判定结果不好，尝试更换
            card = player.hand[0]  # 简单选择第一张
            player.remove_card(card)
            engine.deck.discard([card])
            engine.log_event("skill", f"{player.name} 发动【鬼才】，用 {card.display_name} 替换判定牌")
            return True

        return False

    def _handle_ganglie(self, player: 'Player', engine: 'GameEngine',
                        source: 'Player' = None, **kwargs) -> bool:
        """
        刚烈：受到伤害后，可以进行判定，若结果不为红桃，伤害来源须弃置两张手牌或受到1点伤害
        """
        if source is None or source == player:
            return False

        # 进行判定
        judge_card = engine.deck.draw(1)[0]
        engine.log_event("skill", f"{player.name} 发动【刚烈】，判定结果: {judge_card.display_name}")
        engine.deck.discard([judge_card])

        from .card import CardSuit
        if judge_card.suit != CardSuit.HEART:
            # 来源需要弃两张牌或受1点伤害
            if source.hand_count >= 2:
                if source.is_ai:
                    # AI弃牌
                    cards = source.hand[:2]
                    for c in cards:
                        source.remove_card(c)
                    engine.deck.discard(cards)
                    engine.log_event("skill", f"{source.name} 弃置了两张牌")
                else:
                    # 让玩家选择
                    engine.deal_damage(player, source, 1)
            else:
                engine.deal_damage(player, source, 1)
            return True

        return False

    def _handle_tuxi(self, player: 'Player', engine: 'GameEngine',
                     targets: list = None, **kwargs) -> bool:
        """
        突袭：摸牌阶段，可以少摸牌，然后获得等量其他角色各一张手牌
        """
        if targets is None:
            targets = []

        for target in targets:
            if target.hand:
                card = random.choice(target.hand)
                target.remove_card(card)
                player.draw_cards([card])
                engine.log_event("skill", f"{player.name} 发动【突袭】，获得了 {target.name} 的一张手牌")

        return len(targets) > 0

    def _handle_guose(self, player: 'Player', engine: 'GameEngine',
                      card: 'Card' = None, target: 'Player' = None, **kwargs) -> bool:
        """
        国色：可以将一张方块牌当【乐不思蜀】使用
        （转化技能，暂未实现延时锦囊）
        """
        return True

    def _handle_liuli(self, player: 'Player', engine: 'GameEngine',
                      new_target: 'Player' = None, **kwargs) -> bool:
        """
        流离：成为杀的目标时，可以弃置一张牌并选择攻击范围内的一名其他角色，将此杀转移给该角色
        """
        if new_target is None or not player.hand:
            return False

        # 弃置一张牌
        card = player.hand[0]
        player.remove_card(card)
        engine.deck.discard([card])

        engine.log_event("skill", f"{player.name} 发动【流离】，将【杀】转移给 {new_target.name}")
        return True

    def _handle_qingnang(self, player: 'Player', engine: 'GameEngine',
                         target: 'Player' = None, cards: list = None, **kwargs) -> bool:
        """
        青囊：出牌阶段限一次，弃置一张手牌，令一名角色回复1点体力
        """
        if not cards or not target:
            return False

        card = cards[0]
        if card not in player.hand:
            return False

        player.remove_card(card)
        engine.deck.discard([card])

        healed = target.heal(1)
        engine.log_event("skill", f"{player.name} 发动【青囊】，{target.name} 回复了 {healed} 点体力")
        return True

    def _handle_jijiu(self, player: 'Player', engine: 'GameEngine',
                      card: 'Card' = None, **kwargs) -> bool:
        """
        急救：回合外，可以将一张红色牌当【桃】使用
        （转化技能，在濒死求桃时检查）
        """
        return True

    # ==================== 貂蝉技能 ====================

    def _handle_lijian(self, player: 'Player', engine: 'GameEngine',
                       targets: List['Player'] = None, card: 'Card' = None, **kwargs) -> bool:
        """
        离间：出牌阶段限一次，弃一牌令两名男性角色决斗
        """
        if not card or not targets or len(targets) < 2:
            return False

        player.remove_card(card)
        engine.deck.discard([card])

        target1, target2 = targets[0], targets[1]
        engine.log_event("skill", f"{player.name} 发动【离间】，{target1.name} 视为对 {target2.name} 使用【决斗】")

        # 模拟决斗
        engine._use_juedou_forced(target1, target2)
        return True

    def _handle_biyue(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        闭月：结束阶段摸一张牌
        """
        cards = engine.deck.draw(1)
        player.draw_cards(cards)
        engine.log_event("skill", f"{player.name} 发动【闭月】，摸了 1 张牌")
        return True

    # ==================== 新武将技能 ====================

    def _handle_liegong(self, player: 'Player', engine: 'GameEngine',
                        target: 'Player' = None, **kwargs) -> bool:
        """
        烈弓：使用杀时，若目标手牌数>=你体力值或<=你攻击范围，其不能闪避
        """
        if not target:
            return False

        target_hand = target.hand_count
        player_hp = player.hp
        attack_range = player.equipment.attack_range

        if target_hand >= player_hp or target_hand <= attack_range:
            engine.log_event("skill", f"{player.name} 发动【烈弓】，{target.name} 不能使用【闪】")
            return True
        return False

    def _handle_kuanggu(self, player: 'Player', engine: 'GameEngine',
                        target: 'Player' = None, damage: int = 1, **kwargs) -> bool:
        """
        狂骨：对距离1以内的角色造成伤害后回复1点体力
        """
        if not target:
            return False

        distance = engine.calculate_distance(player, target)
        if distance <= 1 and player.hp < player.max_hp:
            player.heal(1)
            engine.log_event("skill", f"{player.name} 发动【狂骨】，回复了 1 点体力")
            return True
        return False

    def _handle_duanliang(self, player: 'Player', engine: 'GameEngine',
                          card: 'Card' = None, **kwargs) -> bool:
        """
        断粮：将黑色基本牌或装备牌当【兵粮寸断】使用
        """
        # 转化技能，在出牌时检查
        return True

    def _handle_jushou(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        据守：结束阶段摸三张牌并翻面
        """
        cards = engine.deck.draw(3)
        player.draw_cards(cards)
        player.toggle_flip()
        engine.log_event("skill", f"{player.name} 发动【据守】，摸了 3 张牌并翻面")
        return True

    def _handle_qixi(self, player: 'Player', engine: 'GameEngine',
                     card: 'Card' = None, **kwargs) -> bool:
        """
        奇袭：将黑色牌当【过河拆桥】使用
        """
        # 转化技能，在出牌时检查
        return True

    def _handle_keji(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        克己：若出牌阶段未使用杀，跳过弃牌阶段
        """
        if player.sha_count == 0:
            engine.log_event("skill", f"{player.name} 发动【克己】，跳过弃牌阶段")
            return True
        return False

    def _handle_kurou(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        苦肉：出牌阶段，失去1点体力摸两张牌
        """
        if player.hp <= 1:
            return False

        player.hp -= 1
        cards = engine.deck.draw(2)
        player.draw_cards(cards)
        engine.log_event("skill", f"{player.name} 发动【苦肉】，失去 1 点体力，摸了 2 张牌")
        return True

    def _handle_shensu(self, player: 'Player', engine: 'GameEngine',
                       target: 'Player' = None, choice: int = 1, **kwargs) -> bool:
        """
        神速：跳过阶段视为对目标使用杀
        """
        if not target:
            return False

        engine.log_event("skill", f"{player.name} 发动【神速】，视为对 {target.name} 使用【杀】")
        engine.deal_damage(player, target, 1)
        return True

    def _handle_jieyin(self, player: 'Player', engine: 'GameEngine',
                       target: 'Player' = None, cards: List['Card'] = None, **kwargs) -> bool:
        """
        结姻：弃两张手牌，自己和一名受伤男性各回复1点体力
        """
        if not target or not cards or len(cards) < 2:
            return False

        if target.gender != "male" or target.hp >= target.max_hp:
            return False

        for card in cards:
            player.remove_card(card)
        engine.deck.discard(cards)

        player.heal(1)
        target.heal(1)
        engine.log_event("skill", f"{player.name} 发动【结姻】，与 {target.name} 各回复 1 点体力")
        return True

    def _handle_xiaoji(self, player: 'Player', engine: 'GameEngine', **kwargs) -> bool:
        """
        枭姬：失去装备区的牌后摸两张牌
        """
        cards = engine.deck.draw(2)
        player.draw_cards(cards)
        engine.log_event("skill", f"{player.name} 发动【枭姬】，摸了 2 张牌")
        return True


# 技能效果描述
SKILL_DESCRIPTIONS = {
    "rende": {
        "name": "仁德",
        "description": "出牌阶段，你可以将任意数量的手牌交给其他角色。每回合你以此法给出第二张牌时，回复1点体力。"
    },
    "jijiang": {
        "name": "激将",
        "description": "主公技。当你需要使用或打出【杀】时，你可以令其他蜀势力角色选择是否打出一张【杀】。"
    },
    "jianxiong": {
        "name": "奸雄",
        "description": "当你受到伤害后，你可以获得造成伤害的牌。"
    },
    "hujia": {
        "name": "护驾",
        "description": "主公技。当你需要使用或打出【闪】时，你可以令其他魏势力角色选择是否打出一张【闪】。"
    },
    "zhiheng": {
        "name": "制衡",
        "description": "出牌阶段限一次，你可以弃置任意数量的牌，然后摸等量的牌。"
    },
    "jiuyuan": {
        "name": "救援",
        "description": "主公技。锁定技。其他吴势力角色对你使用【桃】时，你额外回复1点体力。"
    },
    "wusheng": {
        "name": "武圣",
        "description": "你可以将一张红色牌当【杀】使用或打出。"
    },
    "paoxiao": {
        "name": "咆哮",
        "description": "锁定技。出牌阶段，你使用【杀】无次数限制。"
    },
    "guanxing": {
        "name": "观星",
        "description": "准备阶段，你可以观看牌堆顶的X张牌（X为存活角色数且至多为5），然后将这些牌以任意顺序放置于牌堆顶或牌堆底。"
    },
    "kongcheng": {
        "name": "空城",
        "description": "锁定技。若你没有手牌，你不是【杀】和【决斗】的合法目标。"
    },
    "yingzi": {
        "name": "英姿",
        "description": "摸牌阶段，你可以多摸一张牌。"
    },
    "fanjian": {
        "name": "反间",
        "description": "出牌阶段限一次，你可以选择一名其他角色并展示一张手牌，令其选择一种花色后获得此牌。若此牌花色与其所选花色不同，你对其造成1点伤害。"
    },
    "wushuang": {
        "name": "无双",
        "description": "锁定技。你使用【杀】指定目标后，目标角色需使用两张【闪】才能抵消此【杀】；你使用【决斗】指定目标后，或成为【决斗】的目标后，对方每次需打出两张【杀】。"
    }
}
