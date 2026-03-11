"""请求处理器模块
统一 AI 和人类玩家的输入请求接口.

M1-T03: 将 engine.py 中所有 self.ui.ask_for_* 调用
        替换为通过 RequestHandler 统一路由。
"""

from __future__ import annotations

import logging
import random
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .actions import GameRequest, GameResponse, RequestType

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .card import Card, CardSuit
    from .engine import GameEngine
    from .player import Player


class RequestHandler(ABC):
    """请求处理器抽象基类.

    所有玩家输入场景（出闪、出杀、出桃、无懈可击、选牌、选花色等）
    统一通过此接口路由，实现 UI/AI 解耦。
    """

    @abstractmethod
    def request_shan(self, player: Player) -> Card | None:
        """请求玩家打出闪，返回打出的闪牌或 None."""
        ...

    @abstractmethod
    def request_sha(self, player: Player) -> Card | None:
        """请求玩家打出杀，返回打出的杀牌或 None."""
        ...

    @abstractmethod
    def request_tao(self, savior: Player, dying: Player) -> Card | None:
        """请求玩家使用桃救援，返回打出的桃牌或 None."""
        ...

    @abstractmethod
    def request_wuxie(
        self,
        responder: Player,
        trick_card: Card,
        source: Player,
        target: Player | None,
        is_cancelled: bool,
    ) -> Card | None:
        """请求玩家打出无懈可击，返回打出的无懈牌或 None."""
        ...

    @abstractmethod
    def choose_card_from_player(self, chooser: Player, target: Player) -> Card | None:
        """选择目标角色的一张牌（过河拆桥/顺手牵羊）."""
        ...

    @abstractmethod
    def choose_card_to_show(self, player: Player) -> Card | None:
        """选择一张手牌展示（火攻）."""
        ...

    @abstractmethod
    def choose_card_to_discard_for_huogong(self, player: Player, suit: CardSuit) -> Card | None:
        """选择一张指定花色的手牌弃置（火攻后续）."""
        ...

    @abstractmethod
    def choose_suit(self, player: Player) -> CardSuit:
        """选择一种花色（反间）."""
        ...

    @abstractmethod
    def guanxing_selection(
        self, player: Player, cards: list[Card]
    ) -> tuple[list[Card], list[Card]]:
        """观星排列：返回 (置顶牌列表, 置底牌列表)."""
        ...

    @abstractmethod
    def ask_zhuque_convert(self, player: Player) -> bool:
        """询问是否将普通杀转为火杀（朱雀羽扇）."""
        ...

    @abstractmethod
    def ask_for_jijiang(self, player: Player) -> Card | None:
        """激将：请求蜀国角色代打杀."""
        ...

    @abstractmethod
    def ask_for_hujia(self, player: Player) -> Card | None:
        """护驾：请求魏国角色代打闪."""
        ...

    @abstractmethod
    def request_discard(self, player: Player, min_cards: int, max_cards: int) -> list[Card]:
        """请求玩家弃牌，返回选择的牌列表."""
        ...

    @abstractmethod
    def request_skill_card(
        self, player: Player, skill_name: str, candidates: list[Card]
    ) -> Card | None:
        """请求玩家为技能选择一张牌（如龙胆、武圣转化）。.

        Args:
            player: 使用技能的玩家。
            skill_name: 技能标识 (如 "longdan_as_shan", "wusheng_as_sha")。
            candidates: 可选牌列表。

        Returns:
            选中的牌, 或 None 表示放弃。
        """
        ...


class DefaultRequestHandler(RequestHandler):
    """默认请求处理器.

    将现有 AI 自动决策 / UI 回调 / 无 UI 回退 三分支逻辑
    从 engine.py 提取到此处统一管理。
    """

    def __init__(self, engine: GameEngine):
        self.engine = engine

    # ---------- 内部工具 ----------

    def _get_ui(self):
        return self.engine.ui

    # ---------- 出闪 ----------

    def request_shan(self, player: Player) -> Card | None:
        from .card import CardName

        shan_cards = player.get_cards_by_name(CardName.SHAN)
        if not shan_cards:
            return None

        if player.is_ai:
            return shan_cards[0]

        ui = self._get_ui()
        if ui:
            return ui.ask_for_shan(player)

        # 无 UI 回退
        return shan_cards[0]

    # ---------- 出杀 ----------

    def request_sha(self, player: Player) -> Card | None:
        from .card import CardName

        sha_cards = player.get_cards_by_name(CardName.SHA)
        if not sha_cards:
            return None

        if player.is_ai:
            return sha_cards[0]

        ui = self._get_ui()
        if ui:
            return ui.ask_for_sha(player)

        return sha_cards[0]

    # ---------- 出桃 ----------

    def request_tao(self, savior: Player, dying: Player) -> Card | None:
        from .card import CardName

        tao_cards = savior.get_cards_by_name(CardName.TAO)
        if not tao_cards:
            return None

        if savior.is_ai:
            should_save = self.engine._ai_should_save(savior, dying)
            return tao_cards[0] if should_save else None

        ui = self._get_ui()
        if ui:
            return ui.ask_for_tao(savior, dying)

        return None

    # ---------- 无懈可击 ----------

    def request_wuxie(
        self,
        responder: Player,
        trick_card: Card,
        source: Player,
        target: Player | None,
        is_cancelled: bool,
    ) -> Card | None:
        from .card import CardName

        wuxie_cards = responder.get_cards_by_name(CardName.WUXIE)
        if not wuxie_cards:
            return None

        if responder.is_ai:
            should = self.engine._ai_should_wuxie(
                responder, source, target, trick_card, is_cancelled
            )
            return wuxie_cards[0] if should else None

        ui = self._get_ui()
        if ui:
            return ui.ask_for_wuxie(responder, trick_card, source, target, is_cancelled)

        return None

    # ---------- 选牌 ----------

    def choose_card_from_player(self, chooser: Player, target: Player) -> Card | None:
        all_cards = target.get_all_cards()
        if not all_cards:
            return None

        if chooser.is_ai:
            return random.choice(all_cards)

        ui = self._get_ui()
        if ui:
            return ui.choose_card_from_player(chooser, target)

        return random.choice(all_cards)

    def choose_card_to_show(self, player: Player) -> Card | None:
        if not player.hand:
            return None

        if player.is_ai:
            return random.choice(player.hand)

        ui = self._get_ui()
        if ui and hasattr(ui, "choose_card_to_show"):
            return ui.choose_card_to_show(player)

        return player.hand[0]

    def choose_card_to_discard_for_huogong(self, player: Player, suit: CardSuit) -> Card | None:
        matching = [c for c in player.hand if c.suit == suit]
        if not matching:
            return None

        if player.is_ai:
            return matching[0]

        ui = self._get_ui()
        if ui and hasattr(ui, "choose_card_to_discard_for_huogong"):
            return ui.choose_card_to_discard_for_huogong(player, suit)

        return matching[0]

    # ---------- 选花色 ----------

    def choose_suit(self, player: Player) -> CardSuit:
        from .card import CardSuit

        if player.is_ai:
            return random.choice(list(CardSuit))

        ui = self._get_ui()
        if ui and hasattr(ui, "choose_suit"):
            return ui.choose_suit(player)

        return random.choice(list(CardSuit))

    # ---------- 观星 ----------

    def guanxing_selection(
        self, player: Player, cards: list[Card]
    ) -> tuple[list[Card], list[Card]]:
        from .card import CardName

        if player.is_ai:

            def card_priority(c) -> int:
                if c.name == CardName.TAO:
                    return 0
                elif c.name == CardName.SHAN:
                    return 1
                elif c.name == CardName.SHA:
                    return 2
                elif c.name == CardName.WUZHONG:
                    return 3
                return 10

            sorted_cards = sorted(cards, key=card_priority)
            half = len(sorted_cards) // 2
            return sorted_cards[: half + 1], sorted_cards[half + 1 :]

        ui = self._get_ui()
        if ui and hasattr(ui, "guanxing_selection"):
            return ui.guanxing_selection(player, cards)

        # 无 UI 回退
        half = len(cards) // 2
        return cards[: half + 1], cards[half + 1 :]

    # ---------- 朱雀羽扇 ----------

    def ask_zhuque_convert(self, player: Player) -> bool:
        if player.is_ai:
            return True  # AI 总是转火杀

        ui = self._get_ui()
        if ui and hasattr(ui, "ask_zhuque_convert"):
            return ui.ask_zhuque_convert(player)

        return False

    # ---------- 激将 ----------

    def ask_for_jijiang(self, player: Player) -> Card | None:
        from .card import CardName

        sha_cards = player.get_cards_by_name(CardName.SHA)
        if not sha_cards:
            return None

        if player.is_ai:
            return sha_cards[0]

        ui = self._get_ui()
        if ui and hasattr(ui, "ask_for_jijiang"):
            return ui.ask_for_jijiang(player)

        return None

    # ---------- 护驾 ----------

    def ask_for_hujia(self, player: Player) -> Card | None:
        from .card import CardName

        shan_cards = player.get_cards_by_name(CardName.SHAN)
        if not shan_cards:
            return None

        if player.is_ai:
            return shan_cards[0]

        ui = self._get_ui()
        if ui and hasattr(ui, "ask_for_hujia"):
            return ui.ask_for_hujia(player)

        return None

    def request_discard(self, player: Player, min_cards: int, max_cards: int) -> list[Card]:
        if max_cards <= 0 or not player.hand:
            return []

        discard_count = min(max_cards, len(player.hand))

        if player.is_ai and player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            cards = list(bot.choose_discard(player, discard_count, self.engine))
            if len(cards) >= min_cards:
                return cards[:discard_count]

        ui = self._get_ui()
        if ui and hasattr(ui, "choose_cards_to_discard"):
            selected = ui.choose_cards_to_discard(player, discard_count)
            if selected is not None:
                selected_cards = list(selected)[:discard_count]
                if len(selected_cards) >= min_cards:
                    return selected_cards
        if min_cards == 0:
            return []

        return list(player.hand[-discard_count:])

    def request_skill_card(
        self, player: Player, skill_name: str, candidates: list[Card]
    ) -> Card | None:
        if not candidates:
            return None

        if player.is_ai:
            return candidates[0]  # AI 自动选第一张

        ui = self._get_ui()
        if ui and hasattr(ui, "request_skill_card"):
            return ui.request_skill_card(player, skill_name, candidates)
        return None


class NetworkRequestHandler(DefaultRequestHandler):
    """联机请求处理器.

    保持同步引擎模型不变，把真人玩家的同步请求桥接到网络层的
    `GAME_REQUEST` / `GAME_RESPONSE` 往返中；AI 和本地 UI 仍复用
    `DefaultRequestHandler` 的现有逻辑。
    """

    def __init__(
        self,
        engine: GameEngine,
        request_callback: Callable[[GameRequest], GameResponse],
        connected_player_ids: set[int] | None = None,
    ):
        super().__init__(engine)
        self._request_callback = request_callback
        self._connected_player_ids = set(connected_player_ids or set())

    def _is_network_human(self, player: Player) -> bool:
        return (
            not player.is_ai
            and player.id in self._connected_player_ids
            and self._request_callback is not None
        )

    @staticmethod
    def _serialize_card(card: Card) -> dict[str, Any]:
        data = card.to_dict()
        data["display_name"] = card.display_name
        return data

    @staticmethod
    def _resolve_single_card(candidates: list[Card], response: GameResponse) -> Card | None:
        if not response.accepted or not response.card_ids:
            return None

        cards_by_id = {card.id: card for card in candidates}
        return cards_by_id.get(response.card_ids[0])

    @staticmethod
    def _resolve_multiple_cards(
        candidates: list[Card],
        response: GameResponse,
        min_cards: int,
        max_cards: int,
    ) -> list[Card]:
        if not response.accepted:
            return []

        selected_ids = response.card_ids
        if len(selected_ids) < min_cards or len(selected_ids) > max_cards:
            return []

        cards_by_id = {card.id: card for card in candidates}
        selected: list[Card] = []
        seen: set[str] = set()
        for card_id in selected_ids:
            if card_id in seen or card_id not in cards_by_id:
                return []
            seen.add(card_id)
            selected.append(cards_by_id[card_id])
        return selected

    @staticmethod
    def _new_choice_token(prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex}"

    def _build_target_card_choices(
        self, target: Player
    ) -> tuple[list[dict[str, Any]], dict[str, Card | list[Card]]]:
        choices: list[dict[str, Any]] = []
        resolved: dict[str, Card | list[Card]] = {}

        if target.hand:
            hand_token = self._new_choice_token("hand")
            choices.append(
                {
                    "token": hand_token,
                    "zone": "hand",
                    "hidden": True,
                    "count": len(target.hand),
                    "label": "手牌（随机一张）",
                }
            )
            resolved[hand_token] = list(target.hand)

        for card in target.equipment.get_all_cards():
            token = self._new_choice_token("equipment")
            choices.append(
                {
                    "token": token,
                    "zone": "equipment",
                    "hidden": False,
                    "label": card.display_name,
                    "card": self._serialize_card(card),
                }
            )
            resolved[token] = card

        return choices, resolved

    @staticmethod
    def _resolve_card_choice(
        candidates: dict[str, Card | list[Card]],
        response: GameResponse,
    ) -> Card | None:
        if not response.accepted or not isinstance(response.option, str):
            return None

        selected = candidates.get(response.option)
        if selected is None:
            return None
        if isinstance(selected, list):
            return random.choice(selected) if selected else None
        return selected

    @staticmethod
    def _resolve_ordered_cards(candidates: list[Card], card_ids: list[str]) -> list[Card] | None:
        if len(card_ids) != len(set(card_ids)):
            return None

        cards_by_id = {card.id: card for card in candidates}
        ordered: list[Card] = []
        for card_id in card_ids:
            card = cards_by_id.get(card_id)
            if card is None:
                return None
            ordered.append(card)
        return ordered

    def _perform_request(self, request: GameRequest) -> GameResponse:
        try:
            return self._request_callback(request)
        except Exception as exc:
            logger.warning("Network request bridge failed: %s", exc)
            return GameResponse(
                request_type=request.request_type,
                player_id=request.player_id,
                accepted=False,
            )

    def _request_single_card(
        self,
        player: Player,
        request_type: RequestType,
        candidates: list[Card],
        *,
        required: bool = False,
        extra_options: dict[str, Any] | None = None,
    ) -> Card | None:
        if not candidates:
            return None

        request = GameRequest(
            request_type=request_type,
            player_id=player.id,
            options={
                "cards": [self._serialize_card(card) for card in candidates],
                **(extra_options or {}),
            },
            required=required,
            min_cards=1 if required else 0,
            max_cards=1,
        )
        response = self._perform_request(request)
        return self._resolve_single_card(candidates, response)

    def request_shan(self, player: Player) -> Card | None:
        from .card import CardName

        if not self._is_network_human(player):
            return super().request_shan(player)

        shan_cards = player.get_cards_by_name(CardName.SHAN)
        return self._request_single_card(
            player,
            RequestType.PLAY_SHAN,
            shan_cards,
            extra_options={"reason": "request_shan"},
        )

    def request_sha(self, player: Player) -> Card | None:
        from .card import CardName

        if not self._is_network_human(player):
            return super().request_sha(player)

        sha_cards = player.get_cards_by_name(CardName.SHA)
        return self._request_single_card(
            player,
            RequestType.PLAY_SHA,
            sha_cards,
            extra_options={"reason": "request_sha"},
        )

    def request_tao(self, savior: Player, dying: Player) -> Card | None:
        from .card import CardName

        if not self._is_network_human(savior):
            return super().request_tao(savior, dying)

        tao_cards = savior.get_cards_by_name(CardName.TAO)
        return self._request_single_card(
            savior,
            RequestType.PLAY_TAO,
            tao_cards,
            extra_options={
                "reason": "request_tao",
                "dying_player_id": dying.id,
                "dying_player_name": dying.name,
            },
        )

    def request_wuxie(
        self,
        responder: Player,
        trick_card: Card,
        source: Player,
        target: Player | None,
        is_cancelled: bool,
    ) -> Card | None:
        from .card import CardName

        if not self._is_network_human(responder):
            return super().request_wuxie(responder, trick_card, source, target, is_cancelled)

        wuxie_cards = responder.get_cards_by_name(CardName.WUXIE)
        return self._request_single_card(
            responder,
            RequestType.PLAY_WUXIE,
            wuxie_cards,
            extra_options={
                "reason": "request_wuxie",
                "trick_card": self._serialize_card(trick_card),
                "source_player_id": source.id,
                "source_player_name": source.name,
                "target_player_id": target.id if target else None,
                "target_player_name": target.name if target else None,
                "is_cancelled": is_cancelled,
            },
        )

    def choose_card_from_player(self, chooser: Player, target: Player) -> Card | None:
        if not self._is_network_human(chooser):
            return super().choose_card_from_player(chooser, target)

        all_cards = target.get_all_cards()
        if not all_cards:
            return None

        choices, resolved = self._build_target_card_choices(target)
        if not choices:
            return None

        response = self._perform_request(
            GameRequest(
                request_type=RequestType.CHOOSE_OPTION,
                player_id=chooser.id,
                required=True,
                options={
                    "reason": "choose_card_from_player",
                    "target_player_id": target.id,
                    "target_player_name": target.name,
                    "choices": choices,
                },
            )
        )
        selected = self._resolve_card_choice(resolved, response)
        if selected in all_cards:
            return selected
        return super().choose_card_from_player(chooser, target)

    def choose_card_to_show(self, player: Player) -> Card | None:
        if not self._is_network_human(player):
            return super().choose_card_to_show(player)

        return self._request_single_card(
            player,
            RequestType.CHOOSE_CARD,
            list(player.hand),
            required=True,
            extra_options={"reason": "choose_card_to_show"},
        )

    def choose_card_to_discard_for_huogong(self, player: Player, suit: CardSuit) -> Card | None:
        if not self._is_network_human(player):
            return super().choose_card_to_discard_for_huogong(player, suit)

        matching = [c for c in player.hand if c.suit == suit]
        return self._request_single_card(
            player,
            RequestType.CHOOSE_CARD,
            matching,
            extra_options={
                "reason": "choose_card_to_discard_for_huogong",
                "required_suit": suit.value,
            },
        )

    def choose_suit(self, player: Player) -> CardSuit:
        from .card import CardSuit

        if not self._is_network_human(player):
            return super().choose_suit(player)

        response = self._perform_request(
            GameRequest(
                request_type=RequestType.CHOOSE_SUIT,
                player_id=player.id,
                required=True,
                options={
                    "reason": "choose_suit",
                    "suits": [suit.value for suit in CardSuit],
                },
            )
        )
        if response.accepted and isinstance(response.option, str):
            try:
                return CardSuit(response.option)
            except ValueError:
                pass
        return super().choose_suit(player)

    def guanxing_selection(
        self, player: Player, cards: list[Card]
    ) -> tuple[list[Card], list[Card]]:
        if not self._is_network_human(player):
            return super().guanxing_selection(player, cards)

        if not cards:
            return [], []

        response = self._perform_request(
            GameRequest(
                request_type=RequestType.GUANXING,
                player_id=player.id,
                required=True,
                max_cards=len(cards),
                options={
                    "reason": "guanxing_selection",
                    "cards": [self._serialize_card(card) for card in cards],
                },
            )
        )
        bottom_ids = response.option
        if not response.accepted or not isinstance(bottom_ids, list):
            return super().guanxing_selection(player, cards)
        if not all(isinstance(card_id, str) for card_id in bottom_ids):
            return super().guanxing_selection(player, cards)
        bottom_card_ids = [card_id for card_id in bottom_ids if isinstance(card_id, str)]

        combined_ids = list(response.card_ids)
        combined_ids.extend(bottom_card_ids)
        expected_ids = {card.id for card in cards}
        if (
            len(combined_ids) != len(cards)
            or len(combined_ids) != len(set(combined_ids))
            or set(combined_ids) != expected_ids
        ):
            return super().guanxing_selection(player, cards)

        top_cards = self._resolve_ordered_cards(cards, response.card_ids)
        bottom_cards = self._resolve_ordered_cards(cards, bottom_card_ids)
        if top_cards is None or bottom_cards is None:
            return super().guanxing_selection(player, cards)
        return top_cards, bottom_cards

    def ask_zhuque_convert(self, player: Player) -> bool:
        if not self._is_network_human(player):
            return super().ask_zhuque_convert(player)

        response = self._perform_request(
            GameRequest(
                request_type=RequestType.CHOOSE_OPTION,
                player_id=player.id,
                required=True,
                options={
                    "reason": "ask_zhuque_convert",
                    "choices": [True, False],
                },
            )
        )
        if response.accepted and isinstance(response.option, bool):
            return response.option
        return super().ask_zhuque_convert(player)

    def ask_for_jijiang(self, player: Player) -> Card | None:
        from .card import CardName

        if not self._is_network_human(player):
            return super().ask_for_jijiang(player)

        sha_cards = player.get_cards_by_name(CardName.SHA)
        return self._request_single_card(
            player,
            RequestType.PLAY_SHA,
            sha_cards,
            extra_options={"reason": "ask_for_jijiang"},
        )

    def ask_for_hujia(self, player: Player) -> Card | None:
        from .card import CardName

        if not self._is_network_human(player):
            return super().ask_for_hujia(player)

        shan_cards = player.get_cards_by_name(CardName.SHAN)
        return self._request_single_card(
            player,
            RequestType.PLAY_SHAN,
            shan_cards,
            extra_options={"reason": "ask_for_hujia"},
        )

    def request_discard(self, player: Player, min_cards: int, max_cards: int) -> list[Card]:
        if not self._is_network_human(player):
            return super().request_discard(player, min_cards, max_cards)

        candidates = list(player.hand)
        if not candidates or max_cards <= 0:
            return []

        response = self._perform_request(
            GameRequest(
                request_type=RequestType.DISCARD,
                player_id=player.id,
                required=True,
                min_cards=min_cards,
                max_cards=max_cards,
                options={
                    "reason": "request_discard",
                    "cards": [self._serialize_card(card) for card in candidates],
                },
            )
        )
        selected = self._resolve_multiple_cards(candidates, response, min_cards, max_cards)
        if len(selected) < min_cards:
            return super().request_discard(player, min_cards, max_cards)
        return selected

    def request_skill_card(
        self, player: Player, skill_name: str, candidates: list[Card]
    ) -> Card | None:
        if not self._is_network_human(player):
            return super().request_skill_card(player, skill_name, candidates)

        return self._request_single_card(
            player,
            RequestType.CHOOSE_CARD,
            candidates,
            extra_options={
                "reason": "request_skill_card",
                "skill_name": skill_name,
            },
        )
