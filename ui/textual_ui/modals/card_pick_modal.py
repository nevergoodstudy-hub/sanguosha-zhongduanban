"""卡牌选取弹窗 (M-C C6).

用于过河拆桥 / 顺手牵羊等需要从目标玩家选一张牌的场景。
修复 P0: 原 choose_card_from_player 使用 random.choice。

显示目标玩家的:
  - 手牌（背面，只显示数量，随机选取）
  - 装备区（显示具体装备名，可直接选）
  - 判定区（如有延时锦囊）

dismiss(card_index: int) → 选中的卡牌在 all_cards 中的索引
dismiss(None)            → 取消
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Button, Static

from ui.textual_ui.modals.base import AnimatedModalScreen

if TYPE_CHECKING:
    pass


class CardPickModal(AnimatedModalScreen[int | None]):
    """从目标玩家选一张牌."""

    DEFAULT_CSS = """
    CardPickModal {
        align: center middle;
        background: $background 70%;
    }
    CardPickModal > #cardpick-container {
        width: 60;
        max-width: 85%;
        height: auto;
        max-height: 80%;
        border: thick $warning;
        background: $surface;
        padding: 1 2;
        overflow-y: auto;
    }
    CardPickModal #cardpick-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    CardPickModal .pick-section {
        margin-bottom: 1;
    }
    CardPickModal .pick-btn {
        width: 100%;
        margin: 0 0 1 0;
    }
    CardPickModal #btn-cancel-pick {
        width: 100%;
        margin-top: 1;
    }
    """

    def __init__(self, target, all_cards: list):
        """Args:
        target: Player — 被选牌的目标
        all_cards: 该玩家所有牌列表（与 get_all_cards 返回一致）.
        """
        super().__init__()
        self._target = target
        self._all_cards = all_cards

    def compose(self) -> ComposeResult:
        target = self._target
        hero_name = target.hero.name if target.hero else "?"

        with Container(id="cardpick-container"):
            yield Static(
                f"🃏 从 {target.name}({hero_name}) 选择一张牌",
                id="cardpick-title",
            )

            # 手牌区（背面，只显示 N 张可选）
            hand_count = target.hand_count if hasattr(target, "hand_count") else len(target.hand)
            if hand_count > 0:
                yield Static(
                    "[bold]📋 手牌区[/bold]（随机抽取）", classes="pick-section", markup=True
                )
                yield Button(
                    f"🎴 手牌 ({hand_count} 张，随机抽取)",
                    id="pick-hand",
                    classes="pick-btn",
                    variant="primary",
                )

            # 装备区
            equip_cards = []
            if hasattr(target, "equipment"):
                eq = target.equipment
                for slot_name, card in [
                    ("武器", eq.weapon),
                    ("防具", eq.armor),
                    ("进攻马", eq.horse_minus),
                    ("防御马", eq.horse_plus),
                ]:
                    if card:
                        equip_cards.append((slot_name, card))

            if equip_cards:
                yield Static("[bold]⚙ 装备区[/bold]", classes="pick-section", markup=True)
                for slot_name, card in equip_cards:
                    # 找到这张牌在 all_cards 中的索引
                    try:
                        idx = self._all_cards.index(card)
                    except ValueError:
                        continue
                    suit_icon = {"spade": "♠", "heart": "♥", "club": "♣", "diamond": "♦"}.get(
                        getattr(card.suit, "value", ""), "?"
                    )
                    yield Button(
                        f"{slot_name}: {suit_icon}{card.number_str} {card.name}",
                        id=f"pick-{idx}",
                        classes="pick-btn",
                        variant="warning",
                    )

            yield Button("❌ 取消", id="btn-cancel-pick", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "pick-hand":
            # 随机选一张手牌
            import random

            target = self._target
            if target.hand:
                card = random.choice(target.hand)
                try:
                    idx = self._all_cards.index(card)
                    self.dismiss(idx)
                except ValueError:
                    self.dismiss(0)
            else:
                self.dismiss(None)
        elif btn_id.startswith("pick-"):
            idx = int(btn_id.split("-")[1])
            self.dismiss(idx)
        elif btn_id == "btn-cancel-pick":
            self.dismiss(None)
