"""UI 主题管理器 (P3-5 可访问性)

提供高对比度主题切换，改善视觉辅助需求。
支持 default / high_contrast / dark 三种预设主题。

用法:
    manager = ThemeManager()
    manager.set_theme("high_contrast")
    css = manager.get_css()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ThemeColors:
    """主题配色方案。"""

    background: str = "#1e1e2e"
    surface: str = "#282840"
    text: str = "#cdd6f4"
    text_muted: str = "#6c7086"
    primary: str = "#89b4fa"
    secondary: str = "#a6e3a1"
    accent: str = "#f5c2e7"
    error: str = "#f38ba8"
    warning: str = "#fab387"
    success: str = "#a6e3a1"
    border: str = "#45475a"
    hp_full: str = "#a6e3a1"
    hp_half: str = "#f9e2af"
    hp_low: str = "#f38ba8"


# 预设主题
THEMES: dict[str, ThemeColors] = {
    "default": ThemeColors(),
    "high_contrast": ThemeColors(
        background="#000000",
        surface="#1a1a1a",
        text="#ffffff",
        text_muted="#cccccc",
        primary="#00aaff",
        secondary="#00ff00",
        accent="#ff00ff",
        error="#ff0000",
        warning="#ffaa00",
        success="#00ff00",
        border="#ffffff",
        hp_full="#00ff00",
        hp_half="#ffff00",
        hp_low="#ff0000",
    ),
    "dark": ThemeColors(
        background="#0d1117",
        surface="#161b22",
        text="#e6edf3",
        text_muted="#7d8590",
        primary="#58a6ff",
        secondary="#3fb950",
        accent="#d2a8ff",
        error="#f85149",
        warning="#d29922",
        success="#3fb950",
        border="#30363d",
        hp_full="#3fb950",
        hp_half="#d29922",
        hp_low="#f85149",
    ),
}


class ThemeManager:
    """主题管理器。

    管理 Textual CSS 变量式主题切换。
    高对比度模式使用更鲜明的颜色边界、纯黑背景和纯白文本，
    符合 WCAG 2.1 AA 级别的对比度要求。
    """

    def __init__(self, theme_name: str = "default") -> None:
        self._current = theme_name
        if theme_name not in THEMES:
            logger.warning("未知主题 '%s'，使用 default", theme_name)
            self._current = "default"

    @property
    def current_theme(self) -> str:
        return self._current

    @property
    def colors(self) -> ThemeColors:
        return THEMES[self._current]

    def set_theme(self, name: str) -> bool:
        """切换主题。返回是否成功。"""
        if name not in THEMES:
            logger.warning("未知主题: %s", name)
            return False
        self._current = name
        return True

    def get_css(self) -> str:
        """生成当前主题的 Textual CSS 变量覆盖。"""
        c = self.colors
        return f"""
        Screen {{
            background: {c.background};
            color: {c.text};
        }}
        Static {{
            color: {c.text};
        }}
        Button {{
            border: solid {c.border};
        }}
        Button:hover {{
            border: heavy {c.accent};
        }}
        """

    def get_hp_color(self, ratio: float) -> str:
        """根据 HP 比例返回对应颜色。"""
        c = self.colors
        if ratio > 0.5:
            return c.hp_full
        if ratio > 0.25:
            return c.hp_half
        return c.hp_low

    @staticmethod
    def available_themes() -> list[str]:
        """返回所有可用主题名。"""
        return list(THEMES.keys())

    def is_high_contrast(self) -> bool:
        """当前是否为高对比度模式。"""
        return self._current == "high_contrast"
