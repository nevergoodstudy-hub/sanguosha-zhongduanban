"""Turn and phase coordination helpers extracted from ``GameController``."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from i18n import t as _t

from ..config import get_config
from ..engine import GameEngine, GamePhase

if TYPE_CHECKING:
    from ..player import Player
    from .controller_io import ControllerIO

PlayerAsyncStep = Callable[["Player"], Awaitable[None]]
DrawPhaseStep = Callable[["Player"], Awaitable[int]]


class TurnCoordinator:
    """Own turn/phase orchestration while the controller stays a stable facade."""

    def __init__(
        self,
        *,
        engine_getter: Callable[[], GameEngine | None],
        controller_io_getter: Callable[[], ControllerIO],
    ) -> None:
        self._engine_getter = engine_getter
        self._controller_io_getter = controller_io_getter

    @property
    def engine(self) -> GameEngine | None:
        return self._engine_getter()

    @property
    def controller_io(self) -> ControllerIO:
        return self._controller_io_getter()

    async def execute_prepare_phase(self, player: Player) -> None:
        """Run the prepare phase and surface logging through the async IO boundary."""
        engine = self.engine
        if not engine:
            return

        await self.controller_io.show_log(_t("controller.phase_prepare"))
        engine.phase_prepare(player)

    async def execute_draw_phase(self, player: Player, show_count: bool = True) -> int:
        """Run the draw phase and report how many cards were drawn."""
        engine = self.engine
        if not engine:
            return 0

        controller_io = self.controller_io
        await controller_io.show_log(_t("controller.phase_draw"))
        old_count = player.hand_count
        engine.phase_draw(player)
        new_cards = player.hand_count - old_count

        if show_count:
            if player.is_ai:
                await controller_io.show_log(
                    _t("controller.drew_cards_ai", player=player.name, count=new_cards)
                )
            else:
                await controller_io.show_log(
                    _t(
                        "controller.drew_cards_human",
                        count=new_cards,
                        hand_count=player.hand_count,
                    )
                )

        return new_cards

    async def execute_discard_phase(
        self,
        player: Player,
        *,
        human_discard_phase: PlayerAsyncStep,
    ) -> None:
        """Route discard handling while delegating the human branch back to the controller."""
        engine = self.engine
        if not engine or player.need_discard <= 0:
            return

        controller_io = self.controller_io
        await controller_io.show_log(_t("controller.phase_discard"))

        if player.is_ai:
            await controller_io.show_log(_t("controller.need_discard", count=player.need_discard))
            engine.phase_discard(player)
            return

        await controller_io.show_log(
            _t("controller.need_discard_limit", count=player.need_discard, limit=player.hp)
        )
        engine.phase = GamePhase.DISCARD
        await controller_io.show_game_state(engine, player)
        await human_discard_phase(player)

    async def execute_end_phase(self, player: Player) -> None:
        """Run the end phase and emit the same controller-facing log messages."""
        engine = self.engine
        if not engine:
            return

        controller_io = self.controller_io
        await controller_io.show_log(_t("controller.phase_end"))
        engine.phase_end(player)
        turn_end_msg = (
            _t("controller.turn_end_ai", player=player.name)
            if player.is_ai
            else _t("controller.turn_end_human")
        )
        await controller_io.show_log(turn_end_msg)

    async def run_ai_turn(
        self,
        player: Player,
        *,
        show_turn_header: PlayerAsyncStep,
        execute_prepare_phase: PlayerAsyncStep,
        execute_draw_phase: DrawPhaseStep,
        execute_discard_phase: PlayerAsyncStep,
        execute_end_phase: PlayerAsyncStep,
    ) -> None:
        """Drive the AI turn sequence while keeping controller hook points patchable."""
        engine = self.engine
        if not engine:
            return

        controller_io = self.controller_io

        await show_turn_header(player)
        await controller_io.show_game_state(engine, player)

        player.reset_turn()

        await execute_prepare_phase(player)
        await execute_draw_phase(player)
        await controller_io.show_game_state(engine, player)

        cfg = get_config()
        if cfg.ai_turn_delay > 0:
            await asyncio.sleep(cfg.ai_turn_delay)

        await controller_io.show_log(_t("controller.phase_play"))
        engine.phase = GamePhase.PLAY
        if player.id in engine.ai_bots:
            engine.ai_bots[player.id].play_phase(player, engine)
        await controller_io.show_game_state(engine, player)

        if cfg.ai_turn_delay > 0:
            await asyncio.sleep(cfg.ai_turn_delay)

        await execute_discard_phase(player)
        await execute_end_phase(player)

        if cfg.ai_turn_delay > 0:
            await asyncio.sleep(cfg.ai_turn_delay)

    async def run_human_turn(
        self,
        player: Player,
        *,
        show_turn_header: PlayerAsyncStep,
        execute_prepare_phase: PlayerAsyncStep,
        execute_draw_phase: DrawPhaseStep,
        human_play_phase: PlayerAsyncStep,
        execute_discard_phase: PlayerAsyncStep,
        execute_end_phase: PlayerAsyncStep,
    ) -> None:
        """Drive the human turn sequence while preserving controller wrapper seams."""
        engine = self.engine
        if not engine:
            return

        controller_io = self.controller_io

        await show_turn_header(player)
        player.reset_turn()

        await execute_prepare_phase(player)
        await controller_io.show_game_state(engine, player)

        await execute_draw_phase(player)
        await controller_io.show_game_state(engine, player)

        await controller_io.show_log(_t("controller.phase_play"))
        engine.phase = GamePhase.PLAY
        await human_play_phase(player)

        await execute_discard_phase(player)
        await execute_end_phase(player)
