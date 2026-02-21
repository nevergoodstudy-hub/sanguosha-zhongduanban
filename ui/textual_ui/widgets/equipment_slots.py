"""EquipmentSlots — 三国杀OL风格装备槽位组件 (4 槽)

武器 / 防具 / 进攻马(-1) / 防御马(+1)
水平布局，每个槽位显示装备名称和花色点数。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.widgets import Static

if TYPE_CHECKING:
    pass


SLOT_LABELS = {
    "weapon": ("⚔", "武器"),
    "armor": ("🛡", "防具"),
    "attack_horse": ("🐎", "-1马"),
    "defense_horse": ("🐎", "+1马"),
}

SUIT_SYMBOLS = {"spade": "♠", "heart": "♥", "club": "♣", "diamond": "♦"}
SUIT_COLORS = {"spade": "#ecf0f1", "heart": "#e74c3c", "club": "#ecf0f1", "diamond": "#e74c3c"}


class EquipmentSlots(Static):
    """三国杀OL风格装备区 4 槽 Widget（水平布局）"""

    DEFAULT_CSS = """
    EquipmentSlots {
        width: 100%;
        height: auto;
        min-height: 2;
        padding: 0 1;
    }
    """

    def __init__(self, player=None, **kwargs):
        super().__init__(**kwargs)
        self._player = player

    def _render_slot(self, slot_key: str, card) -> str:
        """渲染单个装备槽"""
        icon, label = SLOT_LABELS[slot_key]
        if card:
            suit_val = getattr(card.suit, "value", "") if hasattr(card, "suit") else ""
            suit_icon = SUIT_SYMBOLS.get(suit_val, "")
            suit_color = SUIT_COLORS.get(suit_val, "white")
            number = card.number_str if hasattr(card, "number_str") else ""
            return (
                f"[bold]{icon}[/bold]"
                f"[{suit_color}]{suit_icon}{number}[/{suit_color}]"
                f"[bold]{card.name}[/bold]"
            )
        return f"[dim]{icon}{label}:空[/dim]"

    def render(self) -> str:
        if not self._player or not hasattr(self._player, "equipment"):
            return "[dim]⚔空  🛡空  🐎-空  🐎+空[/dim]"

        eq = self._player.equipment
        slots = [
            self._render_slot("weapon", eq.weapon),
            self._render_slot("armor", eq.armor),
            self._render_slot("attack_horse", eq.horse_minus),
            self._render_slot("defense_horse", eq.horse_plus),
        ]
        return "  │  ".join(slots)

    def update_player(self, player) -> None:
        self._player = player
        self.refresh()
