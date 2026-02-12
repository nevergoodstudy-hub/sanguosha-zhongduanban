"""三国杀游戏核心模块
包含游戏引擎、玩家、卡牌、武将、技能系统、事件系统和动作系统

重构版本 v1.1.0:
- 新增事件总线系统 (events.py) 实现模块解耦
- 新增动作/请求系统 (actions.py) 实现 UI/逻辑分离
"""

from .actions import (
    ActionExecutor,
    ActionType,
    ActionValidator,
    DiscardAction,
    EndPhaseAction,
    GameAction,
    GameRequest,
    GameResponse,
    PlayCardAction,
    RequestType,
    RespondAction,
    UseSkillAction,
)
from .card import Card, CardSubtype, CardSuit, CardType, DamageType, Deck
from .engine import GameEngine, GamePhase, GameState
from .events import EventBus, EventEmitter, EventType, GameEvent
from .hero import Hero, Kingdom, Skill
from .player import Identity, Player
from .skill import SkillSystem

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

try:
    from importlib.metadata import version as _get_version
    __version__ = _get_version("sanguosha")
except Exception:
    __version__ = "3.0.0"  # fallback, keep in sync with pyproject.toml
__author__ = "Sanguosha Dev Team"
