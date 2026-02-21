"""HandCardRow — 手牌行容器

Horizontal 滚动容器，内含 CardWidget 实例。
支持刷新手牌和接收 CardClicked 消息。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.containers import HorizontalScroll
from textual.message import Message

from ui.textual_ui.widgets.card_widget import CardWidget

if TYPE_CHECKING:
    pass


class HandCardRow(HorizontalScroll):
    """手牌行容器"""

    DEFAULT_CSS = """
    HandCardRow {
        height: auto;
        min-height: 6;
        max-height: 8;
    }
    """

    class HandCardClicked(Message):
        """手牌区卡牌被点击"""

        def __init__(self, index: int, card=None) -> None:
            super().__init__()
            self.index = index
            self.card = card

    def update_hand(self, cards: list) -> None:
        """刷新手牌显示"""
        self.remove_children()
        for i, card in enumerate(cards):
            widget = CardWidget(card, index=i)
            self.mount(widget)

    def on_card_widget_card_clicked(self, event: CardWidget.CardClicked) -> None:
        """将 CardWidget 的点击事件冒泡为 HandCardClicked"""
        self.post_message(self.HandCardClicked(event.index, event.card))
