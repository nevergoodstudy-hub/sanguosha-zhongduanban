"""无懈可击响应弹窗 (M-C C4).

修复 P0 缺陷: 原 ask_for_wuxie 硬编码 return None。
弹窗显示锦囊信息 + 5秒倒计时，超时自动放弃。

dismiss(True)  → 使用无懈可击
dismiss(False) → 放弃 / 超时
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.timer import Timer
from textual.widgets import Button, Static

from ui.textual_ui.modals.base import AnimatedModalScreen

if TYPE_CHECKING:
    pass


class WuxieResponseModal(AnimatedModalScreen[bool]):
    """无懈可击响应弹窗 — 5秒倒计时，显示锦囊信息."""

    DEFAULT_CSS = """
    WuxieResponseModal {
        align: center middle;
        background: $background 70%;
    }
    WuxieResponseModal > #wuxie-container {
        width: 60;
        max-width: 85%;
        height: auto;
        max-height: 80%;
        border: thick $secondary;
        background: $surface;
        padding: 1 2;
    }
    WuxieResponseModal #wuxie-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    WuxieResponseModal #wuxie-info {
        text-align: center;
        margin-bottom: 1;
    }
    WuxieResponseModal #wuxie-countdown {
        text-align: center;
        color: $error;
        text-style: bold;
        margin-bottom: 1;
    }
    WuxieResponseModal .btn-row {
        layout: horizontal;
        height: auto;
        margin-top: 1;
    }
    WuxieResponseModal .btn-row Button {
        width: 1fr;
        margin: 0 1;
    }
    """

    def __init__(
        self,
        trick_name: str = "锦囊",
        source_name: str = "",
        target_name: str = "",
        currently_cancelled: bool = False,
        countdown: int = 5,
    ):
        super().__init__()
        self._trick_name = trick_name
        self._source_name = source_name
        self._target_name = target_name
        self._currently_cancelled = currently_cancelled
        self._remaining = countdown
        self._countdown_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        # 构建锦囊信息描述
        action = "取消" if self._currently_cancelled else "使用"
        info_line = f"{self._source_name} 对 {self._target_name} {action}【{self._trick_name}】"
        cancel_hint = "（当前已被无懈，再次无懈将恢复生效）" if self._currently_cancelled else ""

        with Container(id="wuxie-container"):
            yield Static("🃏 是否使用【无懈可击】？", id="wuxie-title")
            yield Static(f"{info_line}{cancel_hint}", id="wuxie-info")
            yield Static(f"⏱ {self._remaining}s 后自动放弃", id="wuxie-countdown")
            with Horizontal(classes="btn-row"):
                yield Button("🎴 使用无懈可击", id="btn-use-wuxie", variant="warning")
                yield Button("⏭ 放弃", id="btn-skip-wuxie", variant="default")

    def on_mount(self) -> None:
        super().on_mount()  # 淡入动画
        self._countdown_timer = self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self._remaining -= 1
        with contextlib.suppress(Exception):
            self.query_one("#wuxie-countdown", Static).update(f"⏱ {self._remaining}s 后自动放弃")
        if self._remaining <= 0:
            if self._countdown_timer:
                self._countdown_timer.stop()
            self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._countdown_timer:
            self._countdown_timer.stop()
        if event.button.id == "btn-use-wuxie":
            self.dismiss(True)
        else:
            self.dismiss(False)
