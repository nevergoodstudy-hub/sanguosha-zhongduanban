"""技能注册表与装饰器

提供统一的技能注册机制：

- 使用 @skill_handler("skill_id") 将处理函数注册到全局注册表
- get_registry() 返回不可变副本用于外部读取
- 防重复注册（后注册覆盖并记录警告）
"""
from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

# 运行期全局注册表：skill_id -> handler
_SKILL_REGISTRY: dict[str, Callable[..., bool]] = {}


def skill_handler(skill_id: str) -> Callable[[Callable[..., bool]], Callable[..., bool]]:
    """装饰器：注册技能处理函数到全局注册表。

    用法：
        @skill_handler("rende")
        def handle_rende(player, engine, **kwargs): ...
    """
    def _decorator(fn: Callable[..., bool]) -> Callable[..., bool]:
        if skill_id in _SKILL_REGISTRY:
            logger.warning("Skill handler for '%s' duplicated, overriding", skill_id)
        _SKILL_REGISTRY[skill_id] = fn
        return fn
    return _decorator


def get_registry() -> dict[str, Callable[..., bool]]:
    """获取当前注册的 skill handlers（浅拷贝，避免外部修改）。"""
    return dict(_SKILL_REGISTRY)
