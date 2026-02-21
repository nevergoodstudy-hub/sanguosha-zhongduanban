"""主菜单界面"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Static

from i18n import t as _t


class MainMenuScreen(Screen):
    """主菜单界面"""

    CSS = """
    MainMenuScreen {
        align: center middle;
    }
    #menu-box {
        width: 60;
        height: auto;
        border: double green;
        padding: 1 2;
    }
    #title {
        text-align: center;
        text-style: bold;
        color: red;
        margin-bottom: 1;
    }
    .menu-btn {
        width: 100%;
        margin: 1 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Static(_t("ui.menu.title"), id="title"),
            Button(_t("ui.menu.start"), id="btn-start", classes="menu-btn", variant="success"),
            Button(_t("ui.menu.rules"), id="btn-rules", classes="menu-btn", variant="primary"),
            Button(_t("ui.menu.quit"), id="btn-quit", classes="menu-btn", variant="error"),
            id="menu-box",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-start":
            from .game_setup import GameSetupScreen

            self.app.push_screen(GameSetupScreen())
        elif event.button.id == "btn-rules":
            from .rules import RulesScreen

            self.app.push_screen(RulesScreen())
        elif event.button.id == "btn-quit":
            self.app.exit()
