"""PlayerPanel — 可点击玩家面板 (M-B).

国籍色条 + 武将名 + HP条 + 手牌数 + 装备图标 + 身份标记。
.targetable / .dead / .dying CSS 状态。
on_click 发布 PlayerClicked Message。
hover tooltip 显示技能描述。
"""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from textual.message import Message
from textual.reactive import reactive
from textual.timer import Timer
from textual.widgets import Static

if TYPE_CHECKING:
    pass


# 国籍颜色
KINGDOM_COLORS = {
    "wei": "#3498db",  # 魏 蓝
    "shu": "#e74c3c",  # 蜀 红
    "wu": "#27ae60",  # 吴 绿
    "qun": "#f39c12",  # 群 黄
}


class PlayerPanel(Static, can_focus=True):
    """可点击的玩家面板."""

    DEFAULT_CSS = """
    PlayerPanel {
        width: 100%;
        height: auto;
        min-height: 3;
        padding: 0 1;
        border: round $primary;
        margin-bottom: 1;
        transition: background 200ms, border 200ms;
    }
    PlayerPanel:hover {
        border: heavy $accent;
        background: $primary-darken-1;
    }
    PlayerPanel.targetable {
        border: heavy $warning;
        background: $warning-darken-3;
    }
    PlayerPanel.dead {
        opacity: 40%;
        text-style: strike;
    }
    PlayerPanel.dying {
        background: $error-darken-2;
        border: heavy $error;
    }
    PlayerPanel.active-turn {
        border: double $accent;
        background: $accent-darken-3;
    }
    """

    player_index = reactive(-1)

    class PlayerClicked(Message):
        """玩家面板被点击."""

        def __init__(self, index: int, player=None) -> None:
            super().__init__()
            self.index = index
            self.player = player

    def __init__(self, player, index: int = -1, **kwargs):
        super().__init__(**kwargs)
        self._player = player
        self.player_index = index
        self._distance: int = -1  # 与人类玩家的距离
        self._in_range: bool = False  # 是否在攻击范围内
        self._prev_hp: int = player.hp if hasattr(player, "hp") else 0  # P2-1
        self._pulse_timer: Timer | None = None  # P1-3: 呼吸脉冲
        self._pulse_dim: bool = False
        self._update_tooltip()

    def _update_tooltip(self) -> None:
        """设置 tooltip 显示技能描述."""
        p = self._player
        if p.hero and hasattr(p.hero, "skills"):
            lines = [f"【{p.hero.name}】 {p.hero.kingdom.chinese_name}"]
            for s in p.hero.skills:
                desc = getattr(s, "description", s.name)
                lines.append(f"  ▸ 【{s.name}】{desc}")
            self.tooltip = "\n".join(lines)

    def render(self) -> str:
        """渲染三国杀OL风格玩家面板."""
        p = self._player
        hero_name = p.hero.name if p.hero else "?"
        kingdom = p.hero.kingdom.value if p.hero else ""
        kingdom_color = KINGDOM_COLORS.get(kingdom, "white")

        # 身份显示规则
        identity_str = ""
        if hasattr(p, "identity"):
            from game.player import Identity

            if p.identity == Identity.LORD:
                identity_str = "[bold red]👑[/bold red]"
            elif not p.is_alive:
                identity_str = f"[dim]({p.identity.chinese_name})[/dim]"
            else:
                identity_str = "[dim]❓[/dim]"

        # HP 条（视觉进度条风格）
        if p.is_alive:
            if p.hp <= 1:
                hp_color = "red"
            elif p.hp <= p.max_hp // 2:
                hp_color = "yellow"
            else:
                hp_color = "green"
            hp_filled = f"[{hp_color}]█[/{hp_color}]" * p.hp
            hp_empty = "[dim]░[/dim]" * (p.max_hp - p.hp)
            hp_bar = f"{hp_filled}{hp_empty} {p.hp}/{p.max_hp}"
        else:
            hp_bar = "[dim]💀 已阵亡[/dim]"

        # 装备图标（紧凑单行）
        equip_icons = []
        if hasattr(p, "equipment"):
            if p.equipment.weapon:
                equip_icons.append(f"[bold]⚔[/bold]{p.equipment.weapon.name}")
            if p.equipment.armor:
                equip_icons.append(f"[bold]🛡[/bold]{p.equipment.armor.name}")
            if p.equipment.horse_minus:
                equip_icons.append("[red]-🐎[/red]")
            if p.equipment.horse_plus:
                equip_icons.append("[green]+🐎[/green]")
        equip_str = " ".join(equip_icons)

        # 状态标记
        status_parts = []
        if getattr(p, "is_chained", False):
            status_parts.append("[yellow]🔗[/yellow]")
        if getattr(p, "flipped", False):
            status_parts.append("[dim]🔄[/dim]")
        # 判定区
        if hasattr(p, "judge_area") and p.judge_area:
            for jc in p.judge_area:
                status_parts.append(f"[red]⚠{jc.name}[/red]")
        status_str = " ".join(status_parts)

        # 距离/攻击范围标记
        dist_str = ""
        if self._distance >= 0 and p.is_alive:
            range_icon = "[⚔]" if self._in_range else "[✖]"
            range_color = "green" if self._in_range else "red"
            dist_str = f"[{range_color}]距{self._distance}{range_icon}[/{range_color}]"

        # 组装两行显示
        line1 = (
            f"[{kingdom_color}]█▌[/{kingdom_color}] "
            f"{identity_str} [bold]{p.name}[/bold] {hero_name}  "
            f"{hp_bar}  "
            f"🃏[bold]{p.hand_count}[/bold]"
        )
        if dist_str:
            line1 += f"  {dist_str}"

        line2_parts = []
        if equip_str:
            line2_parts.append(equip_str)
        if status_str:
            line2_parts.append(status_str)
        if line2_parts:
            line1 += "\n    " + "  ".join(line2_parts)

        return line1

    def on_click(self) -> None:
        self.post_message(self.PlayerClicked(self.player_index, self._player))

    def update_player(self, player, distance: int = -1, in_range: bool = False) -> None:
        """更新玩家数据并刷新，带 HP 变化动画 (P2-1)."""
        old_hp = self._prev_hp
        new_hp = player.hp if hasattr(player, "hp") else 0
        self._player = player
        self._distance = distance
        self._in_range = in_range
        self._update_tooltip()
        # 更新 CSS 状态类
        self.remove_class("dead", "dying", "active-turn")
        if not player.is_alive:
            self.add_class("dead")
        elif player.hp <= 0:
            self.add_class("dying")
        # P2-1: HP 变化动画反馈
        if new_hp != old_hp and player.is_alive:
            css_cls = "pulse-damage" if new_hp < old_hp else "pulse-heal"
            self.add_class(css_cls)
            self.styles.animate(
                "opacity",
                value=0.4,
                duration=0.2,
                easing="out_cubic",
                on_complete=lambda: self._hp_flash_restore(css_cls),
            )
        self._prev_hp = new_hp
        self.refresh()

    def _hp_flash_restore(self, css_cls: str) -> None:
        """恢复 HP 闪烁 (P2-1)."""
        try:
            self.styles.animate(
                "opacity",
                value=1.0,
                duration=0.3,
                easing="in_out_cubic",
                on_complete=lambda: self.remove_class(css_cls),
            )
        except Exception:
            self.remove_class(css_cls)

    # P2-4: 死亡震动效果
    def death_shake(self) -> None:
        """死亡时快速抖动面板 (timer-based offset toggle).

        连续 4 次 ±1 水平偏移，每次 0.06s，最后恢复 offset=(0,0)。
        注意: Textual set_timer(0.0) 会导致 ZeroDivisionError，
        所以延迟最小值为 0.01s。
        """
        offsets = [(-1, 0), (1, 0), (-1, 0), (1, 0), (0, 0)]
        for i, (x, y) in enumerate(offsets):
            delay = max(0.01, 0.06 * i)
            self.set_timer(
                delay,
                lambda _x=x, _y=y: self._apply_shake_offset(_x, _y),
            )
        # 震动结束后执行 opacity 渐隐到 dead 状态
        self.set_timer(
            0.06 * (len(offsets) + 1),
            self._finish_death_shake,
        )

    def _apply_shake_offset(self, x: int, y: int) -> None:
        """设置 offset 用于震动."""
        with contextlib.suppress(Exception):
            self.styles.offset = (x, y)

    def _finish_death_shake(self) -> None:
        """震动结束: opacity 渐隐并标记 dead."""
        try:
            self.styles.offset = (0, 0)
            self.add_class("dead")
            self.styles.animate(
                "opacity",
                value=0.4,
                duration=0.4,
                easing="out_cubic",
            )
        except Exception:
            self.add_class("dead")

    # P1-3: 目标选择呼吸脉冲
    def start_pulse(self) -> None:
        """启动 targetable 呼吸脉冲动画."""
        if self._pulse_timer is not None:
            return
        self._pulse_dim = False
        self._pulse_timer = self.set_interval(0.8, self._pulse_tick)

    def stop_pulse(self) -> None:
        """停止呼吸脉冲并恢复."""
        if self._pulse_timer is not None:
            self._pulse_timer.stop()
            self._pulse_timer = None
        self.styles.animate("opacity", value=1.0, duration=0.2)

    def _pulse_tick(self) -> None:
        """呼吸脉冲 tick: opacity 在 0.6 和 1.0 之间交替."""
        target = 0.6 if not self._pulse_dim else 1.0
        self._pulse_dim = not self._pulse_dim
        with contextlib.suppress(Exception):
            self.styles.animate("opacity", value=target, duration=0.6, easing="in_out_cubic")
