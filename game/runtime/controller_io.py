"""Controller-facing runtime I/O boundary."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from game.engine import GameEngine
    from game.player import Player
    from ui.protocol import GameUI


class ControllerIO:
    """Async-friendly adapter around the synchronous ``GameUI`` protocol."""

    def __init__(self, ui: GameUI, prompt: Callable[[str], str] | None = None) -> None:
        self._ui = ui
        self._prompt = prompt or input

    async def _run(self, func: Callable[..., Any], *args: Any) -> Any:
        return await asyncio.to_thread(func, *args)

    async def show_main_menu(self) -> int:
        return await self._run(self._ui.show_main_menu)

    async def show_rules(self) -> None:
        await self._run(self._ui.show_rules)

    async def show_player_count_menu(self) -> int:
        return await self._run(self._ui.show_player_count_menu)

    async def show_difficulty_menu(self) -> str:
        return await self._run(self._ui.show_difficulty_menu)

    async def show_game_state(self, engine: GameEngine, current_player: Player) -> None:
        await self._run(self._ui.show_game_state, engine, current_player)

    async def show_log(self, message: str) -> None:
        await self._run(self._ui.show_log, message)

    async def show_help(self) -> None:
        await self._run(self._ui.show_help)

    async def get_player_action(self) -> str:
        return await self._run(self._ui.get_player_action)

    async def prompt_text(self, prompt: str) -> str:
        return (await self._run(self._prompt, prompt)).strip()

    def choose_target(self, player: Player, targets: list[Player], prompt: str) -> Player | None:
        return self._ui.choose_target(player, targets, prompt)

    def show_skill_menu(self, player: Player, usable_skills: list[str]) -> str | None:
        return self._ui.show_skill_menu(player, usable_skills)

    def choose_card_to_play(self, player: Player):
        return self._ui.choose_card_to_play(player)

    async def choose_cards_to_discard(self, player: Player, count: int):
        return await self._run(self._ui.choose_cards_to_discard, player, count)
