"""GameEngine 回合推进辅助函数."""

from __future__ import annotations

from typing import Any

from .events import EventType


def next_turn(engine: Any) -> None:
    """进入下一个玩家回合（行为与原实现保持一致）."""
    previous_index = engine.current_player_index

    # 找到下一个存活的玩家
    for i in range(1, len(engine.players) + 1):
        next_index = (engine.current_player_index + i) % len(engine.players)
        if engine.players[next_index].is_alive:
            engine.current_player_index = next_index
            break

    # 如果回到主公，回合数+1
    if (
        engine.current_player_index == engine.lord_player_index
        and previous_index != engine.lord_player_index
    ):
        engine.event_bus.emit(
            EventType.ROUND_END,
            round=engine.round_count,
            player=engine.players[previous_index],
        )
        engine.round_count += 1
        for player in engine.players:
            player.reset_round()
        engine.event_bus.emit(
            EventType.ROUND_START,
            round=engine.round_count,
            player=engine.current_player,
        )
