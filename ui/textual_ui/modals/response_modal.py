"""响应类 ModalScreen 弹窗 (M-C C1/C2/C3).

ResponseModalBase — 半透明背景 + 倒计时 + dismiss 模式基类
ShanResponseModal — "是否出闪"
ShaResponseModal  — "是否出杀"（决斗/南蛮/万箭）
TaoResponseModal  — "是否使用桃"（濒死救援）

线程安全模式:
  push_screen(Modal, callback) → user clicks → dismiss(result) → callback

ModalScreen[T] 的 T 为 dismiss 返回值类型:
  - True  → 使用该卡牌
  - False / None → 放弃
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.timer import Timer
from textual.widgets import Button, Static

from ui.textual_ui.modals.base import AnimatedModalScreen

if TYPE_CHECKING:
    pass


class ResponseModalBase(AnimatedModalScreen[bool]):
    """响应类弹窗基类.

    半透明背景覆盖，居中弹窗框，可选倒计时自动拒绝。
    子类只需定义 title_text / body_text / confirm_label / reject_label。
    """

    DEFAULT_CSS = """
    ResponseModalBase {
        align: center middle;
        background: $background 70%;
    }
    ResponseModalBase > #modal-container {
        width: 55;
        max-width: 80%;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    ResponseModalBase #modal-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    ResponseModalBase #modal-body {
        text-align: center;
        margin-bottom: 1;
    }
    ResponseModalBase #modal-countdown {
        text-align: center;
        color: $warning;
        text-style: bold;
        margin-bottom: 1;
    }
    ResponseModalBase #modal-cards-info {
        margin-bottom: 1;
        text-align: center;
    }
    ResponseModalBase .btn-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }
    ResponseModalBase .btn-row Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    # 子类可覆盖
    title_text: str = "请选择"
    body_text: str = ""
    confirm_label: str = "✅ 确认"
    reject_label: str = "❌ 放弃"
    countdown_seconds: int = 0  # 0 表示不倒计时
    cards_info: str = ""  # 可选：显示可用卡牌信息

    def __init__(
        self,
        title: str = "",
        body: str = "",
        cards: list | None = None,
        countdown: int = 0,
    ):
        super().__init__()
        if title:
            self.title_text = title
        if body:
            self.body_text = body
        if countdown > 0:
            self.countdown_seconds = countdown
        self._remaining = self.countdown_seconds
        self._countdown_timer: Timer | None = None
        # 卡牌信息
        if cards:
            info_parts = []
            for c in cards:
                suit_icon = {"spade": "♠", "heart": "♥", "club": "♣", "diamond": "♦"}.get(
                    getattr(c.suit, "value", ""), "?"
                )
                info_parts.append(f"{suit_icon}{c.number_str} {c.name}")
            self.cards_info = "  ".join(info_parts)

    def compose(self) -> ComposeResult:
        with Container(id="modal-container"):
            yield Static(self.title_text, id="modal-title")
            if self.body_text:
                yield Static(self.body_text, id="modal-body")
            if self.cards_info:
                yield Static(f"可用: {self.cards_info}", id="modal-cards-info")
            if self.countdown_seconds > 0:
                yield Static(f"⏱ {self._remaining}s", id="modal-countdown")
            with Horizontal(classes="btn-row"):
                yield Button(self.confirm_label, id="btn-confirm", variant="success")
                yield Button(self.reject_label, id="btn-reject", variant="error")

    def on_mount(self) -> None:
        super().on_mount()  # 淡入动画
        if self.countdown_seconds > 0:
            self._countdown_timer = self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        """倒计时每秒 tick."""
        self._remaining -= 1
        try:
            cd_widget = self.query_one("#modal-countdown", Static)
            cd_widget.update(f"⏱ {self._remaining}s")
        except Exception:
            pass
        if self._remaining <= 0:
            if self._countdown_timer:
                self._countdown_timer.stop()
            self.dismiss(False)  # 超时自动拒绝

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._countdown_timer:
            self._countdown_timer.stop()
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ShanResponseModal(ResponseModalBase):
    """闪响应弹窗: 你被【杀】攻击，是否出【闪】？."""

    title_text = "⚔ 你被攻击了！"
    body_text = "是否使用【闪】抵消？"
    confirm_label = "🛡 出闪"
    reject_label = "💔 不出"
    countdown_seconds = 15


class ShaResponseModal(ResponseModalBase):
    """杀响应弹窗: 需要出【杀】（决斗/南蛮入侵/万箭齐发）."""

    title_text = "⚡ 需要出杀！"
    body_text = "是否使用【杀】响应？"
    confirm_label = "⚔ 出杀"
    reject_label = "💔 不出"
    countdown_seconds = 15


class TaoResponseModal(ResponseModalBase):
    """桃响应弹窗: 濒死求桃."""

    title_text = "💀 濒死救援！"
    confirm_label = "🍑 使用桃"
    reject_label = "😢 放弃"
    countdown_seconds = 20

    def __init__(self, dying_name: str = "", cards=None, **kwargs):
        body = f"{dying_name} 濒死！是否使用【桃】救援？" if dying_name else "是否使用【桃】？"
        super().__init__(body=body, cards=cards, **kwargs)
