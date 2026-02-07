# -*- coding: utf-8 -*-
"""
安全输入模块
封装 input() 以优雅处理 EOFError 和 KeyboardInterrupt
"""


def safe_input(prompt: str = "", default: str = "") -> str:
    """input() 的安全封装，防止 EOFError / KeyboardInterrupt 导致崩溃。

    Args:
        prompt: 输入提示文字
        default: 当遇到 EOFError 时返回的默认值

    Returns:
        用户输入的字符串，或 EOFError 时的默认值

    Raises:
        SystemExit: 当用户按 Ctrl+C 时，执行干净退出
    """
    try:
        return input(prompt)
    except EOFError:
        # 管道关闭或无头环境 — 返回默认值
        return default
    except KeyboardInterrupt:
        # 用户按 Ctrl+C — 换行后干净退出
        print()
        raise SystemExit(0)
