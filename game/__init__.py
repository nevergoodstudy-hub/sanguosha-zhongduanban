# -*- coding: utf-8 -*-
"""
三国杀游戏核心模块
包含游戏引擎、玩家、卡牌、武将和技能系统
"""

from .card import Card, CardType, CardSuit, Deck
from .hero import Hero, Skill, Kingdom
from .player import Player, Identity
from .engine import GameEngine
from .skill import SkillSystem

__all__ = [
    'Card', 'CardType', 'CardSuit', 'Deck',
    'Hero', 'Skill', 'Kingdom',
    'Player', 'Identity',
    'GameEngine',
    'SkillSystem'
]

__version__ = '1.0.0'
__author__ = 'Sanguosha Dev Team'
