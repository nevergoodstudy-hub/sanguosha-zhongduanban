"""AI模块
提供游戏AI逻辑

Phase 4.1: 策略模式重构 — 按难度拆分为 EasyStrategy / NormalStrategy / HardStrategy
"""

from .bot import AIBot, AIDifficulty
from .easy_strategy import EasyStrategy
from .hard_strategy import HardStrategy, IdentityPredictor, ThreatEvaluator
from .normal_strategy import NormalStrategy
from .strategy import AIStrategy

__all__ = [
    'AIBot', 'AIDifficulty', 'AIStrategy',
    'EasyStrategy', 'NormalStrategy', 'HardStrategy',
    'ThreatEvaluator', 'IdentityPredictor',
]
