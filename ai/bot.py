# -*- coding: utf-8 -*-
"""
AI机器人模块
实现三种难度的AI决策逻辑
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, TYPE_CHECKING
import random

# 导入运行时需要的类
from game.player import Identity
from game.card import CardType

if TYPE_CHECKING:
    from game.player import Player
    from game.card import Card
    from game.engine import GameEngine


class AIDifficulty(Enum):
    """AI难度枚举"""
    EASY = "easy"       # 简单：随机出牌
    NORMAL = "normal"   # 普通：基础策略
    HARD = "hard"       # 困难：深度策略 + 嘲讽值系统


class AIBot:
    """
    AI机器人类
    负责为AI玩家做出决策
    """
    
    def __init__(self, player: 'Player', difficulty: AIDifficulty = AIDifficulty.NORMAL):
        """
        初始化AI机器人
        
        Args:
            player: 关联的玩家
            difficulty: AI难度
        """
        self.player = player
        self.difficulty = difficulty
        
        # 嘲讽值系统（仅困难模式使用）
        self.threat_values: Dict[int, float] = {}
        
        # 身份推测（基于行为）
        self.identity_guess: Dict[int, 'Identity'] = {}
    
    def play_phase(self, player: 'Player', engine: 'GameEngine') -> None:
        """
        出牌阶段决策
        
        Args:
            player: 当前玩家
            engine: 游戏引擎
        """
        if self.difficulty == AIDifficulty.EASY:
            self._easy_play_phase(player, engine)
        elif self.difficulty == AIDifficulty.NORMAL:
            self._normal_play_phase(player, engine)
        else:
            self._hard_play_phase(player, engine)
    
    def choose_discard(self, player: 'Player', count: int, 
                       engine: 'GameEngine') -> List['Card']:
        """
        选择弃牌
        
        Args:
            player: 玩家
            count: 需要弃置的数量
            engine: 游戏引擎
            
        Returns:
            要弃置的卡牌列表
        """
        if not player.hand:
            return []
        
        if self.difficulty == AIDifficulty.EASY:
            return self._easy_discard(player, count)
        else:
            return self._smart_discard(player, count)
    
    def should_use_qinglong(self, player: 'Player', target: 'Player', 
                           engine: 'GameEngine') -> bool:
        """
        决定是否使用青龙偃月刀继续攻击
        
        Args:
            player: 攻击者
            target: 目标
            engine: 游戏引擎
            
        Returns:
            是否继续攻击
        """
        # 有杀且是敌人就继续
        sha_count = len(player.get_cards_by_name("杀"))
        if sha_count > 1:
            return self._is_enemy(player, target)
        return False
    
    # ==================== 简单AI ====================
    
    def _easy_play_phase(self, player: 'Player', engine: 'GameEngine') -> None:
        """简单模式：随机出牌"""
        max_actions = 10  # 防止无限循环
        actions = 0
        
        while actions < max_actions:
            actions += 1
            
            if not player.hand:
                break
            
            # 随机选择一张牌
            card = random.choice(player.hand)
            
            # 尝试使用
            if self._try_use_card_easy(player, card, engine):
                continue
            
            # 50%概率结束回合
            if random.random() < 0.5:
                break
    
    def _try_use_card_easy(self, player: 'Player', card: 'Card', 
                           engine: 'GameEngine') -> bool:
        """简单模式：尝试使用卡牌"""
        # 装备牌直接使用
        if card.card_type == CardType.EQUIPMENT:
            return engine.use_card(player, card)
        
        # 自用锦囊
        if card.name in ["无中生有", "桃园结义"]:
            return engine.use_card(player, card)
        
        # 桃（需要时使用）
        if card.name == "桃":
            if player.hp < player.max_hp:
                return engine.use_card(player, card)
            return False
        
        # 需要目标的牌
        if card.name == "杀":
            if player.can_use_sha():
                targets = engine.get_targets_in_range(player)
                if targets:
                    target = random.choice(targets)
                    return engine.use_card(player, card, [target])
        
        elif card.name in ["决斗", "过河拆桥"]:
            others = engine.get_other_players(player)
            valid_targets = [t for t in others if t.has_any_card() or card.name != "过河拆桥"]
            if valid_targets:
                target = random.choice(valid_targets)
                return engine.use_card(player, card, [target])
        
        elif card.name == "顺手牵羊":
            others = engine.get_other_players(player)
            valid_targets = [t for t in others 
                           if engine.calculate_distance(player, t) <= 1 and t.has_any_card()]
            if valid_targets:
                target = random.choice(valid_targets)
                return engine.use_card(player, card, [target])
        
        elif card.name in ["南蛮入侵", "万箭齐发"]:
            return engine.use_card(player, card)
        
        return False
    
    def _easy_discard(self, player: 'Player', count: int) -> List['Card']:
        """简单模式：随机弃牌"""
        return random.sample(player.hand, min(count, len(player.hand)))
    
    # ==================== 普通AI ====================
    
    def _normal_play_phase(self, player: 'Player', engine: 'GameEngine') -> None:
        """普通模式：基础策略"""
        # 优先级：装备 > 无中生有 > 杀 > 其他锦囊 > 技能
        
        played = True
        while played:
            played = False
            
            # 1. 使用装备
            for card in list(player.hand):
                if card.card_type.value == "equipment":
                    if engine.use_card(player, card):
                        played = True
                        break
            
            if played:
                continue
            
            # 2. 使用无中生有
            wuzhong = player.get_cards_by_name("无中生有")
            if wuzhong:
                if engine.use_card(player, wuzhong[0]):
                    played = True
                    continue
            
            # 3. 使用桃回复体力
            if player.hp < player.max_hp - 1:  # 保留一些桃用于濒死
                tao = player.get_cards_by_name("桃")
                if tao and player.hp <= 2:
                    if engine.use_card(player, tao[0]):
                        played = True
                        continue
            
            # 4. 使用杀
            if player.can_use_sha():
                sha = player.get_cards_by_name("杀")
                # 武圣可以用红牌当杀
                if player.has_skill("wusheng") and not sha:
                    sha = player.get_red_cards()
                
                if sha:
                    targets = self._get_attack_targets(player, engine)
                    if targets:
                        target = self._choose_best_target(player, targets, engine)
                        if engine.use_card(player, sha[0], [target]):
                            played = True
                            continue
            
            # 5. 使用控制锦囊
            for card in list(player.hand):
                if card.name == "过河拆桥":
                    target = self._choose_dismount_target(player, engine)
                    if target:
                        if engine.use_card(player, card, [target]):
                            played = True
                            break
                
                elif card.name == "顺手牵羊":
                    target = self._choose_steal_target(player, engine)
                    if target:
                        if engine.use_card(player, card, [target]):
                            played = True
                            break
                
                elif card.name == "决斗":
                    target = self._choose_duel_target(player, engine)
                    if target:
                        if engine.use_card(player, card, [target]):
                            played = True
                            break
            
            if played:
                continue
            
            # 6. 使用AOE锦囊（如果大部分目标是敌人）
            for card in list(player.hand):
                if card.name in ["南蛮入侵", "万箭齐发"]:
                    if self._should_use_aoe(player, engine):
                        if engine.use_card(player, card):
                            played = True
                            break
            
            if played:
                continue
            
            # 7. 使用主动技能
            if engine.skill_system:
                usable_skills = engine.skill_system.get_usable_skills(player)
                for skill_id in usable_skills:
                    if self._should_use_skill(player, skill_id, engine):
                        self._use_skill_with_ai(player, skill_id, engine)
                        played = True
                        break
            
            # 无法行动则结束
            if not played:
                break
    
    def _get_attack_targets(self, player: 'Player', engine: 'GameEngine') -> List['Player']:
        """获取可攻击的敌方目标"""
        targets = engine.get_targets_in_range(player)
        return [t for t in targets if self._is_enemy(player, t)]
    
    def _choose_best_target(self, player: 'Player', targets: List['Player'], 
                           engine: 'GameEngine') -> 'Player':
        """选择最佳攻击目标"""
        if not targets:
            return targets[0] if targets else None
        
        # 优先攻击体力低的敌人
        targets.sort(key=lambda t: (t.hp, t.hand_count))
        return targets[0]
    
    def _choose_dismount_target(self, player: 'Player', 
                                engine: 'GameEngine') -> Optional['Player']:
        """选择过河拆桥的目标"""
        others = engine.get_other_players(player)
        enemies = [t for t in others if self._is_enemy(player, t) and t.has_any_card()]
        
        if enemies:
            # 优先选择有装备的
            with_equip = [t for t in enemies if t.equipment.has_equipment()]
            if with_equip:
                return random.choice(with_equip)
            return random.choice(enemies)
        return None
    
    def _choose_steal_target(self, player: 'Player', 
                             engine: 'GameEngine') -> Optional['Player']:
        """选择顺手牵羊的目标"""
        others = engine.get_other_players(player)
        valid = [t for t in others 
                if engine.calculate_distance(player, t) <= 1 and t.has_any_card()]
        enemies = [t for t in valid if self._is_enemy(player, t)]
        
        if enemies:
            return random.choice(enemies)
        return None
    
    def _choose_duel_target(self, player: 'Player', 
                           engine: 'GameEngine') -> Optional['Player']:
        """选择决斗的目标"""
        others = engine.get_other_players(player)
        enemies = [t for t in others if self._is_enemy(player, t)]
        
        if enemies:
            # 选择手牌少的（可能没有杀）
            enemies.sort(key=lambda t: t.hand_count)
            return enemies[0]
        return None
    
    def _should_use_aoe(self, player: 'Player', engine: 'GameEngine') -> bool:
        """判断是否应该使用AOE"""
        others = engine.get_other_players(player)
        enemies = [t for t in others if self._is_enemy(player, t)]
        friends = [t for t in others if not self._is_enemy(player, t)]
        
        # 敌人数量大于友军时使用
        return len(enemies) > len(friends)
    
    def _is_enemy(self, player: 'Player', target: 'Player') -> bool:
        """判断目标是否为敌人"""
        my_identity = player.identity
        target_identity = target.identity
        
        # 身份已知的情况
        if my_identity == Identity.LORD or my_identity == Identity.LOYALIST:
            return target_identity in [Identity.REBEL, Identity.SPY]
        elif my_identity == Identity.REBEL:
            return target_identity in [Identity.LORD, Identity.LOYALIST]
        elif my_identity == Identity.SPY:
            # 内奸策略：前期帮助主公，后期杀主公
            alive_count = len([p for p in [player, target] if p.is_alive])
            if alive_count <= 2:
                return True  # 最后单挑阶段
            return target_identity == Identity.REBEL  # 先帮助清理反贼
        
        return False
    
    def _should_use_skill(self, player: 'Player', skill_id: str, 
                          engine: 'GameEngine') -> bool:
        """判断是否应该使用技能"""
        if skill_id == "zhiheng":
            # 制衡：手牌中有闲置的牌时使用
            useless_cards = self._count_useless_cards(player, engine)
            return useless_cards >= 2
        
        elif skill_id == "rende":
            # 仁德：有多余的牌且有需要帮助的友军
            if player.hand_count > 4:
                friends = self._get_friends(player, engine)
                return len(friends) > 0
        
        elif skill_id == "fanjian":
            # 反间：有手牌就对敌人使用
            enemies = [p for p in engine.get_other_players(player) if self._is_enemy(player, p)]
            return player.hand_count > 0 and len(enemies) > 0
        
        return False
    
    def _count_useless_cards(self, player: 'Player', engine: 'GameEngine') -> int:
        """计算无用卡牌数量"""
        useless = 0
        for card in player.hand:
            if card.name == "闪":
                useless += max(0, len(player.get_cards_by_name("闪")) - 2)
            elif card.name == "杀":
                if not player.can_use_sha():
                    useless += 1
        return useless
    
    def _get_friends(self, player: 'Player', engine: 'GameEngine') -> List['Player']:
        """获取友方玩家"""
        return [p for p in engine.get_other_players(player) if not self._is_enemy(player, p)]
    
    def _use_skill_with_ai(self, player: 'Player', skill_id: str, 
                           engine: 'GameEngine') -> bool:
        """AI使用技能"""
        if not engine.skill_system:
            return False
        
        if skill_id == "zhiheng":
            # 选择要弃置的牌
            cards_to_discard = self._smart_discard(player, min(3, player.hand_count))
            return engine.skill_system.use_skill(skill_id, player, cards=cards_to_discard)
        
        elif skill_id == "rende":
            # 选择牌和目标
            friends = self._get_friends(player, engine)
            if friends and player.hand_count > 2:
                target = random.choice(friends)
                cards = [player.hand[0]]  # 给一张牌
                return engine.skill_system.use_skill(skill_id, player, 
                                                     targets=[target], cards=cards)
        
        elif skill_id == "fanjian":
            enemies = [p for p in engine.get_other_players(player) if self._is_enemy(player, p)]
            if enemies and player.hand:
                target = random.choice(enemies)
                card = random.choice(player.hand)
                return engine.skill_system.use_skill(skill_id, player,
                                                     targets=[target], cards=[card])
        
        return False
    
    def _smart_discard(self, player: 'Player', count: int) -> List['Card']:
        """智能弃牌"""
        if not player.hand:
            return []
        
        # 卡牌优先级（低的先弃）
        def card_priority(card: 'Card') -> int:
            if card.name == "桃":
                return 100  # 最高优先级保留
            elif card.name == "无懈可击":
                return 90
            elif card.name == "闪":
                return 70
            elif card.name == "杀":
                # 如果不能用杀了，优先弃掉
                if not player.can_use_sha():
                    return 20
                return 60
            elif card.name == "无中生有":
                return 80
            elif card.card_type.value == "equipment":
                return 30  # 装备优先级低（应该已经装上了）
            else:
                return 50
        
        sorted_cards = sorted(player.hand, key=card_priority)
        return sorted_cards[:count]
    
    # ==================== 困难AI ====================
    
    def _hard_play_phase(self, player: 'Player', engine: 'GameEngine') -> None:
        """困难模式：深度策略 + 嘲讽值系统"""
        # 更新嘲讽值
        self._update_threat_values(engine)
        
        # 使用普通AI的逻辑，但在目标选择时考虑嘲讽值
        self._normal_play_phase(player, engine)
    
    def _update_threat_values(self, engine: 'GameEngine') -> None:
        """更新嘲讽值"""
        for p in engine.players:
            if p.id == self.player.id:
                continue
            
            threat = 0.0
            
            # 基础威胁值基于体力
            threat += (5 - p.hp) * 10
            
            # 手牌数量影响威胁
            threat += p.hand_count * 5
            
            # 装备影响威胁
            if p.equipment.weapon:
                threat += 15
            if p.equipment.armor:
                threat += 10
            
            # 特定武将增加威胁
            if p.hero:
                if p.hero.id == "lvbu":  # 吕布
                    threat += 20
                elif p.hero.id == "zhugeliang":  # 诸葛亮
                    threat += 15
            
            # 身份影响
            if p.identity.value == "lord":
                threat += 30  # 主公是重点目标
            
            self.threat_values[p.id] = threat
    
    def get_highest_threat_enemy(self, player: 'Player', 
                                  engine: 'GameEngine') -> Optional['Player']:
        """获取威胁值最高的敌人"""
        enemies = [p for p in engine.get_other_players(player) if self._is_enemy(player, p)]
        
        if not enemies:
            return None
        
        enemies.sort(key=lambda p: self.threat_values.get(p.id, 0), reverse=True)
        return enemies[0]
