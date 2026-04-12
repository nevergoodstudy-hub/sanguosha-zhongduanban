"""网络动作编解码.

将客户端的松散 JSON payload 转换为领域层 `GameAction`。
"""

from __future__ import annotations

from typing import Any

from game.actions import DiscardAction, EndPhaseAction, GameAction, PlayCardAction, UseSkillAction


def _require_non_empty_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_int_list(value: Any, field_name: str) -> list[int]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        raise ValueError(f"{field_name} must be a list of integers")
    return value


def _require_str_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{field_name} must be a list of non-empty strings")
    return value


def _read_common_metadata(action_data: dict[str, Any]) -> dict[str, Any]:
    source_channel = action_data.get("source_channel", "network")
    if not isinstance(source_channel, str) or not source_channel.strip():
        source_channel = "network"

    correlation_id = action_data.get("correlation_id")
    if correlation_id is not None and (
        not isinstance(correlation_id, str) or not correlation_id.strip()
    ):
        correlation_id = None

    action_id = action_data.get("action_id")
    if action_id is not None and (not isinstance(action_id, str) or not action_id.strip()):
        action_id = None

    metadata: dict[str, Any] = {
        "source_channel": source_channel,
        "correlation_id": correlation_id,
    }
    if action_id:
        metadata["action_id"] = action_id
    return metadata


def decode_client_action(player_id: int, action_data: dict[str, Any]) -> GameAction:
    """将网络动作 payload 转为领域动作."""
    action_type = _require_non_empty_str(action_data.get("action_type"), "action_type")
    metadata = _read_common_metadata(action_data)

    extra_payload = action_data.get("extra_payload", {})
    if not isinstance(extra_payload, dict):
        raise ValueError("extra_payload must be a dict")

    if action_type == "play_card":
        return PlayCardAction(
            player_id=player_id,
            card_id=_require_non_empty_str(action_data.get("card_id"), "card_id"),
            target_ids=_require_int_list(action_data.get("target_ids", []), "target_ids"),
            **metadata,
        )

    if action_type == "use_skill":
        return UseSkillAction(
            player_id=player_id,
            skill_id=_require_non_empty_str(action_data.get("skill_id"), "skill_id"),
            target_ids=_require_int_list(action_data.get("target_ids", []), "target_ids"),
            card_ids=_require_str_list(action_data.get("card_ids", []), "card_ids"),
            extra_payload=extra_payload,
            **metadata,
        )

    if action_type == "discard":
        return DiscardAction(
            player_id=player_id,
            card_ids=_require_str_list(action_data.get("card_ids", []), "card_ids"),
            **metadata,
        )

    if action_type == "end_turn":
        return EndPhaseAction(player_id=player_id, **metadata)

    raise ValueError(f"unsupported action_type: {action_type}")
