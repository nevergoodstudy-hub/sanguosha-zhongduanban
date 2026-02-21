"""游戏阶段与状态枚举 — 从 engine.py 提取以消除循环导入

将 GamePhase / GameState 独立出来后，turn_manager.py 等子模块可以
直接导入本模块，不再需要 ``from .engine import GamePhase`` 造成
engine → turn_manager → engine 的间接循环依赖。
"""

from enum import Enum


class GamePhase(Enum):
    """游戏阶段枚举"""

    PREPARE = "prepare"  # 准备阶段
    JUDGE = "judge"  # 判定阶段
    DRAW = "draw"  # 摸牌阶段
    PLAY = "play"  # 出牌阶段
    DISCARD = "discard"  # 弃牌阶段
    END = "end"  # 结束阶段


class GameState(Enum):
    """游戏状态枚举"""

    NOT_STARTED = "not_started"  # 未开始
    CHOOSING_HEROES = "choosing_heroes"  # 选将阶段
    IN_PROGRESS = "in_progress"  # 进行中
    FINISHED = "finished"  # 已结束
