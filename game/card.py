"""卡牌系统模块
定义卡牌类型、花色、卡牌类和牌堆
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .engine import GameEngine
    from .player import Player


class CardType(Enum):
    """卡牌类型枚举"""

    BASIC = "basic"  # 基本牌
    TRICK = "trick"  # 锦囊牌
    EQUIPMENT = "equipment"  # 装备牌


class CardSubtype(Enum):
    """卡牌子类型枚举"""

    # 基本牌子类型
    ATTACK = "attack"  # 杀
    FIRE_ATTACK = "fire_attack"  # 火杀
    THUNDER_ATTACK = "thunder_attack"  # 雷杀
    DODGE = "dodge"  # 闪
    HEAL = "heal"  # 桃
    ALCOHOL = "alcohol"  # 酒

    # 锦囊牌子类型
    SINGLE_TARGET = "single_target"  # 单体锦囊
    AOE = "aoe"  # 范围锦囊（AOE）
    SELF = "self"  # 自用锦囊
    ALL = "all"  # 全体锦囊
    COUNTER = "counter"  # 反制锦囊
    DELAY = "delay"  # 延时锦囊
    CHAIN = "chain"  # 连环锦囊（铁索连环）

    # 装备牌子类型
    WEAPON = "weapon"  # 武器
    ARMOR = "armor"  # 防具
    TREASURE = "treasure"  # 宝物
    HORSE_PLUS = "horse_plus"  # +1马（防御马）
    HORSE_MINUS = "horse_minus"  # -1马（攻击马）


class DamageType(Enum):
    """伤害类型枚举 (军争篇)"""

    NORMAL = "normal"  # 普通伤害
    FIRE = "fire"  # 火焰伤害
    THUNDER = "thunder"  # 雷电伤害
    LOST_HP = "lost_hp"  # 体力流失（不可传导）


class CardSuit(Enum):
    """卡牌花色枚举"""

    SPADE = "spade"  # 黑桃 ♠
    HEART = "heart"  # 红心 ♥
    CLUB = "club"  # 梅花 ♣
    DIAMOND = "diamond"  # 方块 ♦

    @property
    def symbol(self) -> str:
        """获取花色符号"""
        symbols = {
            CardSuit.SPADE: "♠",
            CardSuit.HEART: "♥",
            CardSuit.CLUB: "♣",
            CardSuit.DIAMOND: "♦",
        }
        return symbols.get(self, "?")

    @property
    def is_red(self) -> bool:
        """是否为红色花色"""
        return self in (CardSuit.HEART, CardSuit.DIAMOND)

    @property
    def is_black(self) -> bool:
        """是否为黑色花色"""
        return self in (CardSuit.SPADE, CardSuit.CLUB)


@dataclass(slots=True)
class Card:
    """卡牌类

    Attributes:
        id: 卡牌唯一标识符
        name: 卡牌名称
        card_type: 卡牌类型（基本牌/锦囊牌/装备牌）
        subtype: 卡牌子类型
        suit: 花色
        number: 点数（1-13，A=1, J=11, Q=12, K=13）
        description: 卡牌描述
        range: 攻击范围（仅武器有效）
        distance_modifier: 距离修正（仅坐骑有效）
    """

    id: str
    name: str
    card_type: CardType
    subtype: CardSubtype
    suit: CardSuit
    number: int
    description: str = ""
    range: int = 1
    distance_modifier: int = 0

    def __post_init__(self):
        """初始化后处理"""
        # 转换字符串类型为枚举类型
        if isinstance(self.card_type, str):
            self.card_type = CardType(self.card_type)
        if isinstance(self.subtype, str):
            self.subtype = CardSubtype(self.subtype)
        if isinstance(self.suit, str):
            self.suit = CardSuit(self.suit)

    @property
    def number_str(self) -> str:
        """获取点数字符串表示"""
        number_map = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return number_map.get(self.number, str(self.number))

    @property
    def suit_symbol(self) -> str:
        """获取花色符号"""
        return self.suit.symbol

    @property
    def is_red(self) -> bool:
        """是否为红色牌"""
        return self.suit.is_red

    @property
    def is_black(self) -> bool:
        """是否为黑色牌"""
        return self.suit.is_black

    @property
    def display_name(self) -> str:
        """获取显示名称（包含花色和点数）"""
        return f"{self.name}{self.suit_symbol}{self.number_str}"

    @property
    def short_name(self) -> str:
        """获取短名称"""
        return f"{self.name}"

    def is_type(self, card_type: CardType) -> bool:
        """检查是否为指定类型"""
        return self.card_type == card_type

    def is_subtype(self, subtype: CardSubtype) -> bool:
        """检查是否为指定子类型"""
        return self.subtype == subtype

    def can_target(self, user: Player, target: Player, game_engine: GameEngine) -> bool:
        """检查是否可以对目标使用此牌

        Args:
            user: 使用者
            target: 目标
            game_engine: 游戏引擎

        Returns:
            是否可以使用
        """
        # 基本检查：不能对自己使用杀
        if self.name == CardName.SHA and user == target:
            return False

        # 锦囊牌检查
        if self.name in [CardName.JUEDOU, CardName.GUOHE]:
            if user == target:
                return False

        # 顺手牵羊需要距离检查
        if self.name == CardName.SHUNSHOU:
            if user == target:
                return False
            distance = game_engine.calculate_distance(user, target)
            if distance > 1:
                return False

        # 检查目标是否存活
        if not target.is_alive:
            return False

        return True

    def __str__(self) -> str:
        return self.display_name

    def __repr__(self) -> str:
        return f"Card({self.id}, {self.display_name})"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.card_type.value,
            "subtype": self.subtype.value,
            "suit": self.suit.value,
            "number": self.number,
            "description": self.description,
            "range": self.range,
            "distance_modifier": self.distance_modifier,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Card:
        """从字典创建卡牌"""
        return cls(
            id=data["id"],
            name=data["name"],
            card_type=CardType(data["type"]),
            subtype=CardSubtype(data["subtype"]),
            suit=CardSuit(data["suit"]),
            number=data["number"],
            description=data.get("description", ""),
            range=data.get("range", 1),
            distance_modifier=data.get("distance_modifier", 0),
        )


class Deck:
    """牌堆类
    管理游戏中的牌堆和弃牌堆
    """

    def __init__(self, data_path: str | None = None):
        """初始化牌堆

        Args:
            data_path: 卡牌数据文件路径
        """
        self.draw_pile: list[Card] = []  # 摸牌堆
        self.discard_pile: list[Card] = []  # 弃牌堆
        self._all_cards: list[Card] = []  # 所有卡牌副本

        if data_path:
            self.load_cards(data_path)

    def load_cards(self, data_path: str) -> None:
        """从JSON文件加载卡牌数据

        Args:
            data_path: JSON文件路径
        """
        path = Path(data_path)
        if not path.exists():
            raise FileNotFoundError(f"卡牌数据文件不存在: {data_path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self._all_cards.clear()

        # 加载基本牌
        for card_data in data.get("basic_cards", []):
            card = Card(
                id=card_data["id"],
                name=card_data["name"],
                card_type=CardType(card_data["type"]),
                subtype=CardSubtype(card_data["subtype"]),
                suit=CardSuit(card_data["suit"]),
                number=card_data["number"],
                description=card_data.get("description", ""),
            )
            count = card_data.get("count", 1)
            for _ in range(count):
                self._all_cards.append(card)

        # 加载锦囊牌
        for card_data in data.get("trick_cards", []):
            card = Card(
                id=card_data["id"],
                name=card_data["name"],
                card_type=CardType(card_data["type"]),
                subtype=CardSubtype(card_data["subtype"]),
                suit=CardSuit(card_data["suit"]),
                number=card_data["number"],
                description=card_data.get("description", ""),
            )
            count = card_data.get("count", 1)
            for _ in range(count):
                self._all_cards.append(card)

        # 加载装备牌
        for card_data in data.get("equipment_cards", []):
            card = Card(
                id=card_data["id"],
                name=card_data["name"],
                card_type=CardType(card_data["type"]),
                subtype=CardSubtype(card_data["subtype"]),
                suit=CardSuit(card_data["suit"]),
                number=card_data["number"],
                description=card_data.get("description", ""),
                range=card_data.get("range", 1),
                distance_modifier=card_data.get("distance_modifier", 0),
            )
            count = card_data.get("count", 1)
            for _ in range(count):
                self._all_cards.append(card)

        # 初始化摸牌堆
        self.reset()

    def reset(self) -> None:
        """重置牌堆（将所有牌放入摸牌堆并洗牌）"""
        self.draw_pile = [card for card in self._all_cards]
        self.discard_pile.clear()
        self.shuffle()

    def shuffle(self) -> None:
        """洗牌"""
        random.shuffle(self.draw_pile)

    def draw(self, count: int = 1) -> list[Card]:
        """摸牌

        Args:
            count: 摸牌数量

        Returns:
            摸到的卡牌列表
        """
        cards = []
        for _ in range(count):
            if not self.draw_pile:
                self._reshuffle_discard()

            if self.draw_pile:
                cards.append(self.draw_pile.pop())

        return cards

    def _reshuffle_discard(self) -> None:
        """将弃牌堆洗入摸牌堆"""
        if self.discard_pile:
            self.draw_pile.extend(self.discard_pile)
            self.discard_pile.clear()
            self.shuffle()

    def discard(self, cards: list[Card]) -> None:
        """弃牌

        Args:
            cards: 要弃置的卡牌列表
        """
        self.discard_pile.extend(cards)

    def peek(self, count: int = 1) -> list[Card]:
        """查看牌堆顶的牌（不取出）

        Args:
            count: 查看数量

        Returns:
            牌堆顶的卡牌列表
        """
        # 如果牌堆不够，先洗入弃牌堆
        while len(self.draw_pile) < count and self.discard_pile:
            self._reshuffle_discard()

        return self.draw_pile[-count:] if count <= len(self.draw_pile) else self.draw_pile[:]

    def put_on_top(self, cards: list[Card]) -> None:
        """将牌放到牌堆顶

        Args:
            cards: 要放置的卡牌列表
        """
        self.draw_pile.extend(cards)

    def put_on_bottom(self, cards: list[Card]) -> None:
        """将牌放到牌堆底

        Args:
            cards: 要放置的卡牌列表
        """
        for card in reversed(cards):
            self.draw_pile.insert(0, card)

    @property
    def remaining(self) -> int:
        """获取摸牌堆剩余牌数"""
        return len(self.draw_pile)

    @property
    def discarded(self) -> int:
        """获取弃牌堆牌数"""
        return len(self.discard_pile)

    @property
    def is_empty(self) -> bool:
        """检查牌堆是否完全耗尽（摸牌堆和弃牌堆都为空）"""
        return len(self.draw_pile) == 0 and len(self.discard_pile) == 0

    def __len__(self) -> int:
        return self.remaining

    def __str__(self) -> str:
        return f"Deck(摸牌堆:{self.remaining}, 弃牌堆:{self.discarded})"

    # 标准三国杀牌堆预期卡牌数量 (基于 data/cards.json)
    EXPECTED_CARD_COUNTS: dict[str, int] = {
        # 基本牌
        "杀": 21,
        "闪": 14,
        "桃": 8,
        "酒": 5,
        "火杀": 4,
        "雷杀": 9,
        # 锦囊牌
        "决斗": 3,
        "南蛮入侵": 3,
        "万箭齐发": 1,
        "无中生有": 4,
        "过河拆桥": 6,
        "顺手牵羊": 5,
        "桃园结义": 1,
        "无懈可击": 4,
        "借刀杀人": 2,
        "火攻": 3,
        "铁索连环": 4,
        # 延时锦囊
        "乐不思蜀": 3,
        "兵粮寸断": 2,
        "闪电": 2,
        # 武器
        "青龙偃月刀": 1,
        "丈八蛇矛": 1,
        "诸葛连弩": 2,
        "贯石斧": 1,
        "麒麟弓": 1,
        "方天画戟": 1,
        "寒冰剑": 1,
        "古锭刀": 1,
        "朱雀羽扇": 1,
        # 防具
        "八卦阵": 2,
        "仁王盾": 1,
        "藤甲": 2,
        "白银狮子": 1,
        # 坐骑
        "赤兔": 1,
        "的卢": 1,
        "爪黄飞电": 1,
        "绝影": 1,
        "大宛": 1,
        "紫骍": 1,
    }

    def validate_deck(self) -> list[str]:
        """验证牌堆完整性

        检查所有卡牌 (牌堆 + 弃牌堆 + 不含已分发给玩家的) 的名称和数量
        是否与预期匹配。

        Returns:
            错误列表（空表示验证通过）
        """
        errors: list[str] = []
        counts: dict[str, int] = {}
        for card in self._all_cards:
            counts[card.name] = counts.get(card.name, 0) + 1

        for name, expected in self.EXPECTED_CARD_COUNTS.items():
            actual = counts.get(name, 0)
            if actual != expected:
                errors.append(f"{name}: expected {expected}, got {actual}")

        # 检查是否有未知卡牌
        for name, count in counts.items():
            if name not in self.EXPECTED_CARD_COUNTS:
                errors.append(f"unexpected card: {name} (count={count})")

        return errors


# 卡牌名称常量
class CardName:
    """卡牌名称常量类"""

    # 基本牌
    SHA = "杀"
    SHAN = "闪"
    TAO = "桃"

    # 锦囊牌
    JUEDOU = "决斗"
    NANMAN = "南蛮入侵"
    WANJIAN = "万箭齐发"
    WUZHONG = "无中生有"
    GUOHE = "过河拆桥"
    SHUNSHOU = "顺手牵羊"
    TAOYUAN = "桃园结义"
    WUXIE = "无懈可击"
    JIEDAO = "借刀杀人"

    # 延时锦囊
    LEBUSISHU = "乐不思蜀"
    BINGLIANG = "兵粮寸断"
    SHANDIAN = "闪电"

    # 军争锦囊
    HUOGONG = "火攻"
    TIESUO = "铁索连环"
    JIU = "酒"

    # 武器
    QINGLONG = "青龙偃月刀"
    ZHANGBA = "丈八蛇矛"
    ZHUGENU = "诸葛连弩"
    GUANSHI = "贯石斧"
    QILIN = "麒麟弓"
    FANGTAN = "方天画戟"
    HANBING = "寒冰剑"

    # 防具
    BAGUA = "八卦阵"
    RENWANG = "仁王盾"
    TENGJIA = "藤甲"
    BAIYINSHIZI = "白银狮子"

    # 军争武器
    GUDINGDAO = "古锭刀"
    ZHUQUEYUSHAN = "朱雀羽扇"

    # 坐骑
    CHITU = "赤兔"
    DILU = "的卢"
    ZHUAHUANG = "爪黄飞电"
    JUEYING = "绝影"
    DAWAN = "大宛"
    ZIXING = "紫骍"
