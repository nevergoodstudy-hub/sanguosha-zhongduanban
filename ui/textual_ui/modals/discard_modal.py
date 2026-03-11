"""弃牌阶段弹窗 (P0-3).

让人类玩家在弃牌阶段选择要弃掉的手牌。
支持多选，必须恰好弃掉 need_count 张牌才能确认。

dismiss(List[int]) → 选中的手牌索引列表
dismiss(None)      → 超时/异常（自动弃末尾的牌）
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.timer import Timer
from textual.widgets import Button, Static

from ui.textual_ui.modals.base import AnimatedModalScreen

if TYPE_CHECKING:
    from game.card import Card


logger = logging.getLogger(__name__)


class DiscardModal(AnimatedModalScreen[list[int] | None]):
    """弃牌阶段弹窗."""

    DEFAULT_CSS = """
    DiscardModal {
        align: center middle;
        background: $background 70%;
    }
    DiscardModal > #discard-container {
        width: 70;
        max-width: 90%;
        height: auto;
        max-height: 85%;
        border: thick $warning;
        background: $surface;
        padding: 1 2;
        overflow-y: auto;
    }
    DiscardModal #discard-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    DiscardModal #discard-status {
        text-align: center;
        margin-bottom: 1;
    }
    DiscardModal #discard-countdown {
        text-align: center;
        color: $warning;
        text-style: bold;
        margin-bottom: 1;
    }
    DiscardModal .card-row {
        height: auto;
        layout: horizontal;
        overflow-x: auto;
    }
    DiscardModal .discard-card-btn {
        min-width: 18;
        margin: 0 1 1 0;
    }
    DiscardModal .discard-card-btn.selected {
        border: heavy $error;
        background: $error-darken-2;
    }
    DiscardModal #btn-confirm-discard {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        cards: list[Card],
        need_count: int,
        countdown: int = 30,
        *,
        title: str | None = None,
        confirm_text: str = "✅ 确认弃牌",
        cancel_text: str | None = None,
        timeout_auto_select: bool = True,
    ):
        """初始化弃牌弹窗.

        Args:
        cards: 玩家当前手牌列表
        need_count: 需要选择的张数
        countdown: 倒计时秒数，0 表示不倒计时
        title: 顶部标题，默认弃牌提示
        confirm_text: 确认按钮前缀文案
        cancel_text: 可选取消按钮文案；None 表示不显示
        timeout_auto_select: 超时后是否自动选择最后 N 张牌
        """
        super().__init__()
        self._cards = cards
        self._need_count = need_count
        self._selected: set[int] = set()
        self._remaining = countdown
        self._countdown = countdown
        self._timer: Timer | None = None
        self._title = title or f"🗑 弃牌阶段 — 请选择 {self._need_count} 张牌弃掉"
        self._confirm_text = confirm_text
        self._cancel_text = cancel_text
        self._timeout_auto_select = timeout_auto_select

    def compose(self) -> ComposeResult:
        with Container(id="discard-container"):
            yield Static(
                self._title,
                id="discard-title",
            )
            yield Static(
                self._status_text(),
                id="discard-status",
            )
            if self._countdown > 0:
                yield Static(f"⏱ {self._remaining}s", id="discard-countdown")

            with Horizontal(classes="card-row"):
                for i, card in enumerate(self._cards):
                    suit_map = {"spade": "♠", "heart": "♥", "club": "♣", "diamond": "♦"}
                    suit_icon = suit_map.get(getattr(card.suit, "value", ""), "?")
                    label = f"{suit_icon}{card.number_str} {card.name}"
                    yield Button(
                        label,
                        id=f"dcard-{i}",
                        classes="discard-card-btn",
                        variant="default",
                    )

            yield Button(
                f"{self._confirm_text} (0/{self._need_count})",
                id="btn-confirm-discard",
                variant="success",
                disabled=True,
            )
            if self._cancel_text:
                yield Button(self._cancel_text, id="btn-cancel-discard", variant="error")

    def on_mount(self) -> None:
        super().on_mount()  # 淡入动画
        if self._countdown > 0:
            self._timer = self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self._remaining -= 1
        try:
            cd = self.query_one("#discard-countdown", Static)
            cd.update(f"⏱ {self._remaining}s")
        except Exception as exc:
            logger.debug("DiscardModal countdown refresh failed: %s", exc)
        if self._remaining <= 0:
            if self._timer:
                self._timer.stop()
            if self._timeout_auto_select:
                auto = list(range(len(self._cards) - self._need_count, len(self._cards)))
                self.dismiss(auto)
            else:
                self.dismiss(None)

    def _status_text(self) -> str:
        selected = len(self._selected)
        if selected < self._need_count:
            return f"[yellow]已选 {selected}/{self._need_count} 张[/yellow]"
        return f"[green]已选 {selected}/{self._need_count} 张 ✓[/green]"

    def _refresh_ui(self) -> None:
        """刷新选中状态."""
        try:
            self.query_one("#discard-status", Static).update(self._status_text())
        except Exception as exc:
            logger.debug("DiscardModal status refresh failed: %s", exc)

        # 更新按钮样式
        for i in range(len(self._cards)):
            try:
                btn = self.query_one(f"#dcard-{i}", Button)
                if i in self._selected:
                    btn.add_class("selected")
                    btn.variant = "error"
                else:
                    btn.remove_class("selected")
                    btn.variant = "default"
            except Exception as exc:
                logger.debug("DiscardModal card button refresh failed: %s", exc)

        # 更新确认按钮
        try:
            confirm = self.query_one("#btn-confirm-discard", Button)
            ok = len(self._selected) == self._need_count
            confirm.disabled = not ok
            confirm.label = f"{self._confirm_text} ({len(self._selected)}/{self._need_count})"
        except Exception as exc:
            logger.debug("DiscardModal confirm button refresh failed: %s", exc)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        if btn_id.startswith("dcard-"):
            idx = int(btn_id.split("-")[1])
            if idx in self._selected:
                self._selected.discard(idx)
            else:
                if len(self._selected) < self._need_count:
                    self._selected.add(idx)
            self._refresh_ui()

        elif btn_id == "btn-confirm-discard":
            if len(self._selected) == self._need_count:
                if self._timer:
                    self._timer.stop()
                self.dismiss(sorted(self._selected))
        elif btn_id == "btn-cancel-discard":
            if self._timer:
                self._timer.stop()
            self.dismiss(None)
