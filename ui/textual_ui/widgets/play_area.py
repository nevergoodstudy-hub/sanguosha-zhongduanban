"""PlayArea — 中央出牌展示区 (三国杀OL风格)

显示最近打出的卡牌，附带淡出效果。
"""

from __future__ import annotations

from textual.reactive import reactive
from textual.widgets import Static


class PlayArea(Static):
    """中央出牌展示区"""

    DEFAULT_CSS = """
    PlayArea {
        width: 100%;
        height: auto;
        min-height: 3;
        max-height: 5;
        content-align: center middle;
        text-align: center;
        border: round $secondary;
        padding: 0 1;
    }
    """

    last_play_text = reactive("", layout=True)
    _fade_timer = None

    def render(self) -> str:
        if not self.last_play_text:
            return "[dim]━━━ 出牌区 ━━━[/dim]"
        return self.last_play_text

    def show_card_play(
        self, player_name: str, card_name: str, target_name: str = "", extra: str = ""
    ) -> None:
        """显示一次出牌"""
        parts = [f"[bold]{player_name}[/bold]"]
        parts.append(f"使用 [bold yellow]【{card_name}】[/bold yellow]")
        if target_name:
            parts.append(f"→ [bold cyan]{target_name}[/bold cyan]")
        if extra:
            parts.append(extra)
        self.last_play_text = " ".join(parts)

        # 5秒后淡出
        if self._fade_timer is not None:
            self._fade_timer.stop()
        self._fade_timer = self.set_timer(5.0, self._fade_out)

    def show_skill_use(self, player_name: str, skill_name: str, extra: str = "") -> None:
        """显示技能发动"""
        text = f"[bold]{player_name}[/bold] ✨ 发动 [bold yellow]【{skill_name}】[/bold yellow]"
        if extra:
            text += f" {extra}"
        self.last_play_text = text

        if self._fade_timer is not None:
            self._fade_timer.stop()
        self._fade_timer = self.set_timer(4.0, self._fade_out)

    def show_damage(self, target_name: str, amount: int, damage_type: str = "") -> None:
        """显示伤害"""
        type_icon = {"fire": "🔥", "thunder": "⚡"}.get(damage_type, "💔")
        self.last_play_text = (
            f"{type_icon} [bold red]{target_name}[/bold red] "
            f"受到 [bold red]{amount}[/bold red] 点伤害"
        )

        if self._fade_timer is not None:
            self._fade_timer.stop()
        self._fade_timer = self.set_timer(3.0, self._fade_out)

    def _fade_out(self) -> None:
        """淡出效果"""
        self.last_play_text = ""
        self._fade_timer = None
