"""Session lifecycle helpers extracted from ``GameController``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from ..engine import GameEngine
from ..player import Identity, Player
from ..skill import SkillSystem

if TYPE_CHECKING:
    from ai.bot import AIDifficulty
    from ui.protocol import GameUI

    from .controller_io import ControllerIO

PlayerAsyncStep = Callable[[Player], Awaitable[None]]
AsyncNoArgStep = Callable[[], Awaitable[None]]


class SessionCoordinator:
    """Own startup/session lifecycle orchestration while controller wrappers stay stable."""

    def __init__(
        self,
        *,
        engine_getter: Callable[[], GameEngine | None],
        engine_setter: Callable[[GameEngine | None], None],
        controller_io_getter: Callable[[], ControllerIO],
        ui_getter: Callable[[], GameUI],
        ai_difficulty_setter: Callable[[AIDifficulty], None],
    ) -> None:
        self._engine_getter = engine_getter
        self._engine_setter = engine_setter
        self._controller_io_getter = controller_io_getter
        self._ui_getter = ui_getter
        self._ai_difficulty_setter = ai_difficulty_setter

    @property
    def engine(self) -> GameEngine | None:
        return self._engine_getter()

    @property
    def controller_io(self) -> ControllerIO:
        return self._controller_io_getter()

    @property
    def ui(self) -> GameUI:
        return self._ui_getter()

    async def start_new_game(
        self,
        *,
        choose_heroes: AsyncNoArgStep,
        setup_ai_bots: Callable[[], None],
        game_loop: AsyncNoArgStep,
    ) -> None:
        """Create and initialize a new session, then hand off to the controller loop wrapper."""
        player_count = await self.controller_io.show_player_count_menu()
        difficulty_str = await self.controller_io.show_difficulty_menu()

        from ai.bot import AIDifficulty

        self._ai_difficulty_setter(AIDifficulty(difficulty_str))

        engine = GameEngine()
        engine.setup_game(player_count, human_player_index=0)

        ui = self.ui
        engine.set_ui(ui)
        ui.set_engine(engine)

        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        self._engine_setter(engine)

        await choose_heroes()
        setup_ai_bots()
        engine.start_game()
        await game_loop()

    async def game_loop(
        self,
        *,
        run_ai_turn: PlayerAsyncStep,
        run_human_turn: PlayerAsyncStep,
        handle_game_over: AsyncNoArgStep,
    ) -> None:
        """Run the outer session loop while delegating turn execution back through controller seams."""
        engine = self.engine
        if not engine:
            return

        while not engine.is_game_over():
            current_player = engine.current_player
            await self.controller_io.show_game_state(engine, current_player)

            if current_player.is_ai:
                await run_ai_turn(current_player)
            else:
                await run_human_turn(current_player)

            if engine.is_game_over():
                break

            engine.next_turn()

        await handle_game_over()

    async def human_discard_phase(self, player: Player) -> None:
        """Handle the controller-managed human discard interaction."""
        engine = self.engine
        if not engine:
            return

        discard_count = player.need_discard
        if discard_count <= 0:
            return

        controller_io = self.controller_io
        await controller_io.show_log(_t("controller.need_discard_cards", count=discard_count))
        cards = await controller_io.choose_cards_to_discard(player, discard_count)

        if cards:
            engine.discard_cards(player, cards)

    async def handle_game_over(self) -> None:
        """Compute the victory flag and forward the result to the async IO boundary."""
        engine = self.engine
        if not engine:
            return

        winner_message = engine.get_winner_message()

        is_victory = False
        if engine.human_player:
            human_identity = engine.human_player.identity
            if engine.winner_identity == Identity.LORD:
                is_victory = human_identity in [Identity.LORD, Identity.LOYALIST]
            elif engine.winner_identity == Identity.REBEL:
                is_victory = human_identity == Identity.REBEL
            elif engine.winner_identity == Identity.SPY:
                is_victory = human_identity == Identity.SPY

        await self.controller_io.show_game_over(winner_message, is_victory)

    async def confirm_quit(self) -> bool:
        """Confirm whether the player wants to exit the play phase."""
        choice = (await self.controller_io.prompt_text(_t("controller.confirm_quit"))).upper()
        return choice == "Y"
