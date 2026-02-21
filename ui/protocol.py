"""GameUI 协议 — 接口隔离拆分 (Phase 3.1)

遵循接口隔离原则 (ISP)，将原有的单一 GameUI Protocol
拆分为三个职责明确的子协议：
  - GameDisplay : 纯展示输出（fire-and-forget）
  - GameInput   : 交互输入（阻塞获取玩家响应）
  - GameNotify  : 生命周期与事件通知（引擎绑定、动画触发等）

GameUI 作为向后兼容的组合协议保留，继承全部三个子协议。
现有代码中 ``GameUI`` 类型标注无需修改；需要更窄接口的场景
可使用对应子协议做类型约束。

TextualUIBridge 等实现类基于结构子类型化 (structural subtyping)
自动满足协议要求，无需显式继承。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from game.card import Card, CardSuit
    from game.engine import GameEngine
    from game.hero import Hero
    from game.player import Player


# ====================================================================== #
#  子协议 1: GameDisplay — 纯展示                                         #
# ====================================================================== #


class GameDisplay(Protocol):
    """纯展示协议 — 只负责向用户输出信息，无需返回有意义的值。"""

    def show_title(self) -> None: ...
    def show_rules(self) -> None: ...
    def show_game_state(self, engine: GameEngine, current_player: Player) -> None: ...
    def show_log(self, message: str) -> None: ...
    def show_game_over(self, winner_message: str, is_victory: bool) -> None: ...
    def clear_screen(self) -> None: ...
    def show_help(self) -> None: ...


# ====================================================================== #
#  子协议 2: GameInput — 交互输入                                          #
# ====================================================================== #


class GameInput(Protocol):
    """交互输入协议 — 阻塞等待并返回玩家选择/响应。"""

    # ---- 菜单输入 ----
    def show_main_menu(self) -> int: ...
    def show_player_count_menu(self) -> int: ...
    def show_difficulty_menu(self) -> str: ...
    def show_hero_selection(
        self, heroes: list[Hero], selected_count: int = 1, is_lord: bool = False
    ) -> list[Hero]: ...

    # ---- 出牌阶段输入 ----
    def get_player_action(self) -> str: ...
    def choose_target(
        self, player: Player, targets: list[Player], prompt: str = "选择目标"
    ) -> Player | None: ...
    def choose_card_to_play(self, player: Player) -> Card | None: ...
    def choose_cards_to_discard(self, player: Player, count: int) -> list[Card]: ...
    def show_skill_menu(self, player: Player, usable_skills: list[str]) -> str | None: ...

    # ---- 响应请求输入 ----
    def ask_for_shan(self, player: Player) -> Card | None: ...
    def ask_for_sha(self, player: Player) -> Card | None: ...
    def ask_for_tao(self, savior: Player, dying: Player) -> Card | None: ...
    def ask_for_wuxie(
        self,
        responder: Player,
        trick_card: Card,
        source: Player,
        target: Player | None,
        currently_cancelled: bool,
    ) -> Card | None: ...
    def choose_card_from_player(self, chooser: Player, target: Player) -> Card | None: ...
    def choose_suit(self, player: Player) -> CardSuit: ...
    def guanxing_selection(
        self, player: Player, cards: list[Card]
    ) -> tuple[list[Card], list[Card]]: ...

    # ---- 其他交互 ----
    def wait_for_continue(self, message: str = "Press Enter to continue...") -> None: ...
    def ask_for_jijiang(self, player: Player) -> Card | None: ...
    def ask_for_hujia(self, player: Player) -> Card | None: ...


# ====================================================================== #
#  子协议 3: GameNotify — 生命周期与事件通知                                #
# ====================================================================== #


class GameNotify(Protocol):
    """生命周期与事件通知协议 — 引擎绑定、动画/音效触发等异步通知。"""

    def set_engine(self, engine: GameEngine) -> None: ...


# ====================================================================== #
#  组合协议: GameUI — 向后兼容                                             #
# ====================================================================== #


class GameUI(GameDisplay, GameInput, GameNotify, Protocol):
    """完整 UI 协议 — 组合 Display + Input + Notify，向后兼容。

    现有代码使用 ``GameUI`` 类型标注的地方无需修改。
    需要更窄接口约束时，可直接使用 ``GameDisplay`` / ``GameInput`` /
    ``GameNotify`` 子协议。
    """

    ...
