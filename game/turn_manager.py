"""回合管理器模块
负责管理游戏回合的阶段流转

本模块将回合阶段管理逻辑从 GameEngine 中解耦，
提供清晰的阶段转换和技能触发时机。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from .constants import SkillId

# GamePhase 已提取到 enums.py，直接导入避免 engine → turn_manager → engine 循环
from .enums import GamePhase
from .events import EventType
from .hero import SkillTiming

# M1-T04: 阶段 → EventType 映射
_PHASE_START_EVENTS: dict[GamePhase, EventType] = {
    GamePhase.PREPARE: EventType.PHASE_PREPARE_START,
    GamePhase.JUDGE: EventType.PHASE_JUDGE_START,
    GamePhase.DRAW: EventType.PHASE_DRAW_START,
    GamePhase.PLAY: EventType.PHASE_PLAY_START,
    GamePhase.DISCARD: EventType.PHASE_DISCARD_START,
    GamePhase.END: EventType.PHASE_END_START,
}
_PHASE_END_EVENTS: dict[GamePhase, EventType] = {
    GamePhase.PREPARE: EventType.PHASE_PREPARE_END,
    GamePhase.JUDGE: EventType.PHASE_JUDGE_END,
    GamePhase.DRAW: EventType.PHASE_DRAW_END,
    GamePhase.PLAY: EventType.PHASE_PLAY_END,
    GamePhase.DISCARD: EventType.PHASE_DISCARD_END,
    GamePhase.END: EventType.PHASE_END_END,
}

if TYPE_CHECKING:
    from .engine import GameEngine
    from .player import Player


# 阶段顺序
PHASE_ORDER = [
    GamePhase.PREPARE,
    GamePhase.JUDGE,
    GamePhase.DRAW,
    GamePhase.PLAY,
    GamePhase.DISCARD,
    GamePhase.END,
]


class TurnManager:
    """回合管理器

    负责管理游戏回合的阶段流转：
    - 阶段顺序控制
    - 阶段跳过处理
    - 技能触发时机管理
    """

    def __init__(self, engine: GameEngine):
        """初始化回合管理器

        Args:
            engine: 游戏引擎引用
        """
        self.engine = engine
        self.current_phase = GamePhase.PREPARE
        self._phase_handlers: dict[GamePhase, Callable] = {}
        self._init_phase_handlers()

    def _init_phase_handlers(self) -> None:
        """初始化阶段处理器"""
        self._phase_handlers = {
            GamePhase.PREPARE: self._execute_prepare_phase,
            GamePhase.JUDGE: self._execute_judge_phase,
            GamePhase.DRAW: self._execute_draw_phase,
            GamePhase.PLAY: self._execute_play_phase,
            GamePhase.DISCARD: self._execute_discard_phase,
            GamePhase.END: self._execute_end_phase,
        }

    def run_turn(self, player: Player) -> None:
        """执行玩家的完整回合

        Args:
            player: 当前回合玩家
        """
        if not player.is_alive:
            return

        # M1-T04: 发布回合开始语义事件
        self.engine.event_bus.emit(EventType.TURN_START, player=player)
        self.engine.log_event("turn_start", _t("turn.start", name=player.name))
        player.reset_turn()

        # 按顺序执行各阶段
        for phase in PHASE_ORDER:
            if not player.is_alive:
                break
            self._execute_phase(player, phase)

        self.engine.log_event("turn_end", _t("turn.end", name=player.name))
        # M1-T04: 发布回合结束语义事件
        self.engine.event_bus.emit(EventType.TURN_END, player=player)

    def _execute_phase(self, player: Player, phase: GamePhase) -> None:
        """执行指定阶段

        Args:
            player: 当前回合玩家
            phase: 要执行的阶段
        """
        self.current_phase = phase
        self.engine.phase = phase

        # M1-T04: 发布阶段开始/结束语义事件
        start_evt = _PHASE_START_EVENTS.get(phase)
        if start_evt:
            self.engine.event_bus.emit(start_evt, player=player)

        handler = self._phase_handlers.get(phase)
        if handler:
            handler(player)

        end_evt = _PHASE_END_EVENTS.get(phase)
        if end_evt:
            self.engine.event_bus.emit(end_evt, player=player)

    def _execute_prepare_phase(self, player: Player) -> None:
        """执行准备阶段"""
        self.engine.log_event("phase", _t("turn.phase_prepare"))

        # 触发准备阶段技能（如观星）
        if self.engine.skill_system and player.hero:
            for skill in player.hero.skills:
                if skill.timing and skill.timing == SkillTiming.PREPARE:
                    self.engine.skill_system.trigger_skill(skill.id, player, self.engine)

    def _execute_judge_phase(self, player: Player) -> None:
        """执行判定阶段 — 直接调用 JudgeSystem (Phase 2.6)"""
        self.engine.judge_sys.phase_judge(player)

    def _execute_draw_phase(self, player: Player) -> None:
        """执行摸牌阶段"""
        # 检查是否跳过（兵粮寸断）
        if player.skip_draw_phase:
            self.engine.log_event("phase", _t("turn.draw_skipped"))
            player.skip_draw_phase = False
            return

        self.engine.log_event("phase", _t("turn.phase_draw"))

        # 基础摸牌数
        draw_count = 2

        # 英姿技能：多摸一张
        if player.has_skill(SkillId.YINGZI):
            draw_count += 1
            self.engine.log_event("skill", _t("turn.yingzi", name=player.name))

        # 突袭技能在摸牌阶段触发
        if player.has_skill(SkillId.TUXI):
            if self._try_trigger_tuxi(player, draw_count):
                return  # 突袭成功，跳过正常摸牌

        cards = self.engine.deck.draw(draw_count)
        player.draw_cards(cards)
        self.engine.log_event("draw_cards", _t("resolver.drew_cards", name=player.name, count=len(cards)))

    def _try_trigger_tuxi(self, player: Player, draw_count: int) -> bool:
        """尝试触发突袭技能

        突袭规则：摸牌阶段，可以少摸牌，然后获取等量其他角色各一张手牌（最多2人）

        Args:
            player: 当前玩家
            draw_count: 原本要摸的牌数

        Returns:
            是否成功触发突袭
        """
        from .skills.registry import get_registry

        # AI 决策是否使用突袭
        if player.is_ai and player.id in self.engine.ai_bots:
            targets = [
                p for p in self.engine.get_other_players(player)
                if p.hand_count > 0
            ]
            if not targets:
                return False

            # 最多选择 min(draw_count, 2) 个目标
            steal_count = min(draw_count, 2, len(targets))
            chosen_targets = targets[:steal_count]

            # 通过技能注册表调用突袭 handler
            registry = get_registry()
            tuxi_handler = registry.get("tuxi")
            if tuxi_handler:
                result = tuxi_handler(player, self.engine, targets=chosen_targets)
                if result:
                    # 突袭成功，补摸剩余牌数
                    remaining = draw_count - steal_count
                    if remaining > 0:
                        cards = self.engine.deck.draw(remaining)
                        player.draw_cards(cards)
                        self.engine.log_event("draw_cards",
                            _t("resolver.drew_cards", name=player.name, count=len(cards)))
                    return True
        return False

    def _execute_play_phase(self, player: Player) -> None:
        """执行出牌阶段"""
        # 检查是否跳过（乐不思蜀）
        if player.skip_play_phase:
            self.engine.log_event("phase", _t("turn.play_skipped"))
            player.skip_play_phase = False
            return

        self.engine.log_event("phase", _t("turn.phase_play"))

        if player.is_ai:
            self._ai_play_phase(player)
        else:
            self._human_play_phase(player)

    def _ai_play_phase(self, player: Player) -> None:
        """AI 出牌阶段"""
        if player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            bot.play_phase(player, self.engine)

    def _human_play_phase(self, player: Player) -> None:
        """人类玩家出牌阶段"""
        # 由 UI 控制
        pass

    def _execute_discard_phase(self, player: Player) -> None:
        """执行弃牌阶段"""
        discard_count = player.need_discard
        if discard_count > 0:
            self.engine.log_event(
                "phase",
                _t("turn.discard_phase", count=discard_count)
            )

            if player.is_ai:
                self._ai_discard(player, discard_count)

    def _ai_discard(self, player: Player, count: int) -> None:
        """AI 弃牌"""
        if player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            cards_to_discard = bot.choose_discard(player, count, self.engine)
            self.engine.discard_cards(player, cards_to_discard)

    def _execute_end_phase(self, player: Player) -> None:
        """执行结束阶段"""
        # 结束阶段技能（闭月等）由 skill_system 通过事件触发
        pass

    def get_current_phase(self) -> GamePhase:
        """获取当前阶段"""
        return self.current_phase

    def skip_phase(self, phase: GamePhase, player: Player) -> None:
        """跳过指定阶段

        Args:
            phase: 要跳过的阶段
            player: 玩家
        """
        if phase == GamePhase.DRAW:
            player.skip_draw_phase = True
        elif phase == GamePhase.PLAY:
            player.skip_play_phase = True


# ==================== 辅助函数 ====================


def get_phase_name(phase: GamePhase) -> str:
    """获取阶段名称 (i18n)"""
    key_map = {
        GamePhase.PREPARE: "turn.name_prepare",
        GamePhase.JUDGE: "turn.name_judge",
        GamePhase.DRAW: "turn.name_draw",
        GamePhase.PLAY: "turn.name_play",
        GamePhase.DISCARD: "turn.name_discard",
        GamePhase.END: "turn.name_end",
    }
    key = key_map.get(phase)
    return _t(key) if key else _t("turn.name_unknown")


def get_next_phase(current: GamePhase) -> GamePhase | None:
    """获取下一个阶段"""
    try:
        idx = PHASE_ORDER.index(current)
        if idx < len(PHASE_ORDER) - 1:
            return PHASE_ORDER[idx + 1]
    except ValueError:
        pass
    return None
