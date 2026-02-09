"""Textual TUI 主应用（M3-T01 / M3-T02）

Screen 切换: MainMenu → GameSetup → GamePlay → GameOver
各 Screen 已拆分至 screens/ 子包。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import App
from textual.binding import Binding

from ui.textual_ui.bridge import TextualUIBridge  # noqa: F401

# -- 向后兼容：从 screens 子包重导出所有 Screen 类 --
from ui.textual_ui.screens import (  # noqa: F401
    GameOverScreen,
    GamePlayScreen,
    GameSetupScreen,
    HeroSelectScreen,
    MainMenuScreen,
    RulesScreen,
)

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
    .flash-damage {
        background: $error 30%;
        transition: opacity 300ms;
    }
    .flash-heal {
        background: $success 30%;
        transition: opacity 300ms;
    }
    .flash-skill {
        background: $warning 30%;
        transition: opacity 300ms;
    }
    .card-btn {
        min-width: 16;
        margin: 0 1;
        transition: opacity 150ms;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "退出"),
    ]

    def __init__(self):
        super().__init__()
        self._engine: GameEngine | None = None
        self._difficulty: str = "normal"

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())
