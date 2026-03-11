"""TextualUIBridge — 引擎 ↔ Textual 桥接层.

实现 GameUI Protocol，将引擎调用转发到 Textual 界面。
所有需要人类玩家交互的方法统一复用 `GamePlayScreen` 的共享 modal helper，
避免 bridge 与 screen 维护两套阻塞等待逻辑。
"""

from __future__ import annotations

import logging
import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


class TextualUIBridge:
    """引擎 ↔ Textual 桥接层."""

    def __init__(self, screen):
        """Args:
        screen: GamePlayScreen 实例.
        """
        self._screen = screen
        self.log_messages: list[str] = []
        self.engine = None

    @staticmethod
    def _skill_prompt(skill_name: str) -> str:
        prompts = {
            "guicai": "✨ 鬼才：请选择要替换判定的手牌",
            "longdan_as_shan": "✨ 龙胆：请选择 1 张【杀】当【闪】打出",
            "longdan_as_sha": "✨ 龙胆：请选择 1 张【闪】当【杀】打出",
            "wusheng_as_sha": "✨ 武圣：请选择 1 张红色牌当【杀】打出",
        }
        return prompts.get(skill_name, f"✨ {skill_name}：请选择 1 张牌")

    def _call_screen_helper(
        self,
        method_name: str,
        *args,
        default=None,
        log_context: str | None = None,
        level: int = logging.WARNING,
        **kwargs,
    ):
        screen = getattr(self, "_screen", None)
        if screen is None:
            return default

        method = getattr(screen, method_name, None)
        if method is None:
            return default

        try:
            return method(*args, **kwargs)
        except Exception as exc:
            logger.log(
                level,
                "TextualUIBridge failed to %s: %s",
                log_context or method_name,
                exc,
                exc_info=logger.isEnabledFor(logging.DEBUG),
            )
            return default

    def _push_modal_and_wait(
        self,
        modal_factory,
        *,
        timeout: float = 300,
        description: str = "modal interaction",
    ):
        """通过 GamePlayScreen 的共享 helper 同步等待 modal 结果."""
        return self._call_screen_helper(
            "_run_modal_and_wait",
            modal_factory,
            timeout=timeout,
            description=description,
            default=None,
            log_context=f"wait for {description}",
        )

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
        self._call_screen_helper(
            "_post_log",
            message,
            default=None,
            log_context="post battle log",
            level=logging.DEBUG,
        )

    def show_game_state(self, engine, current_player) -> None:
        self._call_screen_helper(
            "_post_refresh",
            default=None,
            log_context="refresh game state",
            level=logging.DEBUG,
        )

    def show_game_over(self, winner_message, is_victory):
        pass

    def clear_screen(self):
        pass

    # ================================================================== #
    #  GameUI Protocol — 响应请求（ModalScreen 弹窗）                      #
    # ================================================================== #

    def ask_for_shan(self, player) -> Optional:
        """人类玩家被要求出闪 → ShanResponseModal."""
        shan_cards = player.get_cards_by_name("闪")
        if not shan_cards:
            return None
        from ui.textual_ui.modals.response_modal import ShanResponseModal

        result = self._push_modal_and_wait(
            lambda: ShanResponseModal(cards=shan_cards),
            timeout=20,
            description="shan response",
        )
        if result:
            return shan_cards[0]
        return None

    def ask_for_sha(self, player) -> Optional:
        """人类玩家被要求出杀 → ShaResponseModal."""
        sha_cards = player.get_cards_by_name("杀")
        if not sha_cards:
            return None
        from ui.textual_ui.modals.response_modal import ShaResponseModal

        result = self._push_modal_and_wait(
            lambda: ShaResponseModal(cards=sha_cards),
            timeout=20,
            description="sha response",
        )
        if result:
            return sha_cards[0]
        return None

    def ask_for_tao(self, savior, dying) -> Optional:
        """人类玩家被要求出桃 → TaoResponseModal."""
        tao_cards = savior.get_cards_by_name("桃")
        if not tao_cards:
            return None
        from ui.textual_ui.modals.response_modal import TaoResponseModal

        result = self._push_modal_and_wait(
            lambda: TaoResponseModal(dying_name=dying.name, cards=tao_cards),
            timeout=25,
            description="tao response",
        )
        if result:
            return tao_cards[0]
        return None

    def ask_for_wuxie(self, responder, trick_card, source, target, currently_cancelled):
        """人类玩家被问是否使用无懈可击 → WuxieResponseModal."""
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
            description="wuxie response",
        )
        if result:
            return wuxie_cards[0]
        return None

    def choose_card_from_player(self, chooser, target):
        """从目标玩家选一张牌 → CardPickModal."""
        all_cards = target.get_all_cards()
        if not all_cards:
            return None
        from ui.textual_ui.modals.card_pick_modal import CardPickModal

        result = self._push_modal_and_wait(
            lambda: CardPickModal(target=target, all_cards=all_cards),
            timeout=30,
            description="card pick",
        )
        if result is not None and 0 <= result < len(all_cards):
            return all_cards[result]
        return random.choice(all_cards)

    def choose_suit(self, player):
        """选择花色 → SuitSelectModal."""
        from game.card import CardSuit
        from ui.textual_ui.modals.suit_modal import SuitSelectModal

        result = self._push_modal_and_wait(
            lambda: SuitSelectModal(),
            timeout=30,
            description="suit selection",
        )
        if result:
            suit_map = {s.value: s for s in CardSuit}
            return suit_map.get(result, list(CardSuit)[0])
        return list(CardSuit)[0]

    # ================================================================== #
    #  GameUI Protocol — 玩家操作                                         #
    # ================================================================== #

    def choose_target(self, player, targets, prompt="选择目标"):
        """选择目标 → TargetSelectModal."""
        from ui.textual_ui.modals.target_modal import TargetSelectModal

        result = self._push_modal_and_wait(
            lambda: TargetSelectModal(targets=targets, prompt=prompt),
            timeout=60,
            description="target selection",
        )
        if result is not None and 0 <= result < len(targets):
            return targets[result]
        return None

    def choose_card_to_play(self, player):
        return None

    def choose_cards_to_discard(self, player, count):
        if count <= 0:
            return []
        selected = self._call_screen_helper(
            "_select_cards_from_candidates",
            list(player.hand),
            count,
            title=f"🗑 请选择弃掉 {count} 张牌",
            confirm_text="✅ 确认弃牌",
            countdown=30,
            timeout=35.0,
            auto_select_on_timeout=True,
            description="discard selection",
            default=None,
            log_context="select discard cards",
        )
        if selected and len(selected) == min(count, len(player.hand)):
            return list(selected)
        return list(player.hand[-count:])

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

    def request_skill_card(self, player, skill_name: str, candidates: list):
        if not candidates:
            return None
        return self._call_screen_helper(
            "_select_single_card_from_candidates",
            list(candidates),
            title=self._skill_prompt(skill_name),
            confirm_text="✅ 确认选择",
            cancel_text="❌ 放弃",
            countdown=30,
            timeout=35.0,
            auto_select_on_timeout=False,
            description="skill card selection",
            default=None,
            log_context=f"select card for skill {skill_name}",
        )

    def choose_card_to_show(self, player):
        if not getattr(player, "hand", None):
            return None
        return self._call_screen_helper(
            "_select_single_card_from_candidates",
            list(player.hand),
            title="🔥 火攻：请选择要展示的手牌",
            confirm_text="✅ 确认展示",
            cancel_text="❌ 放弃",
            countdown=30,
            timeout=35.0,
            auto_select_on_timeout=False,
            description="card reveal selection",
            default=None,
            log_context="select card to show",
        )

    def choose_card_to_discard_for_huogong(self, player, suit):
        matching = [card for card in player.hand if card.suit == suit]
        if not matching:
            return None
        return self._call_screen_helper(
            "_select_single_card_from_candidates",
            matching,
            title=f"🔥 火攻：请选择 1 张 {suit.symbol} 花色手牌弃置",
            confirm_text="✅ 确认弃置",
            cancel_text="❌ 放弃",
            countdown=30,
            timeout=35.0,
            auto_select_on_timeout=False,
            description="huogong discard selection",
            default=None,
            log_context="select huogong discard card",
        )
