"""GamePlayScreen 辅助函数.

将纯函数逻辑从 game_play.py 抽离，降低主屏幕文件复杂度。
"""

from __future__ import annotations

import re


def countdown_color(secs: int, total: int = 30) -> str:
    """根据剩余秒数计算 RGB 渐变色.

    green(#27ae60) → yellow(#f39c12) → red(#e74c3c)
    ratio > 0.5 时 green→yellow，ratio <= 0.5 时 yellow→red
    """
    ratio = max(0.0, min(1.0, secs / total))
    if ratio > 0.5:
        # green → yellow (ratio 1.0→0.5 maps to factor 0→1)
        f = (1.0 - ratio) * 2  # 0→1
        r = int(0x27 + (0xF3 - 0x27) * f)
        g = int(0xAE + (0x9C - 0xAE) * f)
        b = int(0x60 + (0x12 - 0x60) * f)
    else:
        # yellow → red (ratio 0.5→0 maps to factor 0→1)
        f = (0.5 - ratio) * 2  # 0→1
        r = int(0xF3 + (0xE7 - 0xF3) * f)
        g = int(0x9C + (0x4C - 0x9C) * f)
        b = int(0x12 + (0x3C - 0x12) * f)
    return f"#{r:02x}{g:02x}{b:02x}"


def parse_card_play_message(msg: str) -> tuple[str, str, str] | None:
    """解析 '玩家 对 目标 使用了【卡牌】' 或 '玩家 使用了【卡牌】'."""
    m = re.search(r"(.+?)\s+(?:对\s+(.+?)\s+)?使用[了]*【(.+?)】", msg)
    if not m:
        return None
    player_name = m.group(1).strip()
    target_name = m.group(2).strip() if m.group(2) else ""
    card_name = m.group(3).strip()
    return player_name, card_name, target_name


def parse_skill_message(msg: str) -> tuple[str, str] | None:
    """解析 '玩家 发动【技能】'."""
    m = re.search(r"(.+?)\s+发动【(.+?)】", msg)
    if not m:
        return None
    player_name = m.group(1).strip()
    skill_name = m.group(2).strip()
    return player_name, skill_name


def parse_damage_message(msg: str) -> tuple[str, int, str] | None:
    """解析伤害消息，返回(目标名, 伤害值, 伤害类型)."""
    m = re.search(r"(.+?)\s+受到[了]*\s*(\d+)\s*点", msg)
    if not m:
        return None

    target_name = m.group(1).strip()
    amount = int(m.group(2))
    dtype = ""
    if "火焰" in msg:
        dtype = "fire"
    elif "雷电" in msg:
        dtype = "thunder"
    return target_name, amount, dtype
