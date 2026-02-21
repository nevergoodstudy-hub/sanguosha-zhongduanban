"""集中式日志配置 (P2-3)

提供 setup_logging() 统一初始化日志格式和级别。
支持文本和 JSON 两种格式。

用法:
    from tools.log_config import setup_logging
    setup_logging(level="DEBUG")           # 文本格式
    setup_logging(level="INFO", json_format=True)  # JSON 格式
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


# 默认格式
TEXT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class JsonFormatter(logging.Formatter):
    """JSON 格式化器，用于结构化日志输出。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
    log_file: str | None = None,
) -> None:
    """初始化全局日志配置。

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        json_format: 是否使用 JSON 格式
        log_file: 日志输出文件路径 (None 则仅输出到 stderr)
    """
    root = logging.getLogger()

    # 避免重复 handler
    if root.handlers:
        return

    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 格式化器
    formatter: logging.Formatter
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(TEXT_FORMAT, datefmt=DATE_FORMAT)

    # stderr handler
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    root.addHandler(console)

    # 文件 handler
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # 降低第三方库噪音
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
