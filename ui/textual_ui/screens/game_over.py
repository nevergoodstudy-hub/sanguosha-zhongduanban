"""游戏结束界面"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Static


class GameOverScreen(Screen):
    """游戏结束界面"""

    CSS = """
    GameOverScreen {
        align: center middle;
    }
    #gameover-box {
        width: 50;
        height: auto;
        border: double red;
        padding: 2;
    }
    #result-text {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, message: str, is_victory: bool):
        super().__init__()
        self._message = message
        self._is_victory = is_victory

    def compose(self) -> ComposeResult:
        icon = "🏆 胜利!" if self._is_victory else "💀 失败"
        color = "green" if self._is_victory else "red"
        yield Container(
            Static(f"[bold {color}]{icon}[/bold {color}]", id="result-text"),
            Static(self._message),
            Button("🏠 返回主菜单", id="btn-back", variant="primary"),
            Button("🚪 退出", id="btn-quit", variant="error"),
            id="gameover-box",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            from .main_menu import MainMenuScreen
            self.app.switch_screen(MainMenuScreen())
        elif event.button.id == "btn-quit":
            self.app.exit()
