"""花色选择弹窗 (M-C C7).

修复 P0: 原 choose_suit 使用 random.choice。
提供 ♠♥♣♦ 四个大按钮，点击 dismiss 对应 CardSuit。

dismiss(str)  → 花色值 ("spade"/"heart"/"club"/"diamond")
dismiss(None) → 取消
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Button, Static

from ui.textual_ui.modals.base import AnimatedModalScreen


class SuitSelectModal(AnimatedModalScreen[str | None]):
    """花色选择弹窗 — 四色大按钮."""

    DEFAULT_CSS = """
    SuitSelectModal {
        align: center middle;
        background: $background 70%;
    }
    SuitSelectModal > #suit-container {
        width: 50;
        max-width: 80%;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    SuitSelectModal #suit-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    SuitSelectModal .suit-grid {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        height: auto;
    }
    SuitSelectModal .suit-btn {
        width: 100%;
        height: 3;
        content-align: center middle;
    }
    SuitSelectModal #btn-cancel-suit {
        width: 100%;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="suit-container"):
            yield Static("🎴 选择花色", id="suit-title")
            with Container(classes="suit-grid"):
                yield Button("♠ 黑桃", id="suit-spade", classes="suit-btn", variant="default")
                yield Button("♥ 红桃", id="suit-heart", classes="suit-btn", variant="error")
                yield Button("♣ 梅花", id="suit-club", classes="suit-btn", variant="default")
                yield Button("♦ 方块", id="suit-diamond", classes="suit-btn", variant="warning")
            yield Button("❌ 取消", id="btn-cancel-suit", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        suit_map = {
            "suit-spade": "spade",
            "suit-heart": "heart",
            "suit-club": "club",
            "suit-diamond": "diamond",
        }
        if btn_id in suit_map:
            self.dismiss(suit_map[btn_id])
        elif btn_id == "btn-cancel-suit":
            self.dismiss(None)
