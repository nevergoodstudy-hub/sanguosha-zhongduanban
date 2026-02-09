"""
Pydantic 网络消息校验模型测试 (Phase 3.3)
"""

import json

import pytest
from pydantic import ValidationError

from net.models import (
    ChatData,
    ClientMsgModel,
    GameActionData,
    RoomCreateData,
    RoomJoinData,
    validate_client_message,
)


class TestClientMsgModel:
    """外层消息结构校验"""

    def test_valid_heartbeat(self):
        msg = ClientMsgModel(type="heartbeat", player_id=1)
        assert msg.type == "heartbeat"
        assert msg.player_id == 1

    def test_empty_type_rejected(self):
        with pytest.raises(ValidationError):
            ClientMsgModel(type="", player_id=1)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            ClientMsgModel(type="heartbeat", player_id=1, hack="inject")

    def test_missing_type_rejected(self):
        with pytest.raises(ValidationError):
            ClientMsgModel(player_id=1)


class TestRoomCreateData:
    def test_valid(self):
        data = RoomCreateData(player_name="张飞", max_players=5)
        assert data.player_name == "张飞"
        assert data.max_players == 5

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            RoomCreateData(player_name="")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            RoomCreateData(player_name="a" * 21)

    def test_max_players_bounds(self):
        with pytest.raises(ValidationError):
            RoomCreateData(player_name="ok", max_players=1)  # < 2
        with pytest.raises(ValidationError):
            RoomCreateData(player_name="ok", max_players=9)  # > 8


class TestRoomJoinData:
    def test_valid(self):
        data = RoomJoinData(player_name="关羽", room_id="abc123")
        assert data.room_id == "abc123"

    def test_empty_room_id_rejected(self):
        with pytest.raises(ValidationError):
            RoomJoinData(player_name="关羽", room_id="")


class TestGameActionData:
    def test_valid(self):
        data = GameActionData(action_type="play_card", card_id=42)
        assert data.action_type == "play_card"

    def test_empty_action_type_rejected(self):
        with pytest.raises(ValidationError):
            GameActionData(action_type="")


class TestChatData:
    def test_valid(self):
        data = ChatData(message="大家好")
        assert data.message == "大家好"

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            ChatData(message="")

    def test_message_too_long(self):
        with pytest.raises(ValidationError):
            ChatData(message="x" * 501)


class TestValidateClientMessage:
    """端到端 JSON 校验"""

    def test_valid_heartbeat(self):
        raw = json.dumps({"type": "heartbeat", "player_id": 1, "data": {}})
        msg = validate_client_message(raw)
        assert msg.type == "heartbeat"

    def test_valid_room_create(self):
        raw = json.dumps({
            "type": "room_create",
            "player_id": 1,
            "data": {"player_name": "曹操", "max_players": 4},
        })
        msg = validate_client_message(raw)
        assert msg.type == "room_create"

    def test_invalid_json_rejected(self):
        with pytest.raises(ValidationError):
            validate_client_message("{not valid json")

    def test_room_create_bad_data_rejected(self):
        raw = json.dumps({
            "type": "room_create",
            "player_id": 1,
            "data": {"player_name": "", "max_players": 100},
        })
        with pytest.raises(ValidationError):
            validate_client_message(raw)

    def test_chat_message_validation(self):
        raw = json.dumps({
            "type": "chat",
            "player_id": 1,
            "data": {"message": ""},
        })
        with pytest.raises(ValidationError):
            validate_client_message(raw)

    def test_hero_chosen_validation(self):
        raw = json.dumps({
            "type": "hero_chosen",
            "player_id": 1,
            "data": {"hero_id": "liubei"},
        })
        msg = validate_client_message(raw)
        assert msg.type == "hero_chosen"
