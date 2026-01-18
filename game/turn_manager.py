# -*- coding: utf-8 -*-
"""
回合管理器模块
负责管理游戏回合的阶段流转

本模块将回合阶段管理逻辑从 GameEngine 中解耦，
提供清晰的阶段转换和技能触发时机。
"""

from __future__ import annotations
from typing import Callable, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum, auto

if TYPE_CHECKING:
    from .engine import GameEngine
    from .player import Player


class GamePhase(Enum):
    """游戏阶段枚举"""
    PREPARE = "prepare"       # 准备阶段
    JUDGE = "judge"           # 判定阶段
    DRAW = "draw"             # 摸牌阶段
    PLAY = "play"             # 出牌阶段
    DISCARD = "discard"       # 弃牌阶段
    END = "end"               # 结束阶段


# 阶段顺序
PHASE_ORDER = [
    GamePhase.PREPARE,
    GamePhase.JUDGE,
    GamePhase.DRAW,
    GamePhase.PLAY,
    GamePhase.DISCARD,
    GamePhase.END,
]


@dataclass
class PhaseContext:
    """阶段执行上下文"""
    player: 'Player'
    phase: GamePhase
    skipped: bool = False
    extra_data: Dict = field(default_factory=dict)


class TurnManager:
    """
    回合管理器

    负责管理游戏回合的阶段流转：
    - 阶段顺序控制
    - 阶段跳过处理
    - 技能触发时机管理
    """

    def __init__(self, engine: 'GameEngine'):
        """
        初始化回合管理器

        Args:
            engine: 游戏引擎引用
        """
        self.engine = engine
        self.current_phase = GamePhase.PREPARE
        self._phase_handlers: Dict[GamePhase, Callable] = {}
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

    def run_turn(self, player: 'Player') -> None:
        """
        执行玩家的完整回合

        Args:
            player: 当前回合玩家
        """
        if not player.is_alive:
            return

        self.engine.log_event("turn_start", f"=== {player.name} 的回合 ===")
        player.reset_turn()

        # 按顺序执行各阶段
        for phase in PHASE_ORDER:
            if not player.is_alive:
                break
            self._execute_phase(player, phase)

        self.engine.log_event("turn_end", f"=== {player.name} 的回合结束 ===")

    def _execute_phase(self, player: 'Player', phase: GamePhase) -> None:
        """
        执行指定阶段

        Args:
            player: 当前回合玩家
            phase: 要执行的阶段
        """
        self.current_phase = phase
        self.engine.phase = phase

        handler = self._phase_handlers.get(phase)
        if handler:
            handler(player)

    def _execute_prepare_phase(self, player: 'Player') -> None:
        """执行准备阶段"""
        self.engine.log_event("phase", "【准备阶段】")

        # 触发准备阶段技能（如观星）
        if self.engine.skill_system and player.hero:
            for skill in player.hero.skills:
                if skill.timing and skill.timing.value == "prepare":
                    self.engine.skill_system.trigger_skill(skill.id, player, self.engine)

    def _execute_judge_phase(self, player: 'Player') -> None:
        """执行判定阶段"""
        # 委托给 engine 处理（保持兼容）
        self.engine.phase_judge(player)

    def _execute_draw_phase(self, player: 'Player') -> None:
        """执行摸牌阶段"""
        # 检查是否跳过（兵粮寸断）
        if player.skip_draw_phase:
            self.engine.log_event("phase", "【摸牌阶段】被跳过")
            player.skip_draw_phase = False
            return

        self.engine.log_event("phase", "【摸牌阶段】")

        # 基础摸牌数
        draw_count = 2

        # 英姿技能：多摸一张
        if player.has_skill("yingzi"):
            draw_count += 1
            self.engine.log_event("skill", f"{player.name} 发动【英姿】，多摸一张牌")

        # 突袭技能在摸牌阶段触发
        if player.has_skill("tuxi"):
            if self._try_trigger_tuxi(player, draw_count):
                return  # 突袭成功，跳过正常摸牌

        cards = self.engine.deck.draw(draw_count)
        player.draw_cards(cards)
        self.engine.log_event("draw_cards", f"{player.name} 摸了 {len(cards)} 张牌")

    def _try_trigger_tuxi(self, player: 'Player', draw_count: int) -> bool:
        """
        尝试触发突袭技能

        Args:
            player: 当前玩家
            draw_count: 原本要摸的牌数

        Returns:
            是否成功触发突袭
        """
        # AI 决策是否使用突袭
        if player.is_ai and player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            # 简化处理：如果有其他玩家有手牌，可能使用突袭
            targets = [
                p for p in self.engine.get_other_players(player)
                if p.hand_count > 0
            ]
            if targets and len(targets) >= draw_count:
                # 这里可以扩展为更复杂的突袭逻辑
                pass
        return False

    def _execute_play_phase(self, player: 'Player') -> None:
        """执行出牌阶段"""
        # 检查是否跳过（乐不思蜀）
        if player.skip_play_phase:
            self.engine.log_event("phase", "【出牌阶段】被跳过")
            player.skip_play_phase = False
            return

        self.engine.log_event("phase", "【出牌阶段】")

        if player.is_ai:
            self._ai_play_phase(player)
        else:
            self._human_play_phase(player)

    def _ai_play_phase(self, player: 'Player') -> None:
        """AI 出牌阶段"""
        if player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            bot.play_phase(player, self.engine)

    def _human_play_phase(self, player: 'Player') -> None:
        """人类玩家出牌阶段"""
        # 由 UI 控制
        pass

    def _execute_discard_phase(self, player: 'Player') -> None:
        """执行弃牌阶段"""
        discard_count = player.need_discard
        if discard_count > 0:
            self.engine.log_event(
                "phase",
                f"【弃牌阶段】需要弃置 {discard_count} 张牌"
            )

            if player.is_ai:
                self._ai_discard(player, discard_count)

    def _ai_discard(self, player: 'Player', count: int) -> None:
        """AI 弃牌"""
        if player.id in self.engine.ai_bots:
            bot = self.engine.ai_bots[player.id]
            cards_to_discard = bot.choose_discard(player, count, self.engine)
            self.engine.discard_cards(player, cards_to_discard)

    def _execute_end_phase(self, player: 'Player') -> None:
        """执行结束阶段"""
        # 触发结束阶段技能（如闭月）
        if player.has_skill("biyue"):
            self._trigger_biyue(player)

    def _trigger_biyue(self, player: 'Player') -> None:
        """触发闭月技能"""
        cards = self.engine.deck.draw(1)
        if cards:
            player.draw_cards(cards)
            self.engine.log_event("skill", f"{player.name} 发动【闭月】，摸了 1 张牌")

    def get_current_phase(self) -> GamePhase:
        """获取当前阶段"""
        return self.current_phase

    def skip_phase(self, phase: GamePhase, player: 'Player') -> None:
        """
        跳过指定阶段

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
    """获取阶段中文名称"""
    names = {
        GamePhase.PREPARE: "准备阶段",
        GamePhase.JUDGE: "判定阶段",
        GamePhase.DRAW: "摸牌阶段",
        GamePhase.PLAY: "出牌阶段",
        GamePhase.DISCARD: "弃牌阶段",
        GamePhase.END: "结束阶段",
    }
    return names.get(phase, "未知阶段")


def get_next_phase(current: GamePhase) -> Optional[GamePhase]:
    """获取下一个阶段"""
    try:
        idx = PHASE_ORDER.index(current)
        if idx < len(PHASE_ORDER) - 1:
            return PHASE_ORDER[idx + 1]
    except ValueError:
        pass
    return None
