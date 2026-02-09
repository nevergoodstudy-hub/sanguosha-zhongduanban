"""技能处理器包 — 按势力拆分

将原 skill.py 中 30+ 个 _handle_xxx 方法拆分到按势力组织的子模块：
  - shu.py  : 蜀国武将技能 (13 个)
  - wei.py  : 魏国武将技能 (9 个)
  - wu.py   : 吴国武将技能 (11 个)
  - qun.py  : 群雄武将技能 (5 个)

每个子模块导出 XXX_HANDLERS 字典 (skill_id -> handler function)，
本模块负责合并并提供统一的 get_all_skill_handlers() 入口。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Dict

from . import qun as _qun  # noqa: F401

# 导入子模块以触发装饰器副作用（注册处理器）
from . import shu as _shu  # noqa: F401
from . import wei as _wei  # noqa: F401
from . import wu as _wu  # noqa: F401

# 装饰器注册机制
from .registry import get_registry, skill_handler  # re-export for convenience

# 兼容：仍然导出各势力字典（若存在），便于外部排查/迁移
try:
    from .shu import SHU_HANDLERS  # type: ignore
except Exception:  # pragma: no cover - 兼容未定义
    SHU_HANDLERS = {}
try:
    from .wei import WEI_HANDLERS  # type: ignore
except Exception:  # pragma: no cover
    WEI_HANDLERS = {}
try:
    from .wu import WU_HANDLERS  # type: ignore
except Exception:  # pragma: no cover
    WU_HANDLERS = {}
try:
    from .qun import QUN_HANDLERS  # type: ignore
except Exception:  # pragma: no cover
    QUN_HANDLERS = {}


def get_all_skill_handlers() -> dict[str, Callable[..., bool]]:
    """优先返回装饰器注册表；若为空则回退合并各势力字典。"""
    reg = get_registry()
    if reg:
        return reg
    handlers: dict[str, Callable[..., bool]] = {}
    handlers.update(SHU_HANDLERS)
    handlers.update(WEI_HANDLERS)
    handlers.update(WU_HANDLERS)
    handlers.update(QUN_HANDLERS)
    return handlers


__all__ = [
    "SHU_HANDLERS",
    "WEI_HANDLERS",
    "WU_HANDLERS",
    "QUN_HANDLERS",
    "get_all_skill_handlers",
    "skill_handler",
]
