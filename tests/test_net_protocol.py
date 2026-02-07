# -*- coding: utf-8 -*-
"""
网络协议测试 (M4-T01)
"""

import json
import pytest
from net.protocol import (
    MsgType, RoomState, ServerMsg, ClientMsg,
    parse_message, validate_msg_type,
)


class TestMsgType:
    """消息类型枚举测试"""

    def test_all_types_have_string_values(self):
        for t in MsgType:
            assert isinstance(t.value, str)

    def test_room_types(self):
        assert MsgType.ROOM_CREATE.value == "room_create"
        assert MsgType.ROOM_JOIN.value == "room_join"
        assert MsgType.ROOM_START.value == "room_start"

    def test_game_types(self):
        assert MsgType.GAME_STATE.value == "game_state"
        assert MsgType.GAME_EVENT.value == "game_event"
        assert MsgType.GAME_ACTION.value == "game_action"
        assert MsgType.GAME_RESPONSE.value == "game_response"

    def test_room_state(self):
        assert RoomState.WAITING.value == "waiting"
        assert RoomState.PLAYING.value == "playing"


class TestServerMsg:
    """服务端消息测试"""

    def test_roundtrip_json(self):
        """序列化 → 反序列化 保持一致"""
        msg = ServerMsg(type=MsgType.GAME_EVENT, data={"hp": 3}, seq=42)
        raw = msg.to_json()
        restored = ServerMsg.from_json(raw)
        assert restored.type == MsgType.GAME_EVENT
        assert restored.data["hp"] == 3
        assert restored.seq == 42

    def test_error_factory(self):
        msg = ServerMsg.error("房间已满", code=403)
        assert msg.type == MsgType.ERROR
        assert msg.data["message"] == "房间已满"
        assert msg.data["code"] == 403

    def test_heartbeat_ack(self):
        msg = ServerMsg.heartbeat_ack()
        assert msg.type == MsgType.HEARTBEAT_ACK

    def test_room_created_factory(self):
        msg = ServerMsg.room_created("room-1", {"max_players": 4})
        assert msg.type == MsgType.ROOM_CREATED
        assert msg.data["room_id"] == "room-1"
        assert msg.data["max_players"] == 4

    def test_room_joined_factory(self):
        msg = ServerMsg.room_joined("room-1", 1, "玩家A", [{"id": 1, "name": "玩家A"}])
        d = msg.data
        assert d["room_id"] == "room-1"
        assert d["player_id"] == 1
        assert len(d["players"]) == 1

    def test_room_update_factory(self):
        msg = ServerMsg.room_update("room-1", [], RoomState.WAITING)
        assert msg.data["state"] == "waiting"

    def test_room_listing_factory(self):
        msg = ServerMsg.room_listing([{"id": "r1", "players": 2}])
        assert len(msg.data["rooms"]) == 1

    def test_game_state_factory(self):
        msg = ServerMsg.game_state({"round": 1, "players": []})
        assert msg.type == MsgType.GAME_STATE
        assert msg.data["round"] == 1

    def test_game_event_factory(self):
        msg = ServerMsg.game_event("damage", {"source": "A", "target": "B", "amount": 1}, seq=10)
        assert msg.type == MsgType.GAME_EVENT
        assert msg.seq == 10
        assert msg.data["event_type"] == "damage"

    def test_game_request_factory(self):
        msg = ServerMsg.game_request("play_shan", 1, {"card_name": "闪"}, timeout=15.0)
        assert msg.data["request_type"] == "play_shan"
        assert msg.data["player_id"] == 1
        assert msg.data["timeout"] == 15.0

    def test_game_over_factory(self):
        msg = ServerMsg.game_over("rebel", "主公阵亡", {"rounds": 5})
        assert msg.data["winner"] == "rebel"
        assert msg.data["stats"]["rounds"] == 5

    def test_hero_options_factory(self):
        heroes = [{"id": "caocao", "name": "曹操"}]
        msg = ServerMsg.hero_options(1, heroes)
        assert msg.data["player_id"] == 1
        assert msg.data["heroes"][0]["id"] == "caocao"

    def test_chat_broadcast_factory(self):
        msg = ServerMsg.chat_broadcast("玩家A", "你好")
        assert msg.data["player_name"] == "玩家A"
        assert msg.data["message"] == "你好"

    def test_json_contains_type_field(self):
        msg = ServerMsg.error("test")
        obj = json.loads(msg.to_json())
        assert "type" in obj
        assert obj["type"] == "error"


class TestClientMsg:
    """客户端消息测试"""

    def test_roundtrip_json(self):
        msg = ClientMsg(type=MsgType.GAME_ACTION, player_id=1, data={"action": "play_card"})
        raw = msg.to_json()
        restored = ClientMsg.from_json(raw)
        assert restored.type == MsgType.GAME_ACTION
        assert restored.player_id == 1
        assert restored.data["action"] == "play_card"

    def test_heartbeat(self):
        msg = ClientMsg.heartbeat(5)
        assert msg.type == MsgType.HEARTBEAT
        assert msg.player_id == 5

    def test_room_create(self):
        msg = ClientMsg.room_create(1, "玩家A", max_players=6, ai_fill=False)
        assert msg.data["player_name"] == "玩家A"
        assert msg.data["max_players"] == 6
        assert msg.data["ai_fill"] is False

    def test_room_join(self):
        msg = ClientMsg.room_join(2, "玩家B", "room-1")
        assert msg.data["room_id"] == "room-1"

    def test_room_leave(self):
        msg = ClientMsg.room_leave(1)
        assert msg.type == MsgType.ROOM_LEAVE

    def test_room_list(self):
        msg = ClientMsg.room_list()
        assert msg.type == MsgType.ROOM_LIST

    def test_room_ready(self):
        msg = ClientMsg.room_ready(1, ready=True)
        assert msg.data["ready"] is True

    def test_room_start(self):
        msg = ClientMsg.room_start(1)
        assert msg.type == MsgType.ROOM_START

    def test_game_action(self):
        msg = ClientMsg.game_action(1, "play_card", {"card_id": 42, "target_ids": [2]})
        assert msg.data["action_type"] == "play_card"
        assert msg.data["card_id"] == 42

    def test_game_response(self):
        msg = ClientMsg.game_response(1, "play_shan", accepted=True, response_data={"card_id": 7})
        assert msg.data["request_type"] == "play_shan"
        assert msg.data["accepted"] is True
        assert msg.data["card_id"] == 7

    def test_hero_chosen(self):
        msg = ClientMsg.hero_chosen(1, "liubei")
        assert msg.data["hero_id"] == "liubei"

    def test_chat(self):
        msg = ClientMsg.chat(1, "冲啊")
        assert msg.data["message"] == "冲啊"


class TestUtilFunctions:
    """工具函数测试"""

    def test_parse_message(self):
        raw = json.dumps({"type": "heartbeat", "player_id": 0})
        type_str, obj = parse_message(raw)
        assert type_str == "heartbeat"
        assert obj["player_id"] == 0

    def test_validate_msg_type_valid(self):
        assert validate_msg_type("heartbeat") is True
        assert validate_msg_type("game_event") is True
        assert validate_msg_type("room_create") is True

    def test_validate_msg_type_invalid(self):
        assert validate_msg_type("invalid_type") is False
        assert validate_msg_type("") is False

    def test_cross_serialization(self):
        """客户端消息 JSON 可被服务端解析 (type 字段一致)"""
        client_msg = ClientMsg.game_action(1, "play_card")
        raw = client_msg.to_json()
        obj = json.loads(raw)
        assert validate_msg_type(obj["type"])
