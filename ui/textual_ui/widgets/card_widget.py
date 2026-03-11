"""CardWidget — 三国杀OL风格卡牌组件.

花色色差、类型色框、序号标签、键盘交互、
tooltip 效果描述，on_click / on_key 发布 CardClicked Message。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    pass


# 花色映射
SUIT_ICONS = {"spade": "♠", "heart": "♥", "club": "♣", "diamond": "♦"}
SUIT_COLORS = {"spade": "#ecf0f1", "heart": "#e74c3c", "club": "#ecf0f1", "diamond": "#e74c3c"}

# 卡牌类型图标和边框色
CARD_TYPE_ICONS = {
    "basic": "⚔",
    "trick": "📜",
    "equipment": "⚙",
}
CARD_TYPE_BORDER_COLORS = {
    "basic": "#e74c3c",  # 红色 - 基本牌
    "trick": "#3498db",  # 蓝色 - 锦囊牌
    "equipment": "#f39c12",  # 黄色 - 装备牌
}

# 卡牌效果描述映射
CARD_EFFECT_DESC = {
    "杀": "出牌阶段对攻击范围内一名角色使用，目标需出闪否则受到1点伤害",
    "闪": "当你成为杀的目标时，打出闪抵消杀的效果",
    "桃": "出牌阶段回复1点体力，濒死时可使用",
    "决斗": "对一名角色使用，双方交替出杀，先不出杀者受到1点伤害",
    "南蛮入侵": "对所有其他角色使用，不出杀者受到1点伤害",
    "万箭齐发": "对所有其他角色使用，不出闪者受到1点伤害",
    "无中生有": "从牌堆摸两张牌",
    "过河拆桥": "弃置目标一张手牌或装备牌",
    "顺手牵羊": "获得距离1以内目标一张手牌或装备",
    "桃园结义": "所有角色各回复1点体力",
    "无懈可击": "取消一张锦囊牌的效果（无距离限制）",
    "借刀杀人": "令有武器的角色对指定目标使用杀，否则交出武器",
    "乐不思蜀": "延时锦囊，判定非红桃则跳过出牌阶段",
    "兵粮寸断": "延时锦囊，判定非梅花则跳过摸牌阶段",
    "闪电": "延时锦囊，判定黑桃♠2~9则受到3点雷电伤害",
    "火攻": "展示目标手牌，弃置同花色牌造成1点火焰伤害",
    "铁索连环": "选择一两名角色横置/重置铁索状态",
    "酒": "下一张杀伤害+1，濒死时可当桃使用",
    # 武器
    "青龙偃月刀": "攻击范围3，杀被闪时可再出一张杀",
    "丈八蛇矛": "攻击范围3，可弃两张手牌当杀使用",
    "诸葛连弩": "攻击范围1，杀无次数限制",
    "贯石斧": "攻击范围3，杀被闪时可弃两张牌强制命中",
    "麒麟弓": "攻击范围5，杀命中时可弃目标一匹马",
    "方天画戟": "攻击范围4，杀打出最后一张手牌时可额外指定2个目标",
    "寒冰剑": "攻击范围2，杀命中可选择弃置目标两张牌代替伤害",
    "古锤刀": "攻击范围2，目标无手牌时杀+1伤害",
    "朱雀羽扇": "攻击范围4，可将普通杀当火杀使用",
    # 防具
    "八卦阵": "需要出闪时可判定，红色则视为出闪",
    "仁王盾": "黑色杀无效",
    "藤甲": "普通杀和南蛮万箭无效，但受到火焰伤害+1",
    "白银狮子": "失去装备时回复1点体力，受到伤害时最多减到1点",
}


class CardWidget(Static, can_focus=True):
    """三国杀OL风格卡牌 Widget."""

    DEFAULT_CSS = """
    CardWidget {
        width: 18;
        height: 6;
        border: round $primary;
        padding: 0 1;
        content-align: center middle;
        transition: background 200ms, border 200ms;
    }
    CardWidget:hover {
        border: heavy $accent;
        background: $accent-darken-3;
    }
    CardWidget:focus {
        border: heavy $success;
        background: $success-darken-2;
        text-style: bold;
    }
    CardWidget.selected {
        border: double $success;
        background: $success-darken-1;
        text-style: bold;
    }
    CardWidget.playable {
        border: heavy $warning;
        background: $warning-darken-3;
    }
    CardWidget.playable:hover {
        background: $warning-darken-2;
    }
    CardWidget.disabled {
        opacity: 40%;
    }
    """

    selected = reactive(False)
    card_index = reactive(-1)

    class CardClicked(Message):
        """卡牌被点击."""

        def __init__(self, index: int, card=None) -> None:
            super().__init__()
            self.index = index
            self.card = card

    def __init__(self, card, index: int = -1, **kwargs):
        """Args:
        card: game.card.Card 对象
        index: 手牌中的索引.
        """
        super().__init__(**kwargs)
        self._card = card
        self.card_index = index
        # 设置 tooltip
        self.tooltip = self._build_tooltip()

    def _build_tooltip(self) -> str:
        """构建 tooltip 文本：包含花色点数、卡类、效果描述."""
        c = self._card
        suit_val = getattr(c.suit, "value", "") if hasattr(c, "suit") else ""
        suit_icon = SUIT_ICONS.get(suit_val, "")
        number = c.number_str if hasattr(c, "number_str") else "?"
        parts = [f"【{c.name}】 {suit_icon}{number}"]
        # 卡类类型
        type_map = {"basic": "基本牌", "trick": "锦囊牌", "equipment": "装备牌"}
        if hasattr(c, "card_type"):
            type_val = getattr(c.card_type, "value", "")
            parts.append(type_map.get(type_val, type_val))
        # 效果描述
        name_str = str(c.name) if hasattr(c, "name") else ""
        effect = CARD_EFFECT_DESC.get(name_str, "")
        if effect:
            parts.append("━━━")
            parts.append(effect)
        elif hasattr(c, "description") and c.description:
            parts.append("━━━")
            parts.append(c.description)
        # 武器攻击范围
        if hasattr(c, "range") and c.range > 1:
            parts.append(f"攻击范围: {c.range}")
        # 坐骑距离修正
        if hasattr(c, "distance_modifier") and c.distance_modifier != 0:
            sign = "+" if c.distance_modifier > 0 else ""
            parts.append(f"距离修正: {sign}{c.distance_modifier}")
        return "\n".join(parts)

    def render(self) -> str:
        """渲染三国杀OL风格卡面."""
        c = self._card
        suit_val = getattr(c.suit, "value", "") if hasattr(c, "suit") else ""
        suit_icon = SUIT_ICONS.get(suit_val, "?")
        suit_color = SUIT_COLORS.get(suit_val, "white")
        number = c.number_str if hasattr(c, "number_str") else "?"
        name = str(c.name) if hasattr(c, "name") else "?"

        # 截断长名
        if len(name) > 6:
            name = name[:5] + "…"

        type_icon = ""
        if hasattr(c, "card_type"):
            type_icon = CARD_TYPE_ICONS.get(getattr(c.card_type, "value", ""), "")

        # 选中标记
        sel = "[bold green]✓[/bold green]" if self.selected else ""

        # 序号标签（快捷键提示）
        idx_label = ""
        if self.card_index >= 0:
            key = str(self.card_index + 1) if self.card_index < 9 else "0"
            if self.card_index < 10:
                idx_label = f"[dim]『{key}』[/dim] "

        return (
            f"{idx_label}[{suit_color}]{suit_icon}[/{suit_color}] {number}\n"
            f"[bold]{name}[/bold]\n"
            f"{type_icon} {sel}"
        )

    def on_click(self) -> None:
        self.post_message(self.CardClicked(self.card_index, self._card))

    def on_key(self, event) -> None:
        """键盘交互：Enter/Space 等同于点击."""
        if event.key in ("enter", "space"):
            self.post_message(self.CardClicked(self.card_index, self._card))
            event.prevent_default()
            event.stop()

    def watch_selected(self, value: bool) -> None:
        if value:
            self.add_class("selected")
        else:
            self.remove_class("selected")
