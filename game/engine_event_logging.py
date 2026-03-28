"""GameEngine 事件与日志辅助函数.

将 engine.py 内的日志发布与卡牌获得/失去通知逻辑抽离，
降低主 Facade 文件复杂度并保持行为不变。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from .events import EventType

if TYPE_CHECKING:
    from .card import Card
    from .player import Player

logger = logging.getLogger(__name__)


def log_event(
    engine: Any,
    event_type: str,
    message: str,
    source: Player | None = None,
    target: Player | None = None,
    card: Card | None = None,
    **extra_data,
) -> None:
    """记录游戏事件并通过事件总线发布."""
    # 同步写入 Python 日志（便于排查运行问题）
    try:
        level = logging.INFO
        et = (event_type or "").lower()
        if et in {"error", "exception"}:
            level = logging.ERROR
        elif et in {"warn", "warning"}:
            level = logging.WARNING

        src_name = source.name if source else None
        tgt_name = target.name if target else None
        card_name = card.display_name if card else None
        logger.log(
            level,
            "[%s] %s | src=%s tgt=%s card=%s",
            event_type,
            message,
            src_name,
            tgt_name,
            card_name,
        )
    except Exception:
        # 日志系统不应影响游戏流程
        pass

    # 发布语义化事件（替代统一的 LOG_MESSAGE）
    semantic_type = engine._log_category_map.get(event_type, EventType.LOG_MESSAGE)
    engine.event_bus.emit(
        semantic_type,
        message=message,
        log_type=event_type,
        source=source,
        target=target,
        card=card,
        **extra_data,
    )

    # 同时发布 LOG_MESSAGE 供 UI 订阅者消费
    if semantic_type != EventType.LOG_MESSAGE:
        engine.event_bus.emit(
            EventType.LOG_MESSAGE,
            message=message,
            log_type=event_type,
        )


def notify_cards_obtained(
    engine: Any,
    player: Player,
    cards: list[Card],
    *,
    source: Player | None = None,
    from_player: Player | None = None,
    reason: str = "",
) -> None:
    """发布获得牌语义事件."""
    if not cards:
        return
    engine.event_bus.emit(
        EventType.CARD_OBTAINED,
        player=player,
        target=player,
        source=source,
        from_player=from_player,
        cards=list(cards),
        reason=reason,
    )


def notify_cards_lost(
    engine: Any,
    player: Player,
    cards: list[Card],
    *,
    source: Player | None = None,
    to_player: Player | None = None,
    reason: str = "",
) -> None:
    """发布失去牌语义事件."""
    if not cards:
        return
    engine.event_bus.emit(
        EventType.CARD_LOST,
        player=player,
        target=player,
        source=source,
        to_player=to_player,
        cards=list(cards),
        reason=reason,
    )
