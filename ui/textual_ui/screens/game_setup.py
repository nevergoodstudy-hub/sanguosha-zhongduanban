"""游戏设置界面（选人数 + 难度）"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Select, Static

from i18n import t as _t


class GameSetupScreen(Screen):
    """游戏设置界面（选人数 + 难度）"""

    CSS = """
    GameSetupScreen {
        align: center middle;
    }
    #setup-box {
        width: 50;
        height: auto;
        border: double blue;
        padding: 1 2;
    }
    #setup-title {
        text-align: center;
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
    }
    .setup-select {
        width: 100%;
        margin: 1 0;
    }
    #btn-go {
        width: 100%;
        margin-top: 1;
    }
    """

    @staticmethod
    def _player_counts() -> list[tuple[str, int]]:
        return [
            (_t("ui.setup.2p"), 2),
            (_t("ui.setup.3p"), 3),
            (_t("ui.setup.4p"), 4),
            (_t("ui.setup.5p"), 5),
            (_t("ui.setup.6p"), 6),
            (_t("ui.setup.7p"), 7),
            (_t("ui.setup.8p"), 8),
        ]

    @staticmethod
    def _difficulties() -> list[tuple[str, str]]:
        return [
            (_t("ui.setup.easy"), "easy"),
            (_t("ui.setup.normal"), "normal"),
            (_t("ui.setup.hard"), "hard"),
        ]

    @staticmethod
    def _role_preferences() -> list[tuple[str, str]]:
        return [
            (_t("ui.setup.role_lord"), "lord"),
            (_t("ui.setup.role_random"), "random"),
        ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static(_t("ui.setup.title"), id="setup-title"),
            Static(_t("ui.setup.player_count")),
            Select(self._player_counts(), id="sel-count", value=4, classes="setup-select"),
            Static(_t("ui.setup.difficulty")),
            Select(self._difficulties(), id="sel-diff", value="normal", classes="setup-select"),
            Static(_t("ui.setup.role")),
            Select(self._role_preferences(), id="sel-role", value="lord", classes="setup-select"),
            Button(_t("ui.setup.start"), id="btn-go", variant="success"),
            id="setup-box",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-go":
            count_sel = self.query_one("#sel-count", Select)
            diff_sel = self.query_one("#sel-diff", Select)
            role_sel = self.query_one("#sel-role", Select)
            player_count = count_sel.value if count_sel.value is not Select.BLANK else 4
            difficulty = diff_sel.value if diff_sel.value is not Select.BLANK else "normal"
            role_preference = role_sel.value if role_sel.value is not Select.BLANK else "lord"
            # 转到选将界面
            from .hero_select import HeroSelectScreen

            self.app.push_screen(
                HeroSelectScreen(int(player_count), str(difficulty), str(role_preference))
            )
