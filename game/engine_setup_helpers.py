"""GameEngine 对局初始化辅助函数.

抽离 setup/identity/start 前置校验逻辑，降低 engine.py 复杂度。
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from .constants import IdentityConfig
from .enums import GameState
from .player import Identity, Player

if TYPE_CHECKING:
    from i18n import t as _t  # noqa: F401


def setup_game(
    engine: Any,
    player_count: int,
    human_player_index: int = 0,
    role_preference: str = "lord",
) -> None:
    """设置游戏（行为与原实现保持一致）."""
    if player_count < 2 or player_count > 8:
        from i18n import t as _t

        raise ValueError(_t("error.player_count"))

    engine._role_preference = role_preference

    # 创建玩家
    engine.players.clear()
    engine.human_player = None
    for i in range(player_count):
        is_human = i == human_player_index and human_player_index >= 0
        from i18n import t as _t

        player = Player(
            id=i,
            name=_t("game.player_name", index=i + 1) if is_human else f"AI_{i + 1}",
            is_ai=not is_human,
            seat=i,
            game_engine=engine,
        )
        engine.players.append(player)
        if is_human:
            engine.human_player = player

    # 分配身份
    assign_identities(engine)

    # 重置牌堆
    engine.deck.reset()

    engine.state = GameState.CHOOSING_HEROES
    from i18n import t as _t

    engine.log_event("game_setup", _t("game.setup_complete", count=player_count))


def assign_identities(engine: Any) -> None:
    """分配身份（支持2-8人）- 使用 IdentityConfig (SSOT)."""
    player_count = len(engine.players)

    config = IdentityConfig.get_config(player_count)
    identities = (
        [Identity.LORD] * config.get("lord", 1)
        + [Identity.LOYALIST] * config.get("loyalist", 0)
        + [Identity.REBEL] * config.get("rebel", 1)
        + [Identity.SPY] * config.get("spy", 0)
    )

    role_pref = getattr(engine, "_role_preference", "lord")

    if role_pref == "random":
        random.shuffle(identities)
        for i, player in enumerate(engine.players):
            player.identity = identities[i]
    else:
        engine.players[0].identity = identities[0]
        remaining_identities = identities[1:]
        random.shuffle(remaining_identities)
        for i, player in enumerate(engine.players[1:], 1):
            if i - 1 < len(remaining_identities):
                player.identity = remaining_identities[i - 1]


def ensure_can_start_game(engine: Any) -> None:
    """开始游戏前置校验."""
    from i18n import t as _t

    if engine.state != GameState.CHOOSING_HEROES:
        raise RuntimeError(_t("error.game_state_start"))

    for player in engine.players:
        if player.hero is None:
            raise RuntimeError(_t("error.no_hero", player=player.name))
