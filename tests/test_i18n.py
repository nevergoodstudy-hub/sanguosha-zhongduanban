# -*- coding: utf-8 -*-
"""Tests for the i18n module."""

import pytest

from i18n import t, set_locale, get_locale, get_available_locales
import i18n as i18n_mod


@pytest.fixture(autouse=True)
def _reset_locale():
    """Reset locale to zh_CN after each test."""
    original = get_locale()
    yield
    set_locale(original)


class TestSetLocale:
    def test_default_locale(self):
        assert get_locale() == "zh_CN"

    def test_switch_to_en(self):
        set_locale("en_US")
        assert get_locale() == "en_US"

    def test_invalid_locale(self):
        with pytest.raises(ValueError, match="Unsupported locale"):
            set_locale("ja_JP")

    def test_available_locales(self):
        locales = get_available_locales()
        assert "zh_CN" in locales
        assert "en_US" in locales


class TestTranslation:
    def test_basic_key_zh(self):
        set_locale("zh_CN")
        assert t("ui.invalid_choice") == "无效选择"

    def test_basic_key_en(self):
        set_locale("en_US")
        assert t("ui.invalid_choice") == "Invalid choice"

    def test_format_params(self):
        set_locale("zh_CN")
        result = t("ui.ask_shan.prompt", name="关羽")
        assert "关羽" in result
        assert "闪" in result

    def test_format_params_en(self):
        set_locale("en_US")
        result = t("ui.ask_shan.prompt", name="GuanYu")
        assert "GuanYu" in result
        assert "Dodge" in result

    def test_missing_key_returns_key(self):
        result = t("nonexistent.key")
        assert result == "nonexistent.key"

    def test_fallback_to_zh_CN(self):
        """When en_US is missing a key, fall back to zh_CN."""
        set_locale("en_US")
        # Manually remove a key from en_US table to test fallback
        en_table = i18n_mod._tables.get("en_US", {})
        saved = en_table.pop("ui.invalid_choice", None)
        try:
            result = t("ui.invalid_choice")
            assert result == "无效选择"  # Falls back to zh_CN
        finally:
            if saved is not None:
                en_table["ui.invalid_choice"] = saved

    def test_format_map_missing_param_returns_template(self):
        """If format param is missing, return template without crash."""
        set_locale("zh_CN")
        result = t("ui.ask_shan.prompt")  # Missing 'name' param
        assert "ui.ask_shan.prompt" != result  # Should not return key
        # Should return template (with {name} unexpanded) rather than crash

    def test_multiple_params(self):
        set_locale("en_US")
        result = t("ui.ask_tao.prompt", dying="LiuBei", savior="ZhangFei")
        assert "LiuBei" in result
        assert "ZhangFei" in result


class TestStringTables:
    def test_zh_en_same_keys(self):
        """Both locale tables must have exactly the same keys."""
        from i18n.zh_CN import STRINGS as zh
        from i18n.en_US import STRINGS as en
        assert set(zh.keys()) == set(en.keys())
