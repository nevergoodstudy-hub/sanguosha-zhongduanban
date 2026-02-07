# -*- coding: utf-8 -*-
"""
Textual TUI 主应用（M3-T01 / M3-T02）

Screen 切换: MainMenu → GameSetup → GamePlay → GameOver
各 Screen 已拆分至 screens/ 子包。
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from textual.app import App
from textual.binding import Binding

# -- 向后兼容：从 screens 子包重导出所有 Screen 类 --
from ui.textual_ui.screens import (  # noqa: F401
    MainMenuScreen,
    RulesScreen,
    GameSetupScreen,
    HeroSelectScreen,
    GamePlayScreen,
    GameOverScreen,
)
from ui.textual_ui.bridge import TextualUIBridge  # noqa: F401

if TYPE_CHECKING:
    from game.engine import GameEngine


# ==================== App ====================


class SanguoshaApp(App):
    """三国杀 Textual 主应用"""

    TITLE = "三国杀 - 命令行终端版"
    CSS = """
    Screen {
        background: $surface;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "退出"),
    ]

    def __init__(self):
        super().__init__()
        self._engine: Optional[GameEngine] = None
        self._difficulty: str = "normal"

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())
