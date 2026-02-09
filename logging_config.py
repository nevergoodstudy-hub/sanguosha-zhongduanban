"""Project-wide logging setup.

Design goals:
- Write logs to a UTF-8 file (safe for Chinese output).
- Avoid breaking the TUI by default (console logging is off unless enabled).
- Be idempotent: calling setup_logging() multiple times won't duplicate handlers.

Usage:
    from logging_config import setup_logging
    setup_logging()

Environment overrides:
    SANGUOSHA_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
    SANGUOSHA_LOG_FILE=path/to/file.log
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FILE_HANDLER_NAME = "sanguosha_file"
_CONSOLE_HANDLER_NAME = "sanguosha_console"


def _parse_level(level: str | int) -> int:
    if isinstance(level, int):
        return level

    level_str = (level or "").strip().upper()
    if not level_str:
        return logging.INFO

    return logging._nameToLevel.get(level_str, logging.INFO)


def setup_logging(
    *,
    level: str | int = "INFO",
    log_file: str | None = None,
    enable_file: bool = True,
    enable_console: bool = False,
    console_level: str | int = "WARNING",
    max_bytes: int = 2 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Logger:
    """Configure the root logger.

    Returns the root logger.
    """
    env_level = os.environ.get("SANGUOSHA_LOG_LEVEL")
    if env_level:
        level = env_level

    env_log_file = os.environ.get("SANGUOSHA_LOG_FILE")
    if env_log_file:
        log_file = env_log_file

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)  # let handlers filter

    # Format: timestamp level logger:line | message
    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Remove / update existing handlers with our names (idempotent)
    existing_by_name = {getattr(h, "name", ""): h for h in root.handlers}

    if enable_file:
        if not log_file:
            log_dir = Path("logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / "sanguosha.log"
        else:
            log_path = Path(log_file)
            if not log_path.is_absolute():
                log_path = Path.cwd() / log_path
            log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = existing_by_name.get(_FILE_HANDLER_NAME)
        if file_handler is None:
            file_handler = RotatingFileHandler(
                str(log_path),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.name = _FILE_HANDLER_NAME
            root.addHandler(file_handler)

        file_handler.setFormatter(fmt)
        file_handler.setLevel(_parse_level(level))

    if enable_console:
        console_handler = existing_by_name.get(_CONSOLE_HANDLER_NAME)
        if console_handler is None:
            console_handler = logging.StreamHandler()
            console_handler.name = _CONSOLE_HANDLER_NAME
            root.addHandler(console_handler)

        console_handler.setFormatter(fmt)
        console_handler.setLevel(_parse_level(console_level))

    logging.getLogger(__name__).info(
        "Logging initialized | level=%s file=%s console=%s",
        level,
        str(log_file) if log_file else "logs/sanguosha.log",
        enable_console,
    )

    return root
