"""TextualUIBridge — 引擎 ↔ Textual 桥接层

实现 GameUI Protocol，将引擎调用转发到 Textual 界面。
所有需要人类玩家交互的方法通过 ModalScreen + threading.Event 实现
线程安全的阻塞等待。

线程模型:
  worker 线程 (game loop) → call_from_thread(push_screen(Modal)) → UI 线程
  UI 线程 → user clicks → dismiss(result) → callback sets Event
  worker 线程 ← Event.wait() ← 获取结果
"""

from __future__ import annotations

import random
import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass


class TextualUIBridge:
    """引擎 ↔ Textual 桥接层

    实现 show_log 等方法，将引擎调用转发到 Textual 界面。
    用作 engine.set_ui(bridge) 的对象。
    """

    def __init__(self, screen):
        """Args:
        screen: GamePlayScreen 实例
        """
        self._screen = screen
        self.log_messages: list[str] = []
        self.engine = None

    # ------------------------------------------------------------------ #
    #  内部工具：线程安全 modal 调度                                      #
    # ------------------------------------------------------------------ #

    def _push_modal_and_wait(self, modal_factory, *, timeout: float = 300):
        """通用 modal 调度：在 UI 线程 push ModalScreen 并阻塞 worker 线程等待结果。

        Args:
            modal_factory: callable，无参，返回 ModalScreen 实例
            timeout: 等待秒数

        Returns:
            dismiss 传回的结果（任意类型），超时返回 None
        """
        result_holder = [None]
        event = threading.Event()

        def _on_dismiss(result):
            result_holder[0] = result
            event.set()

        def _push():
            modal = modal_factory()
            self._screen.app.push_screen(modal, callback=_on_dismiss)

        self._screen.app.call_from_thread(_push)
        event.wait(timeout=timeout)
        return result_holder[0]

    # ================================================================== #
    #  GameUI Protocol — 菜单（由 Textual Screens 处理，此处为 fallback）  #
    # ================================================================== #

    def set_engine(self, engine):
        self.engine = engine

    def show_title(self):
        pass

    def show_main_menu(self):
        return 1

    def show_player_count_menu(self):
        return 4

    def show_difficulty_menu(self):
        return "normal"

    def show_hero_selection(self, heroes, selected_count=1, is_lord=False):
        return [heroes[0]] if heroes else []

    def show_rules(self):
        pass

    # ================================================================== #
    #  GameUI Protocol — 游戏状态                                         #
    # ================================================================== #

    def show_log(self, message: str) -> None:
        self.log_messages.append(message)
        try:
            self._screen._post_log(message)
        except Exception:
            pass

    def show_game_state(self, engine, current_player) -> None:
        try:
            self._screen._post_refresh()
        except Exception:
            pass

    def show_game_over(self, winner_message, is_victory):
        pass

    def clear_screen(self):
        pass

    # ================================================================== #
    #  GameUI Protocol — 响应请求（ModalScreen 弹窗）                      #
    # ================================================================== #

    def ask_for_shan(self, player) -> Optional:
        """人类玩家被要求出闪 → ShanResponseModal"""
        shan_cards = player.get_cards_by_name("闪")
        if not shan_cards:
            return None
        from ui.textual_ui.modals.response_modal import ShanResponseModal

        result = self._push_modal_and_wait(lambda: ShanResponseModal(cards=shan_cards), timeout=20)
        if result:
            return shan_cards[0]
        return None

    def ask_for_sha(self, player) -> Optional:
        """人类玩家被要求出杀 → ShaResponseModal"""
        sha_cards = player.get_cards_by_name("杀")
        if not sha_cards:
            return None
        from ui.textual_ui.modals.response_modal import ShaResponseModal

        result = self._push_modal_and_wait(lambda: ShaResponseModal(cards=sha_cards), timeout=20)
        if result:
            return sha_cards[0]
        return None

    def ask_for_tao(self, savior, dying) -> Optional:
        """人类玩家被要求出桃 → TaoResponseModal"""
        tao_cards = savior.get_cards_by_name("桃")
        if not tao_cards:
            return None
        from ui.textual_ui.modals.response_modal import TaoResponseModal

        result = self._push_modal_and_wait(
            lambda: TaoResponseModal(dying_name=dying.name, cards=tao_cards),
            timeout=25,
        )
        if result:
            return tao_cards[0]
        return None

    def ask_for_wuxie(self, responder, trick_card, source, target, currently_cancelled):
        """人类玩家被问是否使用无懈可击 → WuxieResponseModal"""
        wuxie_cards = responder.get_cards_by_name("无懈可击")
        if not wuxie_cards:
            return None
        from ui.textual_ui.modals.wuxie_modal import WuxieResponseModal

        trick_name = str(trick_card.name) if trick_card else "锦囊"
        source_name = source.name if source else "?"
        target_name = target.name if target else "全体"
        result = self._push_modal_and_wait(
            lambda: WuxieResponseModal(
                trick_name=trick_name,
                source_name=source_name,
                target_name=target_name,
                currently_cancelled=currently_cancelled,
                countdown=5,
            ),
            timeout=10,
        )
        if result:
            return wuxie_cards[0]
        return None

    def choose_card_from_player(self, chooser, target):
        """从目标玩家选一张牌 → CardPickModal"""
        all_cards = target.get_all_cards()
        if not all_cards:
            return None
        from ui.textual_ui.modals.card_pick_modal import CardPickModal

        result = self._push_modal_and_wait(
            lambda: CardPickModal(target=target, all_cards=all_cards),
            timeout=30,
        )
        if result is not None and 0 <= result < len(all_cards):
            return all_cards[result]
        # fallback: 若用户取消或超时，随机选（保持游戏不卡住）
        return random.choice(all_cards)

    def choose_suit(self, player):
        """选择花色 → SuitSelectModal"""
        from game.card import CardSuit
        from ui.textual_ui.modals.suit_modal import SuitSelectModal

        result = self._push_modal_and_wait(lambda: SuitSelectModal(), timeout=30)
        if result:
            # result 是 "spade"/"heart"/"club"/"diamond" 字符串
            suit_map = {s.value: s for s in CardSuit}
            return suit_map.get(result, list(CardSuit)[0])
        return list(CardSuit)[0]  # fallback

    # ================================================================== #
    #  GameUI Protocol — 玩家操作                                         #
    # ================================================================== #

    def choose_target(self, player, targets, prompt="选择目标"):
        """选择目标 → TargetSelectModal"""
        from ui.textual_ui.modals.target_modal import TargetSelectModal

        result = self._push_modal_and_wait(
            lambda: TargetSelectModal(targets=targets, prompt=prompt),
            timeout=60,
        )
        if result is not None and 0 <= result < len(targets):
            return targets[result]
        return None

    def choose_card_to_play(self, player):
        return None

    def choose_cards_to_discard(self, player, count):
        return player.hand[:count]

    def show_skill_menu(self, player, usable_skills):
        return None

    def get_player_action(self):
        return "E"

    # ================================================================== #
    #  GameUI Protocol — 其他                                             #
    # ================================================================== #

    def show_help(self):
        pass

    def wait_for_continue(self, message=""):
        pass

    def guanxing_selection(self, player, cards):
        return [], cards[:]

    def ask_for_jijiang(self, player):
        return None

    def ask_for_hujia(self, player):
        return None
