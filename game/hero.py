# -*- coding: utf-8 -*-
"""
武将系统模块
定义武将类、技能类和势力
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
import json
from pathlib import Path

if TYPE_CHECKING:
    from .player import Player
    from .engine import GameEngine


class Kingdom(Enum):
    """势力枚举"""
    WEI = "wei"   # 魏
    SHU = "shu"   # 蜀
    WU = "wu"     # 吴
    QUN = "qun"   # 群
    
    @property
    def chinese_name(self) -> str:
        """获取中文名称"""
        names = {
            Kingdom.WEI: "魏",
            Kingdom.SHU: "蜀",
            Kingdom.WU: "吴",
            Kingdom.QUN: "群"
        }
        return names.get(self, "?")
    
    @property
    def color(self) -> str:
        """获取势力颜色（用于终端显示）"""
        colors = {
            Kingdom.WEI: "blue",
            Kingdom.SHU: "red",
            Kingdom.WU: "green",
            Kingdom.QUN: "yellow"
        }
        return colors.get(self, "white")


class SkillType(Enum):
    """技能类型枚举"""
    PASSIVE = "passive"     # 被动技能（锁定技）
    ACTIVE = "active"       # 主动技能
    TRIGGER = "trigger"     # 触发技能
    TRANSFORM = "transform" # 转化技能


class SkillTiming(Enum):
    """技能触发时机枚举"""
    PREPARE = "prepare"         # 准备阶段
    JUDGE = "judge"             # 判定阶段
    DRAW = "draw"               # 摸牌阶段
    PLAY = "play"               # 出牌阶段
    DISCARD = "discard"         # 弃牌阶段
    END = "end"                 # 结束阶段
    BEFORE_ATTACK = "before_attack"     # 使用杀前
    AFTER_ATTACK = "after_attack"       # 使用杀后
    BEFORE_DAMAGED = "before_damaged"   # 受到伤害前
    AFTER_DAMAGED = "after_damaged"     # 受到伤害后
    BEFORE_DYING = "before_dying"       # 濒死前
    ON_DEATH = "on_death"               # 死亡时
    RESPOND = "respond"                 # 响应时（需要出闪/杀时）


@dataclass
class Skill:
    """
    技能类
    
    Attributes:
        id: 技能唯一标识符
        name: 技能名称
        description: 技能描述
        skill_type: 技能类型
        timing: 触发时机
        is_lord_skill: 是否为主公技
        is_compulsory: 是否为锁定技
        limit_per_turn: 每回合使用次数限制（0表示无限制）
        target_card: 目标卡牌（用于转化技）
    """
    id: str
    name: str
    description: str
    skill_type: SkillType
    timing: Optional[SkillTiming] = None
    is_lord_skill: bool = False
    is_compulsory: bool = False
    limit_per_turn: int = 0
    target_card: Optional[str] = None
    
    # 运行时状态
    used_count: int = field(default=0, repr=False)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.skill_type, str):
            self.skill_type = SkillType(self.skill_type)
        if isinstance(self.timing, str):
            self.timing = SkillTiming(self.timing)
    
    def can_use(self, player: 'Player', game_engine: 'GameEngine') -> bool:
        """
        检查技能是否可以使用
        
        Args:
            player: 使用技能的玩家
            game_engine: 游戏引擎
            
        Returns:
            是否可以使用
        """
        # 检查使用次数限制
        if self.limit_per_turn > 0 and self.used_count >= self.limit_per_turn:
            return False
        
        # 主公技检查
        if self.is_lord_skill and player.identity.value != "lord":
            return False
        
        return True
    
    def reset_turn(self) -> None:
        """重置回合状态"""
        self.used_count = 0
    
    def use(self) -> None:
        """使用技能（增加使用次数）"""
        self.used_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.skill_type.value,
            "timing": self.timing.value if self.timing else None,
            "is_lord_skill": self.is_lord_skill,
            "is_compulsory": self.is_compulsory,
            "limit_per_turn": self.limit_per_turn,
            "target_card": self.target_card
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """从字典创建技能"""
        timing = None
        if data.get("timing"):
            timing = SkillTiming(data["timing"])
        elif data.get("phase"):
            # 兼容phase字段
            timing = SkillTiming(data["phase"])
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            skill_type=SkillType(data["type"]),
            timing=timing,
            is_lord_skill=data.get("is_lord_skill", False),
            is_compulsory=data.get("is_compulsory", False),
            limit_per_turn=data.get("limit_per_turn", 0),
            target_card=data.get("target_card")
        )
    
    def __str__(self) -> str:
        prefix = "[锁定技] " if self.is_compulsory else ""
        lord = "[主公技] " if self.is_lord_skill else ""
        return f"{lord}{prefix}{self.name}"
    
    def __repr__(self) -> str:
        return f"Skill({self.id}, {self.name})"


@dataclass
class Hero:
    """
    武将类
    
    Attributes:
        id: 武将唯一标识符
        name: 武将名称
        kingdom: 所属势力
        max_hp: 最大体力值
        gender: 性别
        title: 称号
        skills: 技能列表
    """
    id: str
    name: str
    kingdom: Kingdom
    max_hp: int
    gender: str
    title: str
    skills: List[Skill] = field(default_factory=list)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.kingdom, str):
            self.kingdom = Kingdom(self.kingdom)
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """
        根据ID获取技能
        
        Args:
            skill_id: 技能ID
            
        Returns:
            技能对象，如果不存在返回None
        """
        for skill in self.skills:
            if skill.id == skill_id:
                return skill
        return None
    
    def get_skill_by_name(self, skill_name: str) -> Optional[Skill]:
        """
        根据名称获取技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            技能对象，如果不存在返回None
        """
        for skill in self.skills:
            if skill.name == skill_name:
                return skill
        return None
    
    def has_skill(self, skill_id: str) -> bool:
        """检查是否拥有指定技能"""
        return self.get_skill(skill_id) is not None
    
    def reset_skills(self) -> None:
        """重置所有技能的回合状态"""
        for skill in self.skills:
            skill.reset_turn()
    
    @property
    def skill_names(self) -> List[str]:
        """获取所有技能名称列表"""
        return [skill.name for skill in self.skills]
    
    @property
    def kingdom_name(self) -> str:
        """获取势力中文名"""
        return self.kingdom.chinese_name
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "kingdom": self.kingdom.value,
            "max_hp": self.max_hp,
            "gender": self.gender,
            "title": self.title,
            "skills": [skill.to_dict() for skill in self.skills]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Hero':
        """从字典创建武将"""
        skills = [Skill.from_dict(s) for s in data.get("skills", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            kingdom=Kingdom(data["kingdom"]),
            max_hp=data["max_hp"],
            gender=data["gender"],
            title=data.get("title", ""),
            skills=skills
        )
    
    def __str__(self) -> str:
        skills_str = "、".join(self.skill_names)
        return f"{self.name}[{self.kingdom_name}] HP:{self.max_hp} 技能:{skills_str}"
    
    def __repr__(self) -> str:
        return f"Hero({self.id}, {self.name})"


class HeroRepository:
    """
    武将仓库类
    管理所有武将数据
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        初始化武将仓库
        
        Args:
            data_path: 武将数据文件路径
        """
        self._heroes: Dict[str, Hero] = {}
        
        if data_path:
            self.load_heroes(data_path)
    
    def load_heroes(self, data_path: str) -> None:
        """
        从JSON文件加载武将数据
        
        Args:
            data_path: JSON文件路径
        """
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"武将数据文件不存在: {data_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._heroes.clear()
        
        for hero_data in data.get("heroes", []):
            hero = Hero.from_dict(hero_data)
            self._heroes[hero.id] = hero
    
    def get_hero(self, hero_id: str) -> Optional[Hero]:
        """
        获取武将
        
        Args:
            hero_id: 武将ID
            
        Returns:
            武将对象，如果不存在返回None
        """
        return self._heroes.get(hero_id)
    
    def get_hero_by_name(self, name: str) -> Optional[Hero]:
        """
        根据名称获取武将
        
        Args:
            name: 武将名称
            
        Returns:
            武将对象，如果不存在返回None
        """
        for hero in self._heroes.values():
            if hero.name == name:
                return hero
        return None
    
    def get_all_heroes(self) -> List[Hero]:
        """获取所有武将列表"""
        return list(self._heroes.values())
    
    def get_heroes_by_kingdom(self, kingdom: Kingdom) -> List[Hero]:
        """
        获取指定势力的所有武将
        
        Args:
            kingdom: 势力
            
        Returns:
            武将列表
        """
        return [h for h in self._heroes.values() if h.kingdom == kingdom]
    
    def get_random_heroes(self, count: int) -> List[Hero]:
        """
        随机获取指定数量的武将
        
        Args:
            count: 数量
            
        Returns:
            武将列表
        """
        import random
        all_heroes = self.get_all_heroes()
        return random.sample(all_heroes, min(count, len(all_heroes)))
    
    @property
    def hero_count(self) -> int:
        """获取武将总数"""
        return len(self._heroes)
    
    def __len__(self) -> int:
        return self.hero_count
    
    def __iter__(self):
        return iter(self._heroes.values())
    
    def __contains__(self, hero_id: str) -> bool:
        return hero_id in self._heroes
