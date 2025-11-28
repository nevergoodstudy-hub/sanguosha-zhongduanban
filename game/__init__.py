# -*- coding: utf-8 -*-
"""
三国杀游戏核心模块
包含游戏引擎、玩家、卡牌、武将、技能系统、事件系统和动作系统

重构版本 v1.1.0:
- 新增事件总线系统 (events.py) 实现模块解耦
- 新增动作/请求系统 (actions.py) 实现 UI/逻辑分离
"""

from .card import Card, CardType, CardSubtype, CardSuit, Deck, DamageType
from .hero import Hero, Skill, Kingdom
from .player import Player, Identity
from .engine import GameEngine, GamePhase, GameState
from .skill import SkillSystem
from .events import EventBus, EventType, GameEvent, EventEmitter
from .actions import (
    GameAction, PlayCardAction, UseSkillAction, DiscardAction,
    RespondAction, EndPhaseAction, GameRequest, GameResponse,
    ActionType, RequestType, ActionValidator, ActionExecutor
)

__all__ = [
    # 卡牌系统
    'Card', 'CardType', 'CardSubtype', 'CardSuit', 'Deck', 'DamageType',
    # 武将系统
    'Hero', 'Skill', 'Kingdom',
    # 玩家系统
    'Player', 'Identity',
    # 游戏引擎
    'GameEngine', 'GamePhase', 'GameState',
    # 技能系统
    'SkillSystem',
    # 事件系统
    'EventBus', 'EventType', 'GameEvent', 'EventEmitter',
    # 动作系统
    'GameAction', 'PlayCardAction', 'UseSkillAction', 'DiscardAction',
    'RespondAction', 'EndPhaseAction', 'GameRequest', 'GameResponse',
    'ActionType', 'RequestType', 'ActionValidator', 'ActionExecutor'
]

__version__ = '1.1.0'
__author__ = 'Sanguosha Dev Team'
