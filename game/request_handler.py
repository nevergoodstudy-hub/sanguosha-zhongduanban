# -*- coding: utf-8 -*-
"""
请求处理器模块
统一 AI 和人类玩家的输入请求接口

M1-T03: 将 engine.py 中所有 self.ui.ask_for_* 调用
        替换为通过 RequestHandler 统一路由。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from .player import Player
    from .card import Card, CardSuit
    from .engine import GameEngine


class RequestHandler(ABC):
    """
    请求处理器抽象基类

    所有玩家输入场景（出闪、出杀、出桃、无懈可击、选牌、选花色等）
    统一通过此接口路由，实现 UI/AI 解耦。
    """

    @abstractmethod
    def request_shan(self, player: 'Player') -> Optional['Card']:
        """请求玩家打出闪，返回打出的闪牌或 None"""
        ...

    @abstractmethod
    def request_sha(self, player: 'Player') -> Optional['Card']:
        """请求玩家打出杀，返回打出的杀牌或 None"""
        ...

    @abstractmethod
    def request_tao(self, savior: 'Player', dying: 'Player') -> Optional['Card']:
        """请求玩家使用桃救援，返回打出的桃牌或 None"""
        ...

    @abstractmethod
    def request_wuxie(
        self,
        responder: 'Player',
        trick_card: 'Card',
        source: 'Player',
        target: Optional['Player'],
        is_cancelled: bool,
    ) -> Optional['Card']:
        """请求玩家打出无懈可击，返回打出的无懈牌或 None"""
        ...

    @abstractmethod
    def choose_card_from_player(
        self, chooser: 'Player', target: 'Player'
    ) -> Optional['Card']:
        """选择目标角色的一张牌（过河拆桥/顺手牵羊）"""
        ...

    @abstractmethod
    def choose_card_to_show(self, player: 'Player') -> Optional['Card']:
        """选择一张手牌展示（火攻）"""
        ...

    @abstractmethod
    def choose_card_to_discard_for_huogong(
        self, player: 'Player', suit: 'CardSuit'
    ) -> Optional['Card']:
        """选择一张指定花色的手牌弃置（火攻后续）"""
        ...

    @abstractmethod
    def choose_suit(self, player: 'Player') -> 'CardSuit':
        """选择一种花色（反间）"""
        ...

    @abstractmethod
    def guanxing_selection(
        self, player: 'Player', cards: List['Card']
    ) -> Tuple[List['Card'], List['Card']]:
        """观星排列：返回 (置顶牌列表, 置底牌列表)"""
        ...

    @abstractmethod
    def ask_zhuque_convert(self, player: 'Player') -> bool:
        """询问是否将普通杀转为火杀（朱雀羽扇）"""
        ...

    @abstractmethod
    def ask_for_jijiang(self, player: 'Player') -> Optional['Card']:
        """激将：请求蜀国角色代打杀"""
        ...

    @abstractmethod
    def ask_for_hujia(self, player: 'Player') -> Optional['Card']:
        """护驾：请求魏国角色代打闪"""
        ...


class DefaultRequestHandler(RequestHandler):
    """
    默认请求处理器

    将现有 AI 自动决策 / UI 回调 / 无 UI 回退 三分支逻辑
    从 engine.py 提取到此处统一管理。
    """

    def __init__(self, engine: 'GameEngine'):
        self.engine = engine

    # ---------- 内部工具 ----------

    def _get_ui(self):
        return self.engine.ui

    # ---------- 出闪 ----------

    def request_shan(self, player: 'Player') -> Optional['Card']:
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

    def request_sha(self, player: 'Player') -> Optional['Card']:
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

    def request_tao(self, savior: 'Player', dying: 'Player') -> Optional['Card']:
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
        responder: 'Player',
        trick_card: 'Card',
        source: 'Player',
        target: 'Player | None',
        is_cancelled: bool,
    ) -> Optional['Card']:
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

    def choose_card_from_player(
        self, chooser: 'Player', target: 'Player'
    ) -> Optional['Card']:
        all_cards = target.get_all_cards()
        if not all_cards:
            return None

        if chooser.is_ai:
            return random.choice(all_cards)

        ui = self._get_ui()
        if ui:
            return ui.choose_card_from_player(chooser, target)

        return random.choice(all_cards)

    def choose_card_to_show(self, player: 'Player') -> Optional['Card']:
        if not player.hand:
            return None

        if player.is_ai:
            return random.choice(player.hand)

        ui = self._get_ui()
        if ui and hasattr(ui, 'choose_card_to_show'):
            return ui.choose_card_to_show(player)

        return player.hand[0]

    def choose_card_to_discard_for_huogong(
        self, player: 'Player', suit: 'CardSuit'
    ) -> Optional['Card']:
        matching = [c for c in player.hand if c.suit == suit]
        if not matching:
            return None

        if player.is_ai:
            return matching[0]

        ui = self._get_ui()
        if ui and hasattr(ui, 'choose_card_to_discard_for_huogong'):
            return ui.choose_card_to_discard_for_huogong(player, suit)

        return matching[0]

    # ---------- 选花色 ----------

    def choose_suit(self, player: 'Player') -> 'CardSuit':
        from .card import CardSuit

        if player.is_ai:
            return random.choice(list(CardSuit))

        ui = self._get_ui()
        if ui and hasattr(ui, 'choose_suit'):
            return ui.choose_suit(player)

        return random.choice(list(CardSuit))

    # ---------- 观星 ----------

    def guanxing_selection(
        self, player: 'Player', cards: List['Card']
    ) -> Tuple[List['Card'], List['Card']]:
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
            return sorted_cards[:half + 1], sorted_cards[half + 1:]

        ui = self._get_ui()
        if ui and hasattr(ui, 'guanxing_selection'):
            return ui.guanxing_selection(player, cards)

        # 无 UI 回退
        half = len(cards) // 2
        return cards[:half + 1], cards[half + 1:]

    # ---------- 朱雀羽扇 ----------

    def ask_zhuque_convert(self, player: 'Player') -> bool:
        if player.is_ai:
            return True  # AI 总是转火杀

        ui = self._get_ui()
        if ui and hasattr(ui, 'ask_zhuque_convert'):
            return ui.ask_zhuque_convert(player)

        return False

    # ---------- 激将 ----------

    def ask_for_jijiang(self, player: 'Player') -> Optional['Card']:
        from .card import CardName
        sha_cards = player.get_cards_by_name(CardName.SHA)
        if not sha_cards:
            return None

        if player.is_ai:
            return sha_cards[0]

        ui = self._get_ui()
        if ui and hasattr(ui, 'ask_for_jijiang'):
            return ui.ask_for_jijiang(player)

        return None

    # ---------- 护驾 ----------

    def ask_for_hujia(self, player: 'Player') -> Optional['Card']:
        from .card import CardName
        shan_cards = player.get_cards_by_name(CardName.SHAN)
        if not shan_cards:
            return None

        if player.is_ai:
            return shan_cards[0]

        ui = self._get_ui()
        if ui and hasattr(ui, 'ask_for_hujia'):
            return ui.ask_for_hujia(player)

        return None
