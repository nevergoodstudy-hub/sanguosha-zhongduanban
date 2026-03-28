"""网络请求编解码辅助."""

from __future__ import annotations

from typing import Any

from game.actions import GameRequest, GameResponse, RequestType

from .protocol import ServerMsg


def encode_game_request(request_id: str, request: GameRequest) -> ServerMsg:
    """把领域层 GameRequest 编码为网络层 ServerMsg."""
    return ServerMsg.game_request(
        request.request_type.name.lower(),
        request.player_id,
        request.options,
        timeout=request.timeout,
        request_id=request_id,
        message=request.message,
        required=request.required,
        min_cards=request.min_cards,
        max_cards=request.max_cards,
        card_filter=request.card_filter,
        target_filter=request.target_filter,
    )


def decode_game_response(player_id: int, response_data: dict[str, Any]) -> tuple[str | None, GameResponse]:
    """把客户端响应负载解码为领域层 GameResponse."""
    request_type_raw = response_data.get("request_type", "")
    if not isinstance(request_type_raw, str) or not request_type_raw:
        raise ValueError("request_type is required")

    try:
        request_type = RequestType[request_type_raw.upper()]
    except KeyError as exc:
        raise ValueError(f"unknown request_type: {request_type_raw}") from exc

    request_id = response_data.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise ValueError("request_id must be a string")

    card_ids = response_data.get("card_ids")
    if card_ids is None:
        card_id = response_data.get("card_id")
        if card_id is None:
            normalized_card_ids: list[str] = []
        elif isinstance(card_id, str):
            normalized_card_ids = [card_id]
        else:
            raise ValueError("card_id must be a string")
    elif isinstance(card_ids, list) and all(isinstance(card_id, str) for card_id in card_ids):
        normalized_card_ids = list(card_ids)
    else:
        raise ValueError("card_ids must be a list of strings")

    target_ids = response_data.get("target_ids", [])
    if not isinstance(target_ids, list) or not all(isinstance(target_id, int) for target_id in target_ids):
        raise ValueError("target_ids must be a list of integers")

    return request_id, GameResponse(
        request_type=request_type,
        player_id=player_id,
        accepted=bool(response_data.get("accepted", False)),
        card_ids=normalized_card_ids,
        target_ids=list(target_ids),
        option=response_data.get("option"),
    )
