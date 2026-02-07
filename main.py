# -*- coding: utf-8 -*-
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
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

from logging_config import setup_logging

__version__ = pkg_version("sanguosha") if __name__ != "__main__" else "3.0.0"

logger = logging.getLogger(__name__)

# 确保可以导入项目模块
sys.path.insert(0, str(Path(__file__).parent))

# 向后兼容：旧代码可能引用 SanguoshaGame
from game.game_controller import GameController as SanguoshaGame  # noqa: F401


def main():
    """程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="三国杀 - 命令行终端版 (Textual TUI)")
    # M4: 网络对战参数
    parser.add_argument(
        "--server",
        nargs="?",
        const="0.0.0.0:8765",
        default=None,
        help="启动服务端 (默认 0.0.0.0:8765)",
    )
    parser.add_argument(
        "--connect",
        default=None,
        metavar="HOST:PORT",
        help="连接到服务端 (如 localhost:8765)",
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

    # M4: 服务端模式
    if args.server is not None:
        import asyncio
        from net.server import GameServer
        host, _, port = args.server.partition(":")
        host = host or "0.0.0.0"
        port = int(port) if port else 8765
        server = GameServer(host=host, port=port)
        asyncio.run(server.start())
        return

    # M4: 客户端模式
    if args.connect is not None:
        import asyncio
        from net.client import cli_client_main
        url = f"ws://{args.connect}"
        name = args.name or "玩家"
        asyncio.run(cli_client_main(url, name))
        return

    # 回放模式
    if args.replay is not None:
        from game.save_system import load_game, EnhancedReplay
        from ui.input_safety import safe_input
        import time as _time

        data = load_game(args.replay)
        replay = EnhancedReplay(data)
        summary = replay.get_summary()

        print(f"\u25b6 回放: {args.replay}")
        print(f"  玩家数: {summary['player_count']}  "
              f"回合数: {summary['round_count']}  "
              f"动作数: {summary['total_steps']}  "
              f"种子: {summary['seed']}")

        while True:
            action = replay.step_forward()
            if action is None:
                break
            step = replay.current_step
            total = replay.total_steps
            a_type = action.get('action_type', '?')
            pid = action.get('player_id', '?')
            detail = action.get('data', {})
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
