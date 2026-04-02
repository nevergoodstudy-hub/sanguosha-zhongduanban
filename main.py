"""三国杀 - 命令行终端版.

主程序入口

使用方法:
    python main.py
    python main.py --server [HOST:PORT]
    python main.py --connect HOST:PORT
    python main.py --replay FILE

依赖:
    - Python 3.10+
    - rich / textual
"""

import logging
import os
import sys
import warnings
from pathlib import Path

from logging_config import setup_logging
from versioning import get_project_version

__version__ = get_project_version()

logger = logging.getLogger(__name__)

__all__ = ["main", "__version__", "normalize_connect_url"]


def __getattr__(name: str):
    """延迟暴露 legacy 控制器别名，避免主入口继续直接耦合旧 GameController."""
    if name == "SanguoshaGame":
        warnings.warn(
            "main.SanguoshaGame 是 legacy 兼容别名；请改用 game.game_controller.GameController。",
            DeprecationWarning,
            stacklevel=2,
        )
        from game.game_controller import GameController

        return GameController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def normalize_connect_url(connect: str) -> str:
    """Normalize --connect parameter into a WebSocket URL.

    Raises:
        ValueError: 当输入为空、scheme 不合法、host 缺失或端口非法时。
    """
    from urllib.parse import urlsplit

    normalized = connect.strip()
    if not normalized:
        raise ValueError("--connect value cannot be empty")

    if normalized.startswith(("http://", "https://")):
        raise ValueError("--connect must start with ws:// or wss://")

    if not normalized.startswith(("ws://", "wss://")):
        normalized = f"ws://{normalized}"

    parsed = urlsplit(normalized)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError("--connect must start with ws:// or wss://")

    if not parsed.hostname:
        raise ValueError("--connect missing host")

    netloc_no_auth = parsed.netloc.rsplit("@", 1)[-1]
    if netloc_no_auth.startswith("["):
        right_bracket = netloc_no_auth.find("]")
        port_str = netloc_no_auth[right_bracket + 2 :] if right_bracket != -1 and netloc_no_auth[right_bracket + 1 : right_bracket + 2] == ":" else ""
    else:
        port_str = netloc_no_auth.rsplit(":", 1)[1] if ":" in netloc_no_auth else ""

    if port_str and not port_str.isdigit():
        raise ValueError("--connect port must be numeric")

    try:
        _ = parsed.port
    except ValueError as exc:
        msg = str(exc)
        if "out of range" in msg:
            raise ValueError("--connect port must be in 1-65535") from exc
        raise ValueError("--connect port must be numeric") from exc

    return normalized


def _validate_runtime_layout() -> list[str]:
    """Validate current working directory layout for predictable startup."""
    cwd = Path.cwd()
    required_paths = [
        cwd / "main.py",
        cwd / "pyproject.toml",
        cwd / "data",
        cwd / "game",
        cwd / "ui",
    ]
    missing = [str(path.name) for path in required_paths if not path.exists()]
    return missing


def _warn_if_runtime_layout_suspicious() -> None:
    """Warn when startup is executed outside the project root directory."""
    missing = _validate_runtime_layout()
    if missing:
        logger.warning(
            "Current working directory may not be project root: missing %s",
            ", ".join(missing),
        )
        print(
            "[WARN] 当前运行目录可能不是项目根目录，缺少: "
            f"{', '.join(missing)}\n"
            "       建议先切换到项目目录再运行，例如:\n"
            "       cd sanguosha_backup_20260121_071454"
        )


def _warn_for_network_security_defaults() -> None:
    """Show explicit runtime warnings for common networking misconfigurations."""
    if not os.environ.get("SANGUOSHA_WS_ALLOWED_ORIGINS", "").strip():
        if os.environ.get("SANGUOSHA_DEV_ALLOW_LOCALHOST", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            print(
                "[WARN] 未设置 SANGUOSHA_WS_ALLOWED_ORIGINS，"
                "但已启用 SANGUOSHA_DEV_ALLOW_LOCALHOST。\n"
                "       当前仅开发态 localhost/127.0.0.1/::1 Origin 可连接。"
            )
        else:
            print(
                "[WARN] 未设置 SANGUOSHA_WS_ALLOWED_ORIGINS。"
                "服务端将拒绝所有 WebSocket 连接（安全默认）。\n"
                "       例如设置:"
                " SANGUOSHA_WS_ALLOWED_ORIGINS=http://localhost:3000"
            )


def _warn_for_tls_if_needed() -> None:
    """Warn operator when server runs without TLS certificate/key."""
    cert = os.environ.get("SANGUOSHA_WS_SSL_CERT", "").strip()
    key = os.environ.get("SANGUOSHA_WS_SSL_KEY", "").strip()
    if not cert or not key:
        print(
            "[WARN] 未配置 TLS 证书（SANGUOSHA_WS_SSL_CERT / SANGUOSHA_WS_SSL_KEY），"
            "当前将使用 ws:// 明文传输。"
        )


def main():
    """程序入口."""
    import argparse

    parser = argparse.ArgumentParser(description="三国杀 - 命令行终端版 (Textual TUI)")
    # M4: 网络对战参数
    parser.add_argument(
        "--server",
        nargs="?",
        const="127.0.0.1:8765",
        default=None,
        help="启动服务端 (默认 127.0.0.1:8765)",
    )
    parser.add_argument(
        "--connect",
        default=None,
        metavar="HOST:PORT|WS_URL",
        help="连接到服务端 (如 localhost:8765 / ws://localhost:8765 / wss://game.example.com)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="网络对战时的玩家名称",
    )
    parser.add_argument(
        "--lang",
        choices=["zh_CN", "en_US"],
        default="zh_CN",
        help="语言/Language: zh_CN(默认) / en_US",
    )
    parser.add_argument(
        "--replay",
        default=None,
        metavar="FILE",
        help="回放存档文件 (JSON)",
    )
    parser.add_argument(
        "--step",
        action="store_true",
        help="回放时逐步执行",
    )
    args = parser.parse_args()

    # 设置语言
    from i18n import set_locale

    set_locale(args.lang)

    setup_logging(enable_console=False)
    _warn_if_runtime_layout_suspicious()

    # M4: 服务端模式
    if args.server is not None:
        import asyncio

        from game.config import get_config
        from net.server import GameServer

        cfg = get_config()
        config_errors = cfg.validate()
        if config_errors:
            print("[ERROR] 配置校验失败:")
            for error in config_errors:
                print(f"  - {error}")
            sys.exit(2)

        for warning in cfg.validate_warnings():
            print(f"[WARN] {warning}")

        _warn_for_network_security_defaults()
        _warn_for_tls_if_needed()
        host, _, port = args.server.partition(":")
        host = host or "127.0.0.1"
        port = int(port) if port else 8765
        server = GameServer(
            host=host,
            port=port,
            rate_limit_window=cfg.ws_rate_limit_window,
            rate_limit_max_msgs=cfg.ws_rate_limit_max_msgs,
            max_connections=cfg.ws_max_connections,
            max_connections_per_ip=cfg.ws_max_connections_per_ip,
            max_message_size=cfg.ws_max_message_size,
            heartbeat_timeout=cfg.ws_heartbeat_timeout,
            allowed_origins=cfg.ws_allowed_origins,
            allow_localhost_dev=cfg.ws_dev_allow_localhost,
            ssl_cert=cfg.ws_ssl_cert,
            ssl_key=cfg.ws_ssl_key,
        )
        asyncio.run(server.start())
        return

    # M4: 客户端模式
    if args.connect is not None:
        import asyncio

        from net.client import cli_client_main

        try:
            url = normalize_connect_url(args.connect)
        except ValueError as exc:
            print(f"[ERROR] --connect 参数无效: {exc}")
            sys.exit(2)

        name = args.name or "玩家"
        asyncio.run(cli_client_main(url, name))
        return

    # 回放模式
    if args.replay is not None:
        import time as _time

        from game.save_system import EnhancedReplay, load_game
        from ui.input_safety import safe_input

        data = load_game(args.replay)
        replay = EnhancedReplay(data)
        summary = replay.get_summary()

        print(f"\u25b6 回放: {args.replay}")
        print(
            f"  玩家数: {summary['player_count']}  "
            f"回合数: {summary['round_count']}  "
            f"动作数: {summary['total_steps']}  "
            f"种子: {summary['seed']}"
        )

        while True:
            action = replay.step_forward()
            if action is None:
                break
            step = replay.current_step
            total = replay.total_steps
            a_type = action.get("action_type", "?")
            pid = action.get("player_id", "?")
            detail = action.get("data", {})
            print(f"[{step}/{total}] {a_type} by Player {pid}  {detail}")
            if args.step:
                safe_input("")
            else:
                _time.sleep(replay.delay)

        print(f"\n\u2714 回放完成 ({summary['progress']})")
        return

    # 默认: Textual TUI 模式
    try:
        from ui.textual_ui import SanguoshaApp

        app = SanguoshaApp()
        app.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt - exiting")
        from i18n import t

        print(t("main.interrupted"))
        sys.exit(0)
    except Exception as e:
        logger.exception("Unhandled exception")
        from i18n import t

        print(t("main.error", error=e))
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
