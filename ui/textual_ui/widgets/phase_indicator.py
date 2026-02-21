"""PhaseIndicator — 回合阶段指示器

6 阶段列表：准备 → 判定 → 摸牌 → 出牌 → 弃牌 → 结束
当前阶段高亮显示。
"""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static

PHASES = [
    ("prepare", "准备"),
    ("judge", "判定"),
    ("draw", "摸牌"),
    ("play", "出牌"),
    ("discard", "弃牌"),
    ("end", "结束"),
]


class PhaseIndicator(Static):
    """回合阶段指示器"""

    DEFAULT_CSS = """
    PhaseIndicator {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    """

    current_phase = reactive("prepare")
    round_count = reactive(0)
    deck_count = reactive(0)
    discard_count = reactive(0)
    current_player_name = reactive("")

    def render(self) -> str:
        parts = []
        for phase_id, label in PHASES:
            if phase_id == self.current_phase:
                parts.append(f"[bold $accent]▶ {label}[/bold $accent]")
            else:
                parts.append(f"[dim]  {label}[/dim]")
        phase_bar = " → ".join(parts)

        # 右侧额外信息
        info_parts = []
        if self.round_count > 0:
            info_parts.append(f"R{self.round_count}")
        if self.deck_count >= 0:
            info_parts.append(f"🃏{self.deck_count}")
        if self.discard_count > 0:
            info_parts.append(f"🗑{self.discard_count}")
        if self.current_player_name:
            info_parts.append(f"[bold]{self.current_player_name}[/bold]")
        info_str = "  ".join(info_parts)

        if info_str:
            return f"{phase_bar}  [dim]|[/dim]  {info_str}"
        return phase_bar

    def set_phase(self, phase: str) -> None:
        self.current_phase = phase

    def set_info(
        self,
        round_count: int = 0,
        deck_count: int = 0,
        discard_count: int = 0,
        player_name: str = "",
    ) -> None:
        """更新额外信息"""
        self.round_count = round_count
        self.deck_count = deck_count
        self.discard_count = discard_count
        self.current_player_name = player_name
