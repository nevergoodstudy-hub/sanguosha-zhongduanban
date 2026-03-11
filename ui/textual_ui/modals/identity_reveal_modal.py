"""IdentityRevealModal — 身份揭示模态窗口.

游戏开始时弹出，向人类玩家展示其被分配的身份和胜利条件。
仅当人类不是主公时显示（主公身份本就公开）。
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Button, Static

# 各身份的胜利条件描述
_WIN_CONDITIONS = {
    "lord": "消灭所有反贼和内奸",
    "loyalist": "保护主公，消灭所有反贼和内奸",
    "rebel": "消灭主公",
    "spy": "成为最后的幸存者（先帮主公消灭反贼，再单挑主公）",
}

# 身份颜色
_IDENTITY_COLORS = {
    "lord": "bold red",
    "loyalist": "bold yellow",
    "rebel": "bold green",
    "spy": "bold blue",
}


class IdentityRevealModal(ModalScreen[bool]):
    """身份揭示模态窗口."""

    CSS = """
    IdentityRevealModal {
        align: center middle;
    }
    #reveal-box {
        width: 60;
        height: auto;
        border: double $accent;
        padding: 2 3;
        background: $surface;
    }
    #reveal-title {
        text-align: center;
        text-style: bold;
        color: cyan;
        margin-bottom: 1;
    }
    #reveal-identity {
        text-align: center;
        margin: 1 0;
    }
    #reveal-condition {
        text-align: center;
        margin: 1 0;
    }
    #btn-confirm {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, identity_value: str, identity_chinese: str):
        super().__init__()
        self.identity_value = identity_value
        self.identity_chinese = identity_chinese

    def compose(self) -> ComposeResult:
        color = _IDENTITY_COLORS.get(self.identity_value, "white")
        condition = _WIN_CONDITIONS.get(self.identity_value, "未知")
        yield Container(
            Static("🎭 身份揭示", id="reveal-title"),
            Static(
                f"你的身份是: [{color}]【{self.identity_chinese}】[/{color}]",
                id="reveal-identity",
            ),
            Static(f"胜利条件: {condition}", id="reveal-condition"),
            Static("⚠ 除主公外，其他玩家的身份对你是隐藏的", id="reveal-hint"),
            Button("✔ 确认", id="btn-confirm", variant="success"),
            id="reveal-box",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm":
            self.dismiss(True)
