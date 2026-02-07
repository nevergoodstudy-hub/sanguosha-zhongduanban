# -*- coding: utf-8 -*-
"""
AnimatedModalScreen — 带淡入动画的 ModalScreen 基类 (P1-2)

所有游戏弹窗应继承此基类，以获得：
- 推入时 opacity 0%→100% 的淡入效果 (0.3s, out_cubic)
- 子类可覆盖 FADE_DURATION / FADE_EASING 自定义

技术说明:
- 基于 Textual styles.animate("opacity") API
- 参考 Textual GitHub Discussion #2611 推荐模式
"""

from __future__ import annotations

from typing import TypeVar

from textual.screen import ModalScreen

T = TypeVar("T")


class AnimatedModalScreen(ModalScreen[T]):
    """带淡入效果的 ModalScreen 基类"""

    # 子类可覆盖
    FADE_DURATION: float = 0.3
    FADE_EASING: str = "out_cubic"

    DEFAULT_CSS = """
    AnimatedModalScreen {
        opacity: 0%;
    }
    """

    def on_mount(self) -> None:
        """推入屏幕时执行淡入动画"""
        self.styles.animate(
            "opacity",
            value=1.0,
            duration=self.FADE_DURATION,
            easing=self.FADE_EASING,
        )
