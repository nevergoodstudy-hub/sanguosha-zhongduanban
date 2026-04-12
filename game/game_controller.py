"""Top-level local game controller facade."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from i18n import t as _t

from .card import Card
from .engine import GameEngine
from .player import Player
from .runtime import (
    ControllerIO,
    PlayPhaseCoordinator,
    SessionCoordinator,
    StartupCoordinator,
    TurnCoordinator,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ai.bot import AIDifficulty
    from ui.protocol import GameUI

    from .hero import Hero


class GameController:
    """Coordinate the local game flow through extracted runtime helpers."""

    def __init__(self, ui: GameUI, ai_difficulty: AIDifficulty | None = None) -> None:
        from ai.bot import AIDifficulty

        self.ui = ui
        self.engine: GameEngine | None = None
        self.ai_difficulty: AIDifficulty = ai_difficulty or AIDifficulty.NORMAL
        self.is_running = True

        self._controller_io = ControllerIO(ui)
        self._play_phase = PlayPhaseCoordinator(
            engine_getter=lambda: self.engine,
            controller_io_getter=lambda: self._controller_io,
        )
        self._turns = TurnCoordinator(
            engine_getter=lambda: self.engine,
            controller_io_getter=lambda: self._controller_io,
        )
        self._startup = StartupCoordinator(
            engine_getter=lambda: self.engine,
            controller_io_getter=lambda: self._controller_io,
            ai_difficulty_getter=lambda: self.ai_difficulty,
        )
        self._session = SessionCoordinator(
            engine_getter=lambda: self.engine,
            engine_setter=lambda engine: setattr(self, "engine", engine),
            controller_io_getter=lambda: self._controller_io,
            ui_getter=lambda: self.ui,
            ai_difficulty_setter=lambda difficulty: setattr(self, "ai_difficulty", difficulty),
        )

    async def run(self) -> None:
        """Run the main menu loop until the user exits."""
        while self.is_running:
            choice = await self._controller_io.show_main_menu()

            if choice == 1:
                await self.start_new_game()
            elif choice == 2:
                await self._controller_io.show_rules()
            elif choice == 3:
                self.is_running = False
                await self._controller_io.show_log(_t("controller.thanks"))
                logger.info("User exited game via main menu")

    async def start_new_game(self) -> None:
        """Start a new game session through the extracted session coordinator."""
        return await self._session.start_new_game(
            choose_heroes=self._choose_heroes,
            setup_ai_bots=self._setup_ai_bots,
            game_loop=self._game_loop,
        )

    async def _game_loop(self) -> None:
        """Run the active game session loop through the session coordinator."""
        return await self._session.game_loop(
            run_ai_turn=self._run_ai_turn,
            run_human_turn=self._run_human_turn,
            handle_game_over=self._handle_game_over,
        )

    async def _show_turn_header(self, player: Player) -> None:
        """Display the round banner through the async controller boundary."""
        engine = self.engine
        if not engine:
            return

        border = "─" * 12
        await self._controller_io.show_log("")
        await self._controller_io.show_log(border)
        await self._controller_io.show_log(
            _t(
                "controller.round_header",
                round=engine.round_count,
                player=player.name,
                hero=player.hero.name,
            )
        )
        await self._controller_io.show_log(border)

    async def _execute_prepare_phase(self, player: Player) -> None:
        """Delegate prepare-phase execution to the turn coordinator."""
        await self._turns.execute_prepare_phase(player)

    async def _execute_draw_phase(self, player: Player, show_count: bool = True) -> int:
        """Delegate draw-phase execution to the turn coordinator."""
        return await self._turns.execute_draw_phase(player, show_count)

    async def _execute_discard_phase(self, player: Player) -> None:
        """Delegate discard-phase execution to the turn coordinator."""
        await self._turns.execute_discard_phase(
            player,
            human_discard_phase=self._human_discard_phase,
        )

    async def _execute_end_phase(self, player: Player) -> None:
        """Delegate end-phase execution to the turn coordinator."""
        await self._turns.execute_end_phase(player)

    async def _run_ai_turn(self, player: Player) -> None:
        """Keep the AI turn hook monkeypatchable at controller level."""
        await self._turns.run_ai_turn(
            player,
            show_turn_header=self._show_turn_header,
            execute_prepare_phase=self._execute_prepare_phase,
            execute_draw_phase=self._execute_draw_phase,
            execute_discard_phase=self._execute_discard_phase,
            execute_end_phase=self._execute_end_phase,
        )

    async def _run_human_turn(self, player: Player) -> None:
        """Keep the human turn hook monkeypatchable at controller level."""
        await self._turns.run_human_turn(
            player,
            show_turn_header=self._show_turn_header,
            execute_prepare_phase=self._execute_prepare_phase,
            execute_draw_phase=self._execute_draw_phase,
            human_play_phase=self._human_play_phase,
            execute_discard_phase=self._execute_discard_phase,
            execute_end_phase=self._execute_end_phase,
        )

    async def _choose_heroes(self) -> None:
        """Route hero selection through the startup coordinator wrapper."""
        await self._startup.choose_heroes(
            auto_choose_heroes_for_ai=self._auto_choose_heroes_for_ai,
        )

    async def _auto_choose_heroes_for_ai(self, used_heroes: list[str]) -> dict[int, str]:
        """Keep AI hero selection monkeypatchable at controller level."""
        return await self._startup.auto_choose_heroes_for_ai(
            used_heroes,
            select_hero_for_ai=self._select_hero_for_ai,
        )

    def _select_hero_for_ai(self, player: Player, available: list[Hero]) -> Hero:
        """Delegate AI hero heuristics to the startup coordinator."""
        return self._startup.select_hero_for_ai(player, available)

    def _setup_ai_bots(self) -> None:
        """Delegate AI bot construction to the startup coordinator."""
        self._startup.setup_ai_bots()

    async def _human_play_phase(self, player: Player) -> None:
        """Keep the human play phase monkeypatchable at controller level."""
        await self._play_phase.human_play_phase(
            player,
            confirm_quit=self._confirm_quit,
            update_playable_mask=self._update_playable_mask,
            can_do_anything=self._can_do_anything,
            handle_use_skill=self._handle_use_skill,
            handle_play_specific_card=self._handle_play_specific_card,
        )

    def _check_card_usable(self, player: Player, card: Card) -> bool:
        """Check whether a card is currently legal to play."""
        return self._play_phase.check_card_usable(player, card)

    def get_playable_mask(self, player: Player) -> list[bool]:
        """Return the current hand-card playability mask."""
        return self._play_phase.get_playable_mask(player)

    def _update_playable_mask(self, player: Player) -> None:
        """Refresh the engine-visible playable mask."""
        self._play_phase.update_playable_mask(player)

    def _has_usable_cards(self, player: Player) -> bool:
        """Return whether the player can still play any card."""
        return self._play_phase.has_usable_cards(player)

    def _has_usable_skills(self, player: Player) -> bool:
        """Return whether the player can still activate any skill."""
        return self._play_phase.has_usable_skills(player)

    def _can_do_anything(self, player: Player) -> bool:
        """Return whether the player can continue acting this phase."""
        return self._play_phase.can_do_anything(player)

    async def _handle_play_specific_card(self, player: Player, card: Card) -> None:
        """Delegate card-play handling to the play-phase coordinator."""
        await self._play_phase.handle_play_specific_card(player, card)

    async def _handle_use_skill(self, player: Player) -> None:
        """Delegate skill handling to the play-phase coordinator."""
        await self._play_phase.handle_use_skill(
            player,
            select_cards_for_skill=self._select_cards_for_skill,
        )

    async def _select_cards_for_skill(
        self, player: Player, min_count: int, max_count: int
    ) -> list[Card]:
        """Delegate skill-card selection to the play-phase coordinator."""
        return await self._play_phase.select_cards_for_skill(player, min_count, max_count)

    async def _human_discard_phase(self, player: Player) -> None:
        """Keep human discard monkeypatchable at controller level."""
        return await self._session.human_discard_phase(player)

    async def _handle_game_over(self) -> None:
        """Keep game-over handling monkeypatchable at controller level."""
        return await self._session.handle_game_over()

    async def _confirm_quit(self) -> bool:
        """Keep quit confirmation monkeypatchable at controller level."""
        return await self._session.confirm_quit()
