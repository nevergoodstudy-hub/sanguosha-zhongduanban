# -*- coding: utf-8 -*-
"""游戏规则界面"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static, Button
from textual.containers import Container, VerticalScroll


class RulesScreen(Screen):
    """游戏规则界面"""

    BINDINGS = [Binding("escape", "go_back", "返回")]

    CSS = """
    RulesScreen {
        align: center middle;
    }
    #rules-box {
        width: 70;
        height: 30;
        border: round cyan;
        padding: 1 2;
    }
    #rules-scroll {
        height: 1fr;
        overflow-y: auto;
    }
    #btn-back {
        width: 100%;
        margin-top: 1;
    }
    """

    RULES_TEXT = """\
[bold]游戏目标[/bold]
  主公：杀死所有反贼和内奸
  忠臣：保护主公获胜
  反贼：杀死主公
  内奸：最后存活

[bold]回合流程[/bold]
  1. 准备阶段
  2. 判定阶段（延时锦囊）
  3. 摸牌阶段（摸2张）
  4. 出牌阶段（使用卡牌/技能）
  5. 弃牌阶段（保留手牌≤体力值）
  6. 结束阶段

[bold]操作提示[/bold]
  点击手牌选择出牌
  点击技能按钮使用技能
  [E] 结束出牌阶段

按 Esc 或点击下方按钮返回主菜单
"""

    def compose(self) -> ComposeResult:
        yield Container(
            VerticalScroll(
                Static(self.RULES_TEXT, markup=True),
                id="rules-scroll",
            ),
            Button("↩ 返回主菜单", id="btn-back", variant="primary"),
            id="rules-box",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()

    def action_go_back(self) -> None:
        """Esc 键返回"""
        self.app.pop_screen()
