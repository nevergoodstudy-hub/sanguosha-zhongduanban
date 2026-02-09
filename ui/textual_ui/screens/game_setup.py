"""游戏设置界面（选人数 + 难度）"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Select, Static


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

    PLAYER_COUNTS = [
        ("2人 — 主公 vs 反贼", 2),
        ("3人 — 主公 vs 反贼+内奸", 3),
        ("4人 — 主+忠 vs 反+内", 4),
        ("5人 — 主+忠 vs 2反+内", 5),
        ("6人 — 主+忠 vs 3反+内", 6),
        ("7人 — 主+2忠 vs 3反+内", 7),
        ("8人 — 主+2忠 vs 4反+内", 8),
    ]

    DIFFICULTIES = [
        ("简单 — 随机出牌", "easy"),
        ("普通 — 基础策略", "normal"),
        ("困难 — 深度策略", "hard"),
    ]

    ROLE_PREFERENCES = [
        ("始终主公 — 你始终扮演主公", "lord"),
        ("随机分配 — 随机获得任意身份", "random"),
    ]

    def compose(self) -> ComposeResult:
        yield Container(
            Static("⚙ 游戏设置", id="setup-title"),
            Static("人数:"),
            Select(self.PLAYER_COUNTS, id="sel-count", value=4, classes="setup-select"),
            Static("难度:"),
            Select(self.DIFFICULTIES, id="sel-diff", value="normal", classes="setup-select"),
            Static("身份:"),
            Select(self.ROLE_PREFERENCES, id="sel-role", value="lord", classes="setup-select"),
            Button("▶ 开始游戏", id="btn-go", variant="success"),
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
            self.app.push_screen(HeroSelectScreen(
                int(player_count), str(difficulty), str(role_preference)
            ))
