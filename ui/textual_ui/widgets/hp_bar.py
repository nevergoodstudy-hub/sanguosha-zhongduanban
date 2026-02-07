# -*- coding: utf-8 -*-
"""
HPBar — 体力条组件

reactive HP 显示，颜色随 HP 变化:
  满血: 绿  |  半血: 黄  |  危险: 红
"""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static


class HPBar(Static):
    """体力条 Widget"""

    DEFAULT_CSS = """
    HPBar {
        width: auto;
        height: 1;
    }
    """

    hp = reactive(0)
    max_hp = reactive(0)

    def __init__(self, hp: int = 0, max_hp: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.hp = hp
        self.max_hp = max_hp

    def render(self) -> str:
        if self.max_hp <= 0:
            return "[dim]--[/dim]"

        ratio = self.hp / self.max_hp if self.max_hp > 0 else 0
        if ratio > 0.5:
            color = "green"
        elif ratio > 0.25:
            color = "yellow"
        else:
            color = "red"

        filled = f"[{color}]●[/{color}]" * self.hp
        empty = "[dim]○[/dim]" * (self.max_hp - self.hp)
        return f"{filled}{empty} {self.hp}/{self.max_hp}"

    def update_hp(self, hp: int, max_hp: int) -> None:
        self.hp = hp
        self.max_hp = max_hp
