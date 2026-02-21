"""性能分析工具 (P3-4)

提供 @timed 装饰器和全局 metrics 收集，
用于识别热路径和性能瓶颈。

用法:
    from tools.profiling import timed, report_metrics, reset_metrics

    @timed
    def expensive_function():
        ...

    # 查看报告
    report = report_metrics()
"""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger("sanguosha.perf")

# 全局 metrics 存储
_metrics: dict[str, list[float]] = {}

F = TypeVar("F", bound=Callable[..., Any])

# 慢调用阈值 (秒)
_SLOW_THRESHOLD: float = 0.1


def timed(func: F) -> F:
    """装饰器：记录函数执行时间。

    超过阈值的调用会记录 WARNING 级别日志。
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        name = f"{func.__module__}.{func.__qualname__}"
        _metrics.setdefault(name, []).append(elapsed)
        if elapsed > _SLOW_THRESHOLD:
            logger.warning("SLOW: %s took %.3fs", name, elapsed)
        return result

    return wrapper  # type: ignore[return-value]


def report_metrics() -> dict[str, dict[str, float]]:
    """生成性能报告。

    Returns:
        按函数名组织的指标字典，包含 calls, total_ms, avg_ms, max_ms。
    """
    report: dict[str, dict[str, float]] = {}
    for name, times in _metrics.items():
        report[name] = {
            "calls": len(times),
            "total_ms": sum(times) * 1000,
            "avg_ms": (sum(times) / len(times)) * 1000 if times else 0,
            "max_ms": max(times) * 1000 if times else 0,
        }
    return report


def reset_metrics() -> None:
    """清空所有已收集的指标。"""
    _metrics.clear()


def get_raw_metrics() -> dict[str, list[float]]:
    """获取原始指标数据（用于高级分析）。"""
    return _metrics
