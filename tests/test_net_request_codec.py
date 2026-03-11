"""请求编解码测试."""

import pytest

from game.actions import GameRequest, RequestType
from net.protocol import MsgType
from net.request_codec import decode_game_response, encode_game_request


class TestEncodeGameRequest:
    def test_encode_game_request_includes_bridge_metadata(self):
        request = GameRequest(
            request_type=RequestType.PLAY_SHAN,
            player_id=3,
            message="请选择一张闪",
            options={"cards": [{"id": "shan_heart_2"}]},
            timeout=12.0,
            required=False,
        )

        msg = encode_game_request("req-123", request)

        assert msg.type == MsgType.GAME_REQUEST
        assert msg.data["request_id"] == "req-123"
        assert msg.data["request_type"] == "play_shan"
        assert msg.data["message"] == "请选择一张闪"
        assert msg.data["options"]["cards"][0]["id"] == "shan_heart_2"


class TestDecodeGameResponse:
    def test_decode_game_response_normalizes_single_card_id(self):
        request_id, response = decode_game_response(
            3,
            {
                "request_id": "req-123",
                "request_type": "play_shan",
                "accepted": True,
                "card_id": "shan_heart_2",
            },
        )

        assert request_id == "req-123"
        assert response.request_type == RequestType.PLAY_SHAN
        assert response.player_id == 3
        assert response.accepted is True
        assert response.card_ids == ["shan_heart_2"]

    def test_decode_game_response_rejects_non_string_card_ids(self):
        with pytest.raises(ValueError):
            decode_game_response(
                3,
                {
                    "request_type": "discard",
                    "accepted": True,
                    "card_ids": ["sha_spade_A", 123],
                },
            )

    def test_decode_game_response_preserves_option_payload(self):
        request_id, response = decode_game_response(
            3,
            {
                "request_id": "req-guanxing",
                "request_type": "guanxing",
                "accepted": True,
                "card_ids": ["sha_spade_A", "shan_heart_2"],
                "option": ["tao_club_3"],
            },
        )

        assert request_id == "req-guanxing"
        assert response.request_type == RequestType.GUANXING
        assert response.card_ids == ["sha_spade_A", "shan_heart_2"]
        assert response.option == ["tao_club_3"]
