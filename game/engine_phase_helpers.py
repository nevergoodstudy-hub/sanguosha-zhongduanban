"""GameEngine 阶段执行辅助函数."""

from __future__ import annotations

from typing import Any

from .enums import GamePhase


def _run_phase(engine: Any, player: Any, phase: GamePhase, turn_manager_method: str) -> None:
    """统一执行阶段：设置 phase 并委托 TurnManager 对应方法."""
    engine.phase = phase
    getattr(engine.turn_manager, turn_manager_method)(player)


def phase_prepare(engine: Any, player: Any) -> None:
    _run_phase(engine, player, GamePhase.PREPARE, "_execute_prepare_phase")


def phase_judge(engine: Any, player: Any) -> None:
    _run_phase(engine, player, GamePhase.JUDGE, "_execute_judge_phase")


def phase_draw(engine: Any, player: Any) -> None:
    _run_phase(engine, player, GamePhase.DRAW, "_execute_draw_phase")


def phase_play(engine: Any, player: Any) -> None:
    _run_phase(engine, player, GamePhase.PLAY, "_execute_play_phase")


def phase_discard(engine: Any, player: Any) -> None:
    _run_phase(engine, player, GamePhase.DISCARD, "_execute_discard_phase")


def phase_end(engine: Any, player: Any) -> None:
    _run_phase(engine, player, GamePhase.END, "_execute_end_phase")
