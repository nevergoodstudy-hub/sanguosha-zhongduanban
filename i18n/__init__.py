"""轻量级 i18n 框架 — 零外部依赖。

用法::

    from i18n import t, set_locale

    set_locale("en_US")
    print(t("ui.ask_shan", name="关羽"))

    # 便捷别名
    from i18n import _
    print(_("card.sha"))  # → "Strike" (en_US) / "杀" (zh_CN)

    # 领域助手
    from i18n import card_name, skill_name, kingdom_name, identity_name
    print(card_name("sha"))        # → "杀" / "Strike"
    print(skill_name("wusheng"))   # → "武圣" / "Warrior Saint"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

_LOCALE_DIR = Path(__file__).parent

# 延迟导入翻译表，避免循环
_locale: str = "zh_CN"
_tables: dict[str, dict[str, str]] = {}


def _load_table(locale: str) -> dict[str, str]:
    """按需加载翻译表。优先 JSON，回退到旧 .py 模块。"""
    json_path = _LOCALE_DIR / f"{locale}.json"
    if json_path.exists():
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        # 过滤掉 __meta__ 等非翻译键
        return {k: v for k, v in data.items() if not k.startswith("__")}

    # 回退: 兼容旧 .py 格式
    if locale == "zh_CN":
        from .zh_CN import STRINGS  # type: ignore[import-untyped]
    elif locale == "en_US":
        from .en_US import STRINGS  # type: ignore[import-untyped]
    else:
        raise ValueError(f"Unsupported locale: {locale}")
    return STRINGS


def set_locale(locale: str) -> None:
    """设置当前语言。"""
    global _locale
    # 预加载以确保 locale 有效
    if locale not in _tables:
        _tables[locale] = _load_table(locale)
    _locale = locale


def get_locale() -> str:
    """获取当前语言。"""
    return _locale


def get_available_locales() -> list[str]:
    """返回所有可用的 locale 列表。"""
    return ["zh_CN", "en_US"]


def t(key: str, **kwargs: object) -> str:
    """翻译函数。

    查找当前 locale 对应的字符串，用 ``kwargs`` 做 format 替换。
    若 key 缺失则回退到 zh_CN，仍缺失则原样返回 key。

    Args:
        key: 翻译键，如 ``"ui.ask_shan"``。
        **kwargs: 格式化参数，如 ``name="关羽"``。
    """
    # 确保当前 locale 表已加载
    if _locale not in _tables:
        _tables[_locale] = _load_table(_locale)

    table = _tables[_locale]
    template = table.get(key)

    # 回退到 zh_CN
    if template is None and _locale != "zh_CN":
        if "zh_CN" not in _tables:
            _tables["zh_CN"] = _load_table("zh_CN")
        template = _tables["zh_CN"].get(key)

    if template is None:
        return key

    if kwargs:
        try:
            return template.format_map(kwargs)
        except KeyError:
            return template
    return template


# ── 便捷别名 ──
_ = t


# ── 领域助手函数 ──

def card_name(card_id: str) -> str:
    """获取卡牌的国际化显示名。

    Args:
        card_id: 卡牌标识符，如 ``"sha"``、``"nanman"``。
                 也接受中文原名（会自动反查）。
    """
    key = f"card.{card_id}"
    result = t(key)
    if result != key:
        return result

    # 尝试通过中文名反查 (兼容旧代码用中文名调用)
    if _locale not in _tables:
        _tables[_locale] = _load_table(_locale)
    zh_table = _tables.get("zh_CN")
    if zh_table is None:
        zh_table = _load_table("zh_CN")
        _tables["zh_CN"] = zh_table
    for k, v in zh_table.items():
        if k.startswith("card.") and v == card_id:
            return t(k)

    return card_id  # 未找到则原样返回


def skill_name(skill_id: str) -> str:
    """获取技能的国际化显示名。

    Args:
        skill_id: 技能标识符，如 ``"wusheng"``、``"rende"``。
    """
    key = f"skill.{skill_id}"
    result = t(key)
    return result if result != key else skill_id


def kingdom_name(value: str) -> str:
    """获取势力的国际化显示名。

    Args:
        value: 势力值，如 ``"wei"``、``"shu"``。
    """
    key = f"kingdom.{value}"
    result = t(key)
    return result if result != key else value


def identity_name(value: str) -> str:
    """获取身份的国际化显示名。

    Args:
        value: 身份值，如 ``"lord"``、``"rebel"``。
    """
    key = f"identity.{value}"
    result = t(key)
    return result if result != key else value
