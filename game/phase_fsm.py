"""阶段有限状态机 (Phase FSM)

提供回合阶段的合法转换验证，防止非法阶段跳转。
例如：不能从摸牌阶段直接跳到结束阶段，必须经过出牌和弃牌阶段。
"""

from __future__ import annotations

import logging

from .enums import GamePhase
from .exceptions import InvalidPhaseError

logger = logging.getLogger(__name__)

# 合法的阶段转换表
# key: 当前阶段, value: 允许转换到的目标阶段集合
VALID_TRANSITIONS: dict[GamePhase, set[GamePhase]] = {
    GamePhase.PREPARE: {GamePhase.JUDGE},
    GamePhase.JUDGE: {GamePhase.DRAW},
    GamePhase.DRAW: {GamePhase.PLAY},
    GamePhase.PLAY: {GamePhase.DISCARD},
    GamePhase.DISCARD: {GamePhase.END},
    GamePhase.END: {GamePhase.PREPARE},  # 下一个玩家的回合
}


class InvalidPhaseTransition(InvalidPhaseError):
    """非法阶段转换异常

    当尝试进行不合法的阶段转换时抛出，
    例如从 DRAW 直接跳到 END。
    """

    def __init__(
        self,
        current_phase: GamePhase,
        target_phase: GamePhase,
    ):
        message = f"Invalid phase transition: {current_phase.name} → {target_phase.name}"
        super().__init__(
            message=message,
            current_phase=current_phase.name,
            expected_phase=target_phase.name,
        )
        self.from_phase = current_phase
        self.to_phase = target_phase


class PhaseFSM:
    """回合阶段有限状态机

    管理当前阶段状态，并在转换时校验合法性。

    使用方式::

        fsm = PhaseFSM()
        fsm.transition(GamePhase.JUDGE)   # OK: PREPARE → JUDGE
        fsm.transition(GamePhase.PLAY)    # 抛出 InvalidPhaseTransition
    """

    def __init__(self) -> None:
        self._phase: GamePhase = GamePhase.PREPARE

    @property
    def current(self) -> GamePhase:
        """当前阶段"""
        return self._phase

    def transition(self, target: GamePhase) -> None:
        """转换到目标阶段

        Args:
            target: 目标阶段

        Raises:
            InvalidPhaseTransition: 如果转换不合法
        """
        valid = VALID_TRANSITIONS.get(self._phase, set())
        if target not in valid:
            raise InvalidPhaseTransition(self._phase, target)
        logger.debug("Phase transition: %s → %s", self._phase.name, target.name)
        self._phase = target

    def can_transition(self, target: GamePhase) -> bool:
        """检查是否可以转换到目标阶段

        Args:
            target: 目标阶段

        Returns:
            是否可以转换
        """
        return target in VALID_TRANSITIONS.get(self._phase, set())

    def can_play_card(self) -> bool:
        """当前是否处于可出牌阶段"""
        return self._phase == GamePhase.PLAY

    def reset(self) -> None:
        """重置到准备阶段（新回合开始时调用）"""
        self._phase = GamePhase.PREPARE
