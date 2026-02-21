"""Tests for the i18n module."""

import pytest

import i18n as i18n_mod
from i18n import get_available_locales, get_locale, set_locale, t


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

    def test_missing_key_returns_bracketed_key(self):
        result = t("nonexistent.key")
        assert result == "[nonexistent.key]"

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
        assert result != "ui.ask_shan.prompt"  # Should not return key
        # Should return template (with {name} unexpanded) rather than crash

    def test_multiple_params(self):
        set_locale("en_US")
        result = t("ui.ask_tao.prompt", dying="LiuBei", savior="ZhangFei")
        assert "LiuBei" in result
        assert "ZhangFei" in result


class TestStringTables:
    def test_zh_en_same_keys(self):
        """Both JSON locale tables must have exactly the same keys."""
        import json
        from pathlib import Path

        locale_dir = Path(__file__).parent.parent / "i18n"
        with open(locale_dir / "zh_CN.json", encoding="utf-8") as f:
            zh = json.load(f)
        with open(locale_dir / "en_US.json", encoding="utf-8") as f:
            en = json.load(f)
        zh_keys = {k for k in zh if not k.startswith("__")}
        en_keys = {k for k in en if not k.startswith("__")}
        assert zh_keys == en_keys, (
            f"Key mismatch: zh-only={zh_keys - en_keys}, en-only={en_keys - zh_keys}"
        )


class TestJSONLoading:
    """Test that JSON translation files are loaded correctly."""

    def test_json_loaded_over_py(self):
        """JSON files should be loaded in preference to .py files."""
        # Force reload by clearing cache
        i18n_mod._tables.clear()
        set_locale("zh_CN")
        # The JSON file has card.sha key that .py doesn't
        assert t("card.sha") == "杀"

    def test_json_has_more_keys_than_py(self):
        """JSON tables should have more keys than the old .py tables."""
        from i18n.zh_CN import STRINGS as py_table

        i18n_mod._tables.clear()
        set_locale("zh_CN")
        json_table = i18n_mod._tables["zh_CN"]
        assert len(json_table) > len(py_table)

    def test_meta_key_filtered(self):
        """__meta__ key should be filtered out."""
        i18n_mod._tables.clear()
        set_locale("zh_CN")
        table = i18n_mod._tables["zh_CN"]
        assert "__meta__" not in table


class TestUnderscoreAlias:
    """Test the _() convenience alias."""

    def test_underscore_is_t(self):
        from i18n import _ as translate

        set_locale("zh_CN")
        assert translate("ui.invalid_choice") == t("ui.invalid_choice")

    def test_underscore_with_params(self):
        from i18n import _ as translate

        set_locale("zh_CN")
        result = translate("ui.ask_shan.prompt", name="关羽")
        assert "关羽" in result


class TestCardName:
    """Test card_name() helper."""

    def test_card_name_by_id_zh(self):
        from i18n import card_name

        set_locale("zh_CN")
        assert card_name("sha") == "杀"
        assert card_name("nanman") == "南蛮入侵"
        assert card_name("qinglong") == "青龙偃月刀"

    def test_card_name_by_id_en(self):
        from i18n import card_name

        set_locale("en_US")
        assert card_name("sha") == "Strike"
        assert card_name("nanman") == "Barbarian Invasion"

    def test_card_name_reverse_lookup(self):
        """When given a Chinese name, reverse-lookup to find the key."""
        from i18n import card_name

        set_locale("zh_CN")
        assert card_name("杀") == "杀"  # 中文名反查

    def test_card_name_unknown(self):
        from i18n import card_name

        assert card_name("nonexistent") == "nonexistent"


class TestSkillName:
    """Test skill_name() helper."""

    def test_skill_name_zh(self):
        from i18n import skill_name

        set_locale("zh_CN")
        assert skill_name("wusheng") == "武圣"
        assert skill_name("rende") == "仁德"

    def test_skill_name_en(self):
        from i18n import skill_name

        set_locale("en_US")
        assert skill_name("wusheng") == "Warrior Saint"

    def test_skill_name_unknown(self):
        from i18n import skill_name

        assert skill_name("nonexistent") == "nonexistent"


class TestKingdomName:
    """Test kingdom_name() helper."""

    def test_kingdom_zh(self):
        from i18n import kingdom_name

        set_locale("zh_CN")
        assert kingdom_name("wei") == "魏"
        assert kingdom_name("shu") == "蜀"

    def test_kingdom_en(self):
        from i18n import kingdom_name

        set_locale("en_US")
        assert kingdom_name("wei") == "Wei"


class TestIdentityName:
    """Test identity_name() helper."""

    def test_identity_zh(self):
        from i18n import identity_name

        set_locale("zh_CN")
        assert identity_name("lord") == "主公"
        assert identity_name("rebel") == "反贼"

    def test_identity_en(self):
        from i18n import identity_name

        set_locale("en_US")
        assert identity_name("lord") == "Lord"


class TestIntegrationWithGame:
    """Test that game modules use i18n correctly."""

    def test_get_skill_chinese_name_uses_i18n(self):
        from game.constants import get_skill_chinese_name

        set_locale("zh_CN")
        assert get_skill_chinese_name("wusheng") == "武圣"
        set_locale("en_US")
        assert get_skill_chinese_name("wusheng") == "Warrior Saint"

    def test_kingdom_chinese_name_uses_i18n(self):
        from game.hero import Kingdom

        set_locale("zh_CN")
        assert Kingdom.WEI.chinese_name == "魏"
        set_locale("en_US")
        assert Kingdom.WEI.chinese_name == "Wei"

    def test_identity_chinese_name_uses_i18n(self):
        from game.player import Identity

        set_locale("zh_CN")
        assert Identity.LORD.chinese_name == "主公"
        set_locale("en_US")
        assert Identity.LORD.chinese_name == "Lord"

    def test_winner_message_uses_i18n(self):
        from game.engine import GameEngine
        from game.player import Identity

        engine = GameEngine()
        engine.winner_identity = Identity.LORD
        set_locale("zh_CN")
        assert engine.get_winner_message() == "主公和忠臣获胜！"
        set_locale("en_US")
        assert engine.get_winner_message() == "Lord and Loyalists win!"


class TestKeyCompleteness:
    """Validate all expected key namespaces are present."""

    def test_card_keys_complete(self):
        """All CardName constants should have i18n keys."""
        import json
        from pathlib import Path

        locale_dir = Path(__file__).parent.parent / "i18n"
        with open(locale_dir / "zh_CN.json", encoding="utf-8") as f:
            zh = json.load(f)
        card_keys = [k for k in zh if k.startswith("card.")]
        assert len(card_keys) >= 30  # at least 30 card names

    def test_skill_keys_complete(self):
        import json
        from pathlib import Path

        locale_dir = Path(__file__).parent.parent / "i18n"
        with open(locale_dir / "zh_CN.json", encoding="utf-8") as f:
            zh = json.load(f)
        skill_keys = [k for k in zh if k.startswith("skill.")]
        assert len(skill_keys) >= 34  # at least 34 skill names

    def test_all_namespaces_present(self):
        import json
        from pathlib import Path

        locale_dir = Path(__file__).parent.parent / "i18n"
        with open(locale_dir / "zh_CN.json", encoding="utf-8") as f:
            zh = json.load(f)
        prefixes = {k.split(".")[0] for k in zh if not k.startswith("__")}
        for ns in [
            "ui",
            "main",
            "card",
            "skill",
            "kingdom",
            "identity",
            "game",
            "controller",
            "error",
            "hero",
            "player",
        ]:
            assert ns in prefixes, f"Missing namespace: {ns}"
