"""GamePlayScreen 辅助函数.

将纯函数与渲染片段从 game_play.py 抽离，降低主屏幕文件复杂度。
"""

from __future__ import annotations

import logging
import re
from typing import Any


logger = logging.getLogger(__name__)


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


def build_player_info_text(human) -> str:
    """构建右侧信息面板文本（从 screen 中抽离纯展示逻辑）."""
    hp_full = "●" * human.hp
    hp_empty = "[dim]○[/dim]" * (human.max_hp - human.hp)
    if human.hp <= 1:
        hp_bar = f"[red]{hp_full}[/red]" + hp_empty
    elif human.hp <= human.max_hp // 2:
        hp_bar = f"[yellow]{hp_full}[/yellow]" + hp_empty
    else:
        hp_bar = f"[green]{hp_full}[/green]" + hp_empty

    skills_lines = ""
    if human.hero:
        for s in human.hero.skills:
            tag = ""
            if s.is_compulsory:
                tag = "[dim]锁定技[/dim] "
            elif s.is_lord_skill:
                tag = "[dim]主公技[/dim] "
            skills_lines += f"  [bold yellow]【{s.name}】[/bold yellow]{tag}\n"
            skills_lines += f"    [dim]{s.description}[/dim]\n"

    identity_color = human.identity.color
    identity_name = human.identity.chinese_name

    from game.win_checker import get_identity_win_condition

    win_cond = get_identity_win_condition(human.identity.value)
    return (
        f"[bold]{human.name}[/bold] {human.hero.name if human.hero else ''}\n"
        f"体力: {hp_bar} {human.hp}/{human.max_hp}\n"
        f"身份: [{identity_color}]{identity_name}[/{identity_color}]\n"
        f"目标: {win_cond}\n"
        f"─── 技能 ───\n"
        f"{skills_lines.rstrip()}"
    )


def refresh_phase_bar(screen: Any, engine: Any) -> None:
    """刷新阶段栏与牌堆信息."""
    from ui.textual_ui.widgets.phase_indicator import PhaseIndicator

    phase_bar = screen.query_one("#phase-bar", PhaseIndicator)
    phase_bar.set_phase(engine.phase.value)
    current_name = engine.current_player.name if engine.current_player else ""
    phase_bar.set_info(
        round_count=engine.round_count,
        deck_count=engine.deck.remaining,
        discard_count=engine.deck.discarded,
        player_name=current_name,
    )


def refresh_opponents(screen: Any, engine: Any, human: Any) -> None:
    """刷新对手区（含已死亡玩家）."""
    from textual.containers import VerticalScroll

    from ui.textual_ui.widgets.player_panel import PlayerPanel

    opp_container = screen.query_one("#opponents", VerticalScroll)
    all_others = engine.get_all_other_players(human)
    existing = list(opp_container.query(PlayerPanel))
    if len(existing) != len(all_others):
        with screen.app.batch_update():
            opp_container.remove_children()
            for i, p in enumerate(all_others):
                panel = PlayerPanel(p, index=i, id=f"opp-{i}")
                if not p.is_alive:
                    panel.add_class("dead")
                if p == engine.current_player:
                    panel.add_class("active-turn")
                opp_container.mount(panel)
    else:
        for panel, p in zip(existing, all_others, strict=False):
            dist = engine.calculate_distance(human, p) if p.is_alive else -1
            in_rng = engine.is_in_attack_range(human, p) if p.is_alive else False
            panel.update_player(p, distance=dist, in_range=in_rng)
            if p == engine.current_player:
                panel.add_class("active-turn")
            else:
                panel.remove_class("active-turn")


def refresh_hand_cards(screen: Any, engine: Any, human: Any) -> None:
    """刷新手牌区及可用提示."""
    from textual.containers import Horizontal

    from ui.textual_ui.widgets.card_widget import CardWidget

    hand_container = screen.query_one("#hand-cards", Horizontal)
    is_player_turn = engine.current_player == human
    can_sha = human.can_use_sha() if hasattr(human, "can_use_sha") else True
    has_targets = bool(engine.get_targets_in_range(human)) if is_player_turn else False

    with screen.app.batch_update():
        hand_container.remove_children()
        for i, card in enumerate(human.hand):
            widget = CardWidget(card, index=i)
            if is_player_turn and screen._is_card_playable(card, human, can_sha, has_targets):
                widget.add_class("playable")
            hand_container.mount(widget)


def refresh_equipment(screen: Any, human: Any) -> None:
    """刷新装备槽."""
    from ui.textual_ui.widgets.equipment_slots import EquipmentSlots

    equip_widget = screen.query_one("#equip-section", EquipmentSlots)
    equip_widget.update_player(human)


def refresh_info_panel(screen: Any, human: Any) -> None:
    """刷新信息面板文本."""
    from textual.widgets import Static

    info_text = build_player_info_text(human)
    screen.query_one("#info-panel", Static).update(info_text)
