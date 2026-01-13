# -*- coding: utf-8 -*-
"""
玩家系统模块
定义玩家类和身份系统
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import copy

if TYPE_CHECKING:
    from .card import Card, CardSubtype
    from .hero import Hero, Skill


class Identity(Enum):
    """身份枚举"""
    LORD = "lord"           # 主公
    LOYALIST = "loyalist"   # 忠臣
    REBEL = "rebel"         # 反贼
    SPY = "spy"             # 内奸
    
    @property
    def chinese_name(self) -> str:
        """获取中文名称"""
        names = {
            Identity.LORD: "主公",
            Identity.LOYALIST: "忠臣",
            Identity.REBEL: "反贼",
            Identity.SPY: "内奸"
        }
        return names.get(self, "?")
    
    @property
    def color(self) -> str:
        """获取身份颜色"""
        colors = {
            Identity.LORD: "red",
            Identity.LOYALIST: "yellow",
            Identity.REBEL: "green",
            Identity.SPY: "blue"
        }
        return colors.get(self, "white")


class EquipmentSlot(Enum):
    """装备槽位枚举"""
    WEAPON = "weapon"           # 武器
    ARMOR = "armor"             # 防具
    HORSE_MINUS = "horse_minus" # -1马（攻击马）
    HORSE_PLUS = "horse_plus"   # +1马（防御马）


@dataclass
class Equipment:
    """
    装备区类
    管理玩家的装备
    """
    weapon: Optional['Card'] = None
    armor: Optional['Card'] = None
    horse_minus: Optional['Card'] = None  # -1马（攻击马，如赤兔）
    horse_plus: Optional['Card'] = None   # +1马（防御马，如的卢）
    
    def equip(self, card: 'Card') -> Optional['Card']:
        """
        装备一张卡牌，返回被替换的旧装备（如果有）
        
        Args:
            card: 要装备的卡牌
            
        Returns:
            被替换的旧装备，如果没有则返回None
        """
        from .card import CardSubtype
        
        old_card = None
        
        if card.subtype == CardSubtype.WEAPON:
            old_card = self.weapon
            self.weapon = card
        elif card.subtype == CardSubtype.ARMOR:
            old_card = self.armor
            self.armor = card
        elif card.subtype == CardSubtype.HORSE_MINUS:
            old_card = self.horse_minus
            self.horse_minus = card
        elif card.subtype == CardSubtype.HORSE_PLUS:
            old_card = self.horse_plus
            self.horse_plus = card
        
        return old_card
    
    def unequip(self, slot: EquipmentSlot) -> Optional['Card']:
        """
        卸下指定槽位的装备
        
        Args:
            slot: 装备槽位
            
        Returns:
            卸下的装备，如果没有则返回None
        """
        card = None
        
        if slot == EquipmentSlot.WEAPON:
            card = self.weapon
            self.weapon = None
        elif slot == EquipmentSlot.ARMOR:
            card = self.armor
            self.armor = None
        elif slot == EquipmentSlot.HORSE_MINUS:
            card = self.horse_minus
            self.horse_minus = None
        elif slot == EquipmentSlot.HORSE_PLUS:
            card = self.horse_plus
            self.horse_plus = None
        
        return card
    
    def unequip_card(self, card: 'Card') -> bool:
        """
        根据卡牌移除装备
        
        Args:
            card: 要移除的装备卡牌
            
        Returns:
            是否成功移除
        """
        if self.weapon == card:
            self.weapon = None
            return True
        elif self.armor == card:
            self.armor = None
            return True
        elif self.horse_minus == card:
            self.horse_minus = None
            return True
        elif self.horse_plus == card:
            self.horse_plus = None
            return True
        return False
    
    def get_all_cards(self) -> List['Card']:
        """获取所有装备的卡牌列表"""
        cards = []
        if self.weapon:
            cards.append(self.weapon)
        if self.armor:
            cards.append(self.armor)
        if self.horse_minus:
            cards.append(self.horse_minus)
        if self.horse_plus:
            cards.append(self.horse_plus)
        return cards
    
    def get_card_by_slot(self, slot: EquipmentSlot) -> Optional['Card']:
        """根据槽位获取装备"""
        if slot == EquipmentSlot.WEAPON:
            return self.weapon
        elif slot == EquipmentSlot.ARMOR:
            return self.armor
        elif slot == EquipmentSlot.HORSE_MINUS:
            return self.horse_minus
        elif slot == EquipmentSlot.HORSE_PLUS:
            return self.horse_plus
        return None
    
    @property
    def attack_range(self) -> int:
        """获取攻击范围（由武器决定）"""
        if self.weapon:
            return self.weapon.range
        return 1  # 默认攻击范围为1
    
    @property
    def distance_to_others(self) -> int:
        """获取到其他角色的距离修正（-1马）"""
        if self.horse_minus:
            return -1
        return 0
    
    @property
    def distance_from_others(self) -> int:
        """获取其他角色到自己的距离修正（+1马）"""
        if self.horse_plus:
            return 1
        return 0
    
    def has_equipment(self) -> bool:
        """检查是否有任何装备"""
        return any([self.weapon, self.armor, self.horse_minus, self.horse_plus])
    
    @property
    def count(self) -> int:
        """获取装备数量"""
        return len(self.get_all_cards())
    
    def __str__(self) -> str:
        parts = []
        if self.weapon:
            parts.append(f"[{self.weapon.name}]")
        if self.armor:
            parts.append(f"[{self.armor.name}]")
        if self.horse_minus:
            parts.append(f"[-1马:{self.horse_minus.name}]")
        if self.horse_plus:
            parts.append(f"[+1马:{self.horse_plus.name}]")
        return "".join(parts) if parts else "无"


@dataclass
class Player:
    """
    玩家类
    
    Attributes:
        id: 玩家ID
        name: 玩家名称
        is_ai: 是否为AI玩家
        hero: 武将
        identity: 身份
        hp: 当前体力值
        max_hp: 最大体力值
        hand: 手牌列表
        equipment: 装备区
        is_alive: 是否存活
        seat: 座位号
    """
    id: int
    name: str
    is_ai: bool = True
    hero: Optional['Hero'] = None
    identity: Identity = Identity.REBEL
    hp: int = 0
    max_hp: int = 0
    hand: List['Card'] = field(default_factory=list)
    equipment: Equipment = field(default_factory=Equipment)
    is_alive: bool = True
    seat: int = 0
    
    # 回合状态
    sha_count: int = field(default=0, repr=False)  # 本回合已使用的杀数量
    skill_used: Dict[str, int] = field(default_factory=dict, repr=False)  # 技能使用次数
    
    # 濒死状态
    is_dying: bool = field(default=False, repr=False)
    
    # 军争篇状态
    is_chained: bool = field(default=False, repr=False)  # 铁索连环状态
    is_drunk: bool = field(default=False, repr=False)    # 酒状态（下一张杀伤害+1）
    alcohol_used: bool = field(default=False, repr=False)  # 本回合是否使用过酒
    flipped: bool = field(default=False, repr=False)  # 武将牌翻面状态
    
    # 判定区（延时锦囊）
    judge_area: List['Card'] = field(default_factory=list, repr=False)
    
    # 跳过阶段标记（延时锦囊用）
    skip_play_phase: bool = field(default=False, repr=False)
    skip_draw_phase: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.identity, str):
            self.identity = Identity(self.identity)
    
    def set_hero(self, hero: 'Hero') -> None:
        """
        设置武将
        
        Args:
            hero: 武将对象
        """
        self.hero = hero
        self.max_hp = hero.max_hp
        self.hp = hero.max_hp
        
        # 主公额外加1点体力上限
        if self.identity == Identity.LORD:
            self.max_hp += 1
            self.hp += 1
    
    def draw_cards(self, cards: List['Card']) -> None:
        """
        将卡牌加入手牌
        
        Args:
            cards: 要加入的卡牌列表
        """
        self.hand.extend(cards)
    
    def remove_card(self, card: 'Card') -> bool:
        """
        从手牌中移除一张卡牌
        
        Args:
            card: 要移除的卡牌
            
        Returns:
            是否成功移除
        """
        if card in self.hand:
            self.hand.remove(card)
            return True
        return False
    
    def remove_cards(self, cards: List['Card']) -> List['Card']:
        """
        从手牌中移除多张卡牌
        
        Args:
            cards: 要移除的卡牌列表
            
        Returns:
            成功移除的卡牌列表
        """
        removed = []
        for card in cards:
            if self.remove_card(card):
                removed.append(card)
        return removed
    
    def get_card_by_index(self, index: int) -> Optional['Card']:
        """
        根据索引获取手牌
        
        Args:
            index: 索引（0开始）
            
        Returns:
            卡牌对象，如果索引无效返回None
        """
        if 0 <= index < len(self.hand):
            return self.hand[index]
        return None
    
    def has_card(self, card_name: str) -> bool:
        """
        检查手牌中是否有指定名称的牌
        
        Args:
            card_name: 卡牌名称
            
        Returns:
            是否拥有
        """
        return any(c.name == card_name for c in self.hand)
    
    def get_cards_by_name(self, card_name: str) -> List['Card']:
        """
        获取手牌中所有指定名称的牌
        
        Args:
            card_name: 卡牌名称
            
        Returns:
            卡牌列表
        """
        return [c for c in self.hand if c.name == card_name]
    
    def get_red_cards(self) -> List['Card']:
        """获取所有红色手牌"""
        return [c for c in self.hand if c.is_red]
    
    def equip_card(self, card: 'Card') -> Optional['Card']:
        """
        装备一张卡牌
        
        Args:
            card: 要装备的卡牌
            
        Returns:
            被替换的旧装备
        """
        return self.equipment.equip(card)
    
    def take_damage(self, damage: int, source: Optional['Player'] = None) -> None:
        """
        受到伤害
        
        Args:
            damage: 伤害值
            source: 伤害来源
        """
        self.hp -= damage
        if self.hp <= 0:
            self.is_dying = True
    
    def heal(self, amount: int) -> int:
        """
        回复体力
        
        Args:
            amount: 回复量
            
        Returns:
            实际回复量
        """
        old_hp = self.hp
        self.hp = min(self.hp + amount, self.max_hp)
        actual_heal = self.hp - old_hp
        
        if self.hp > 0:
            self.is_dying = False
        
        return actual_heal
    
    def die(self) -> None:
        """死亡处理"""
        self.is_alive = False
        self.is_dying = False
    
    def reset_turn(self) -> None:
        """重置回合状态"""
        self.sha_count = 0
        self.skill_used.clear()
        self.is_drunk = False
        self.alcohol_used = False
        self.skip_play_phase = False
        self.skip_draw_phase = False
        if self.hero:
            self.hero.reset_skills()
    
    def toggle_chain(self) -> None:
        """切换铁索连环状态"""
        self.is_chained = not self.is_chained
    
    def break_chain(self) -> None:
        """解除铁索连环状态"""
        self.is_chained = False
    
    def toggle_flip(self) -> None:
        """翻转武将牌（据守、微势等技能用）"""
        self.flipped = not self.flipped
    
    def use_alcohol(self) -> bool:
        """
        使用酒
        
        Returns:
            是否成功使用
        """
        if not self.alcohol_used:
            self.is_drunk = True
            self.alcohol_used = True
            return True
        return False
    
    def consume_drunk(self) -> bool:
        """
        消耗酒状态（使用杀时调用）
        
        Returns:
            是否有酒加成
        """
        if self.is_drunk:
            self.is_drunk = False
            return True
        return False
    
    def can_use_sha(self) -> bool:
        """检查是否可以使用杀"""
        # 检查诸葛连弩效果
        if self.equipment.weapon and self.equipment.weapon.name == "诸葛连弩":
            return True
        
        # 检查咆哮技能
        if self.hero and self.hero.has_skill("paoxiao"):
            return True
        
        # 正常情况每回合只能使用一次杀
        return self.sha_count < 1
    
    def use_sha(self) -> None:
        """使用杀（增加计数）"""
        self.sha_count += 1
    
    @property
    def hand_limit(self) -> int:
        """获取手牌上限"""
        return max(0, self.hp)
    
    @property
    def hand_count(self) -> int:
        """获取手牌数量"""
        return len(self.hand)
    
    @property
    def need_discard(self) -> int:
        """获取需要弃置的牌数"""
        return max(0, self.hand_count - self.hand_limit)
    
    @property
    def hp_display(self) -> str:
        """获取体力值显示"""
        hearts = "♥" * self.hp + "○" * (self.max_hp - self.hp)
        return hearts
    
    @property
    def identity_display(self) -> str:
        """获取身份显示"""
        if self.identity == Identity.LORD:
            return self.identity.chinese_name
        return "?"  # 其他身份不公开
    
    def get_all_cards(self) -> List['Card']:
        """获取玩家区域内的所有牌（手牌+装备）"""
        all_cards = list(self.hand)
        all_cards.extend(self.equipment.get_all_cards())
        return all_cards
    
    def has_any_card(self) -> bool:
        """检查是否有任何牌（手牌或装备）"""
        return len(self.hand) > 0 or self.equipment.has_equipment()
    
    def get_skill(self, skill_id: str) -> Optional['Skill']:
        """获取指定技能"""
        if self.hero:
            return self.hero.get_skill(skill_id)
        return None
    
    def has_skill(self, skill_id: str) -> bool:
        """检查是否拥有指定技能"""
        if self.hero:
            return self.hero.has_skill(skill_id)
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于调试）"""
        return {
            "id": self.id,
            "name": self.name,
            "is_ai": self.is_ai,
            "hero": self.hero.name if self.hero else None,
            "identity": self.identity.value,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "hand_count": self.hand_count,
            "equipment": str(self.equipment),
            "is_alive": self.is_alive,
            "seat": self.seat
        }
    
    def __str__(self) -> str:
        hero_name = self.hero.name if self.hero else "未选择武将"
        return f"[{self.name}] {hero_name} {self.hp_display} 手牌:{self.hand_count}"
    
    def __repr__(self) -> str:
        return f"Player({self.id}, {self.name})"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Player):
            return self.id == other.id
        return False
    
    def __hash__(self) -> int:
        return hash(self.id)
