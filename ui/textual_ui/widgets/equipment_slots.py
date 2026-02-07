# -*- coding: utf-8 -*-
"""
EquipmentSlots — 装备槽位组件 (4 槽)

武器 / 防具 / 进攻马 / 防御马
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from textual.widgets import Static

if TYPE_CHECKING:
    from game.player import Player


SLOT_ICONS = {
    "weapon": "⚔ 武器",
    "armor": "🛡 防具",
    "attack_horse": "🐎-进攻",
    "defense_horse": "🐎+防御",
}


class EquipmentSlots(Static):
    """装备区 4 槽 Widget"""

    DEFAULT_CSS = """
    EquipmentSlots {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(self, player=None, **kwargs):
        super().__init__(**kwargs)
        self._player = player

    def render(self) -> str:
        if not self._player or not hasattr(self._player, "equipment"):
            return "[dim]无装备[/dim]"

        eq = self._player.equipment
        lines = []
        slots = [
            ("weapon", eq.weapon),
            ("armor", eq.armor),
            ("attack_horse", eq.horse_minus),
            ("defense_horse", eq.horse_plus),
        ]
        for slot_key, card in slots:
            label = SLOT_ICONS[slot_key]
            if card:
                suit_icon = {"spade": "♠", "heart": "♥", "club": "♣", "diamond": "♦"}.get(
                    getattr(card.suit, "value", ""), ""
                )
                lines.append(f"[bold]{label}[/bold]: {suit_icon}{card.name}")
            else:
                lines.append(f"[dim]{label}: 空[/dim]")
        return "\n".join(lines)

    def update_player(self, player) -> None:
        self._player = player
        self.refresh()
