"""Startup and hero-selection coordination helpers extracted from ``GameController``."""

from __future__ import annotations

import copy
import random
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from ..player import Identity, Player

if TYPE_CHECKING:
    from ai.bot import AIDifficulty

    from ..engine import GameEngine
    from ..hero import Hero
    from .controller_io import ControllerIO

HeroPicker = Callable[[Player, list["Hero"]], "Hero"]
AiChooser = Callable[[list[str]], Awaitable[dict[int, str]]]


class StartupCoordinator:
    """Own startup, hero-selection, and AI-bot setup orchestration."""

    def __init__(
        self,
        *,
        engine_getter: Callable[[], GameEngine | None],
        controller_io_getter: Callable[[], ControllerIO],
        ai_difficulty_getter: Callable[[], AIDifficulty],
    ) -> None:
        self._engine_getter = engine_getter
        self._controller_io_getter = controller_io_getter
        self._ai_difficulty_getter = ai_difficulty_getter

    @property
    def engine(self) -> GameEngine | None:
        return self._engine_getter()

    @property
    def controller_io(self) -> ControllerIO:
        return self._controller_io_getter()

    @property
    def ai_difficulty(self) -> AIDifficulty:
        return self._ai_difficulty_getter()

    async def choose_heroes(self, *, auto_choose_heroes_for_ai: AiChooser) -> None:
        """Handle human hero selection, then fill remaining AI picks."""
        engine = self.engine
        if not engine:
            return

        all_heroes = engine.hero_repo.get_all_heroes()
        used_heroes: list[str] = []

        lord_heroes = [
            hero for hero in all_heroes if any(skill.is_lord_skill for skill in hero.skills)
        ]
        normal_heroes = [
            hero for hero in all_heroes if not any(skill.is_lord_skill for skill in hero.skills)
        ]

        human_player = engine.human_player
        if human_player:
            is_lord = human_player.identity == Identity.LORD

            if is_lord:
                await self.controller_io.show_log(_t("controller.lord_choose_hero"))
                available = lord_heroes.copy()
                remaining = 5 - len(available)
                if remaining > 0:
                    extra = random.sample(normal_heroes, min(remaining, len(normal_heroes)))
                    available.extend(extra)
                random.shuffle(available)
                available = available[:5]
            else:
                await self.controller_io.show_log(_t("controller.choose_hero"))
                available = random.sample(normal_heroes, min(3, len(normal_heroes)))

            selected = await self.controller_io.show_hero_selection(available, 1, is_lord)
            if selected:
                hero = copy.deepcopy(selected[0])
                human_player.set_hero(hero)
                used_heroes.append(hero.id)

                if is_lord:
                    await self.controller_io.show_log(
                        _t("controller.hero_chosen", player=human_player.name, hero=hero.name)
                    )

        ai_choices = await auto_choose_heroes_for_ai(used_heroes)
        engine.choose_heroes(ai_choices)

    async def auto_choose_heroes_for_ai(
        self,
        used_heroes: list[str],
        *,
        select_hero_for_ai: HeroPicker,
    ) -> dict[int, str]:
        """Choose distinct heroes for AI players and emit controller-facing logs."""
        engine = self.engine
        if not engine:
            return {}

        all_heroes = engine.hero_repo.get_all_heroes()
        available = [hero for hero in all_heroes if hero.id not in used_heroes]

        ai_choices: dict[int, str] = {}
        for player in engine.players:
            if player.is_ai and player.hero is None and available:
                hero = select_hero_for_ai(player, available)
                ai_choices[player.id] = hero.id
                available.remove(hero)
                await self.controller_io.show_log(
                    _t("controller.hero_chosen", player=player.name, hero=hero.name)
                )

        return ai_choices

    def select_hero_for_ai(self, player: Player, available: list[Hero]) -> Hero:
        """Apply the existing identity-based heuristics for AI hero selection."""
        from game.hero import SkillType

        preferred: list[Hero] = []
        if player.identity == Identity.LORD:
            preferred = [
                hero for hero in available if any(skill.is_lord_skill for skill in hero.skills)
            ]
        elif player.identity == Identity.LOYALIST:
            preferred = [hero for hero in available if hero.max_hp >= 4]
        elif player.identity == Identity.REBEL:
            preferred = [
                hero
                for hero in available
                if any(skill.skill_type == SkillType.ACTIVE for skill in hero.skills)
            ]
        elif player.identity == Identity.SPY:
            preferred = [hero for hero in available if hero.max_hp >= 4 or len(hero.skills) >= 2]

        if preferred:
            return random.choice(preferred)
        return random.choice(available)

    def setup_ai_bots(self) -> None:
        """Instantiate AI bot objects for every AI-controlled player."""
        engine = self.engine
        if not engine:
            return

        from ai.bot import AIBot

        for player in engine.players:
            if player.is_ai:
                engine.ai_bots[player.id] = AIBot(player, self.ai_difficulty)
