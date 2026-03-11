"""多目标选择弹窗.

用于铁索连环等需要选择多个目标(0-N)的场景。
点击目标按钮切换选中状态，点击确认提交所有选中目标。

dismiss(list[int])  → 选中目标索引列表（可为空=重铸）
dismiss(None)       → 取消选择
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Button, Static

from game.player import Identity
from ui.textual_ui.modals.base import AnimatedModalScreen

if TYPE_CHECKING:
    pass


class MultiTargetModal(AnimatedModalScreen[list[int] | None]):
    """多目标选择弹窗 — 点击切换选中，确认提交."""

    DEFAULT_CSS = """
    MultiTargetModal {
        align: center middle;
        background: $background 70%;
    }
    MultiTargetModal > #mt-container {
        width: 60;
        max-width: 85%;
        height: auto;
        max-height: 80%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
        overflow-y: auto;
    }
    MultiTargetModal #mt-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    MultiTargetModal #mt-hint {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }
    MultiTargetModal .mt-btn {
        width: 100%;
        margin: 0 0 1 0;
    }
    MultiTargetModal .mt-btn.selected {
        background: $success;
    }
    MultiTargetModal #btn-mt-confirm {
        width: 100%;
        margin-top: 1;
    }
    MultiTargetModal #btn-mt-cancel {
        width: 100%;
        margin-top: 0;
    }
    """

    def __init__(
        self, targets: list, prompt: str = "选择目标", min_count: int = 0, max_count: int = 2
    ):
        """Args:
        targets: Player 对象列表
        prompt: 提示文字
        min_count: 最少选择数量
        max_count: 最多选择数量.
        """
        super().__init__()
        self._targets = targets
        self._prompt = prompt
        self._min_count = min_count
        self._max_count = max_count
        self._selected: set[int] = set()

    def compose(self) -> ComposeResult:
        with Container(id="mt-container"):
            yield Static(f"🎯 {self._prompt}", id="mt-title")
            yield Static(
                f"可选 {self._min_count}-{self._max_count} 个目标（已选 0 个，点击切换选中）",
                id="mt-hint",
            )
            for i, t in enumerate(self._targets):
                hero_name = t.hero.name if t.hero else "?"
                hp_bar = "●" * t.hp + "○" * (t.max_hp - t.hp)
                identity_str = ""
                if hasattr(t, "identity") and t.identity == Identity.LORD:
                    identity_str = " [主公]"
                equip_parts = []
                if hasattr(t, "equipment"):
                    if t.equipment.weapon:
                        equip_parts.append(f"⚔{t.equipment.weapon.name}")
                    if t.equipment.armor:
                        equip_parts.append(f"🛡{t.equipment.armor.name}")
                equip_str = " ".join(equip_parts)
                chain_str = " 🔗" if t.is_chained else ""
                label = (
                    f"{t.name} ({hero_name}){identity_str}  "
                    f"{hp_bar} {t.hp}/{t.max_hp}  "
                    f"手牌:{t.hand_count}  {equip_str}{chain_str}"
                )
                yield Button(label, id=f"mt-{i}", classes="mt-btn", variant="primary")
            yield Button("✅ 确认", id="btn-mt-confirm", variant="success")
            yield Button("❌ 取消", id="btn-mt-cancel", variant="error")

    def _update_hint(self) -> None:
        """更新提示文字."""
        try:
            hint = self.query_one("#mt-hint", Static)
            hint.update(
                f"可选 {self._min_count}-{self._max_count} 个目标"
                f"（已选 {len(self._selected)} 个，点击切换选中）"
            )
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("mt-"):
            idx = int(btn_id.split("-")[1])
            if idx in self._selected:
                self._selected.discard(idx)
                event.button.remove_class("selected")
                event.button.variant = "primary"
            elif len(self._selected) < self._max_count:
                self._selected.add(idx)
                event.button.add_class("selected")
                event.button.variant = "success"
            self._update_hint()
        elif btn_id == "btn-mt-confirm":
            if len(self._selected) < self._min_count:
                return  # 不满足最低要求
            self.dismiss(sorted(self._selected))
        elif btn_id == "btn-mt-cancel":
            self.dismiss(None)
