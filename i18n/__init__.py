# -*- coding: utf-8 -*-
"""
轻量级 i18n 框架 — 零外部依赖。

用法::

    from i18n import t, set_locale

    set_locale("en_US")
    print(t("ui.ask_shan", name="关羽"))
"""

from __future__ import annotations

from typing import Dict

# 延迟导入翻译表，避免循环
_locale: str = "zh_CN"
_tables: Dict[str, Dict[str, str]] = {}


def _load_table(locale: str) -> Dict[str, str]:
    """按需加载翻译表。"""
    if locale == "zh_CN":
        from .zh_CN import STRINGS
    elif locale == "en_US":
        from .en_US import STRINGS
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
