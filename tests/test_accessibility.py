"""可访问性与主题系统测试 (P3-5)"""

from __future__ import annotations

import pytest

from ui.textual_ui.themes import THEMES, ThemeColors, ThemeManager


class TestThemeColors:
    """ThemeColors 数据类测试。"""

    def test_default_values(self):
        c = ThemeColors()
        assert c.background == "#1e1e2e"
        assert c.text == "#cdd6f4"
        assert c.hp_full == "#a6e3a1"

    def test_custom_values(self):
        c = ThemeColors(background="#000", text="#fff")
        assert c.background == "#000"
        assert c.text == "#fff"


class TestThemePresets:
    """预设主题测试。"""

    def test_all_presets_exist(self):
        assert "default" in THEMES
        assert "high_contrast" in THEMES
        assert "dark" in THEMES

    def test_high_contrast_uses_pure_black_white(self):
        hc = THEMES["high_contrast"]
        assert hc.background == "#000000"
        assert hc.text == "#ffffff"
        assert hc.border == "#ffffff"

    def test_all_themes_have_required_fields(self):
        required = [
            "background",
            "surface",
            "text",
            "text_muted",
            "primary",
            "secondary",
            "accent",
            "error",
            "warning",
            "success",
            "border",
            "hp_full",
            "hp_half",
            "hp_low",
        ]
        for name, colors in THEMES.items():
            for field in required:
                assert hasattr(colors, field), f"{name} 缺少 {field}"
                val = getattr(colors, field)
                assert val.startswith("#"), f"{name}.{field} = {val} 不是颜色值"


class TestThemeManager:
    """ThemeManager 测试。"""

    def test_default_theme(self):
        m = ThemeManager()
        assert m.current_theme == "default"
        assert m.colors.background == "#1e1e2e"

    def test_init_with_theme(self):
        m = ThemeManager("high_contrast")
        assert m.current_theme == "high_contrast"

    def test_init_unknown_falls_back(self):
        m = ThemeManager("nonexistent")
        assert m.current_theme == "default"

    def test_set_theme(self):
        m = ThemeManager()
        assert m.set_theme("dark") is True
        assert m.current_theme == "dark"

    def test_set_unknown_theme(self):
        m = ThemeManager()
        assert m.set_theme("nonexistent") is False
        assert m.current_theme == "default"

    def test_get_css_returns_string(self):
        m = ThemeManager()
        css = m.get_css()
        assert isinstance(css, str)
        assert "background" in css
        assert "color" in css

    def test_get_css_uses_current_theme_colors(self):
        m = ThemeManager("high_contrast")
        css = m.get_css()
        assert "#000000" in css  # background
        assert "#ffffff" in css  # text

    def test_available_themes(self):
        themes = ThemeManager.available_themes()
        assert "default" in themes
        assert "high_contrast" in themes
        assert "dark" in themes

    def test_is_high_contrast(self):
        m = ThemeManager()
        assert m.is_high_contrast() is False
        m.set_theme("high_contrast")
        assert m.is_high_contrast() is True

    def test_get_hp_color(self):
        m = ThemeManager()
        c = m.colors
        # Full HP
        assert m.get_hp_color(1.0) == c.hp_full
        assert m.get_hp_color(0.6) == c.hp_full
        # Half HP
        assert m.get_hp_color(0.5) == c.hp_half
        assert m.get_hp_color(0.3) == c.hp_half
        # Low HP
        assert m.get_hp_color(0.25) == c.hp_low
        assert m.get_hp_color(0.0) == c.hp_low

    def test_get_hp_color_high_contrast(self):
        m = ThemeManager("high_contrast")
        assert m.get_hp_color(1.0) == "#00ff00"
        assert m.get_hp_color(0.4) == "#ffff00"
        assert m.get_hp_color(0.1) == "#ff0000"
