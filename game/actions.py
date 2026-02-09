"""动作与请求系统
定义玩家操作的标准化接口，实现 UI/逻辑分离
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

from i18n import t as _t

if TYPE_CHECKING:
    from .card import Card
    from .engine import GameEngine
    from .player import Player


class ActionType(Enum):
    """动作类型枚举"""
    PLAY_CARD = auto()       # 出牌
    USE_SKILL = auto()       # 使用技能
    DISCARD = auto()         # 弃牌
    EQUIP = auto()           # 装备
    RESPOND = auto()         # 响应（出闪、出杀等）
    END_PHASE = auto()       # 结束阶段
    CHOOSE_TARGET = auto()   # 选择目标
    CHOOSE_CARD = auto()     # 选择卡牌
    CHOOSE_OPTION = auto()   # 选择选项


class RequestType(Enum):
    """请求类型枚举"""
    PLAY_SHAN = auto()       # 请求出闪
    PLAY_SHA = auto()        # 请求出杀
    PLAY_TAO = auto()        # 请求出桃
    PLAY_WUXIE = auto()      # 请求出无懈可击
    CHOOSE_TARGET = auto()   # 选择目标
    CHOOSE_CARD = auto()     # 选择卡牌
    CHOOSE_CARDS = auto()    # 选择多张卡牌
    CHOOSE_OPTION = auto()   # 选择选项
    CHOOSE_SUIT = auto()     # 选择花色
    GUANXING = auto()        # 观星排列
    DISCARD = auto()         # 弃牌


@dataclass
class GameAction(ABC):
    """游戏动作基类
    所有玩家操作都应继承此类
    """
    action_type: ActionType
    player_id: int
    timestamp: float = field(default_factory=lambda: __import__('time').time())

    @abstractmethod
    def validate(self, engine: GameEngine) -> tuple[bool, str]:
        """验证动作是否合法

        Returns:
            (是否合法, 错误信息)
        """
        pass

    @abstractmethod
    def execute(self, engine: GameEngine) -> bool:
        """执行动作

        Returns:
            是否执行成功
        """
        pass


@dataclass
class PlayCardAction(GameAction):
    """出牌动作"""
    action_type: ActionType = field(default=ActionType.PLAY_CARD, init=False)
    card_id: int = 0
    target_ids: list[int] = field(default_factory=list)

    def validate(self, engine: GameEngine) -> tuple[bool, str]:
        player = engine.get_player_by_id(self.player_id)
        if not player:
            return False, _t("error.player_not_found")

        # 检查是否是当前回合
        if engine.current_player.id != self.player_id:
            return False, _t("error.not_your_turn")

        # 检查卡牌是否存在
        card = None
        for c in player.hand:
            if id(c) == self.card_id or getattr(c, 'id', None) == self.card_id:
                card = c
                break

        if not card:
            return False, _t("error.card_not_found")

        return True, ""

    def execute(self, engine: GameEngine) -> bool:
        valid, msg = self.validate(engine)
        if not valid:
            return False

        player = engine.get_player_by_id(self.player_id)
        card = None
        for c in player.hand:
            if id(c) == self.card_id or getattr(c, 'id', None) == self.card_id:
                card = c
                break

        targets = [engine.get_player_by_id(tid) for tid in self.target_ids]
        targets = [t for t in targets if t is not None]

        return engine.use_card(player, card, targets)


@dataclass
class UseSkillAction(GameAction):
    """使用技能动作"""
    action_type: ActionType = field(default=ActionType.USE_SKILL, init=False)
    skill_id: str = ""
    target_ids: list[int] = field(default_factory=list)
    card_ids: list[int] = field(default_factory=list)

    def validate(self, engine: GameEngine) -> tuple[bool, str]:
        player = engine.get_player_by_id(self.player_id)
        if not player:
            return False, _t("error.player_not_found")

        if not engine.skill_system:
            return False, _t("error.skill_system_not_init")

        if not engine.skill_system.can_use_skill(self.skill_id, player):
            return False, _t("error.skill_cannot_use")

        return True, ""

    def execute(self, engine: GameEngine) -> bool:
        valid, msg = self.validate(engine)
        if not valid:
            return False

        player = engine.get_player_by_id(self.player_id)
        targets = [engine.get_player_by_id(tid) for tid in self.target_ids]
        targets = [t for t in targets if t is not None]

        # 获取卡牌
        cards = []
        for cid in self.card_ids:
            for c in player.hand:
                if id(c) == cid or getattr(c, 'id', None) == cid:
                    cards.append(c)
                    break

        return engine.skill_system.use_skill(
            self.skill_id, player,
            targets=targets if targets else None,
            cards=cards if cards else None
        )


@dataclass
class DiscardAction(GameAction):
    """弃牌动作"""
    action_type: ActionType = field(default=ActionType.DISCARD, init=False)
    card_ids: list[int] = field(default_factory=list)

    def validate(self, engine: GameEngine) -> tuple[bool, str]:
        player = engine.get_player_by_id(self.player_id)
        if not player:
            return False, _t("error.player_not_found")

        if len(self.card_ids) == 0:
            return False, _t("error.no_cards_selected")

        return True, ""

    def execute(self, engine: GameEngine) -> bool:
        valid, msg = self.validate(engine)
        if not valid:
            return False

        player = engine.get_player_by_id(self.player_id)
        cards = []
        for cid in self.card_ids:
            for c in player.hand:
                if id(c) == cid or getattr(c, 'id', None) == cid:
                    cards.append(c)
                    break

        if cards:
            engine.discard_cards(player, cards)
            return True
        return False


@dataclass
class RespondAction(GameAction):
    """响应动作（出闪、出杀等）"""
    action_type: ActionType = field(default=ActionType.RESPOND, init=False)
    card_id: int | None = None  # None 表示不响应
    skill_id: str | None = None  # 使用技能响应

    def validate(self, engine: GameEngine) -> tuple[bool, str]:
        player = engine.get_player_by_id(self.player_id)
        if not player:
            return False, _t("error.player_not_found")
        return True, ""

    def execute(self, engine: GameEngine) -> bool:
        # 响应的具体执行由请求处理器处理
        return True


@dataclass
class EndPhaseAction(GameAction):
    """结束阶段动作"""
    action_type: ActionType = field(default=ActionType.END_PHASE, init=False)

    def validate(self, engine: GameEngine) -> tuple[bool, str]:
        if engine.current_player.id != self.player_id:
            return False, _t("error.not_your_turn")
        return True, ""

    def execute(self, engine: GameEngine) -> bool:
        return True  # 由游戏流程控制


@dataclass
class GameRequest:
    """游戏请求
    引擎向玩家请求输入时使用
    """
    request_type: RequestType
    player_id: int
    message: str = ""
    options: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    required: bool = True  # 是否必须响应

    # 约束条件
    min_cards: int = 0
    max_cards: int = 1
    card_filter: str | None = None  # 卡牌过滤条件
    target_filter: str | None = None  # 目标过滤条件


@dataclass
class GameResponse:
    """游戏响应
    玩家对请求的响应
    """
    request_type: RequestType
    player_id: int
    accepted: bool = False  # 是否接受/响应
    card_ids: list[int] = field(default_factory=list)
    target_ids: list[int] = field(default_factory=list)
    option: str | int | bool | list[int] | None = None


class ActionValidator:
    """动作验证器
    集中处理所有动作的合法性校验
    """

    @staticmethod
    def validate_play_card(player: Player, card: Card,
                           targets: list[Player], engine: GameEngine) -> tuple[bool, str]:
        """验证出牌动作"""
        from .card import CardName
        from .constants import SkillId

        # 检查卡牌是否在手牌中
        if card not in player.hand:
            return False, _t("error.card_not_in_hand")

        # 杀的验证
        if card.name == CardName.SHA:
            if not player.can_use_sha():
                if not player.has_skill(SkillId.PAOXIAO):
                    return False, _t("error.sha_used")

            if not targets:
                return False, _t("error.sha_no_target")

            for target in targets:
                if not engine.is_in_attack_range(player, target):
                    return False, _t("error.target_out_of_range", target=target.name)

                # 空城检测
                if target.has_skill(SkillId.KONGCHENG) and target.hand_count == 0:
                    return False, _t("error.target_kongcheng", target=target.name)

        # 桃的验证
        if card.name == CardName.TAO:
            if player.hp >= player.max_hp:
                return False, _t("error.hp_full")

        # 闪不能主动使用
        if card.name == CardName.SHAN:
            return False, _t("error.shan_passive")

        # 顺手牵羊距离检测
        if card.name == CardName.SHUNSHOU:
            if not targets:
                return False, _t("error.shunshou_need_target")
            for target in targets:
                if engine.calculate_distance(player, target) > 1:
                    return False, _t("error.shunshou_too_far", target=target.name)

        return True, ""

    @staticmethod
    def validate_use_skill(player: Player, skill_id: str,
                           engine: GameEngine) -> tuple[bool, str]:
        """验证技能使用"""
        if not engine.skill_system:
            return False, _t("error.skill_system_not_init")

        if not engine.skill_system.can_use_skill(skill_id, player):
            return False, _t("error.skill_cannot_use")

        return True, ""


class ActionExecutor:
    """动作执行器
    负责执行经过验证的动作
    """

    def __init__(self, engine: GameEngine):
        self.engine = engine

    def execute(self, action: GameAction) -> bool:
        """执行动作"""
        valid, msg = action.validate(self.engine)
        if not valid:
            # 发送错误事件
            if self.engine.event_bus:
                self.engine.event_bus.emit(
                    __import__('game.events', fromlist=['EventType']).EventType.LOG_MESSAGE,
                    message=_t("error.invalid_action", msg=msg)
                )
            return False

        return action.execute(self.engine)
