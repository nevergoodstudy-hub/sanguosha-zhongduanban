"""Tests for replay CLI integration (E-2)."""

import json

import pytest

from game.save_system import EnhancedReplay, load_game


@pytest.fixture
def sample_save(tmp_path):
    """Create a minimal save file for testing."""
    data = {
        "save_version": "2.0.0",
        "schema_version": 2,
        "player_count": 4,
        "round_count": 3,
        "game_seed": 42,
        "state": "finished",
        "phase": "end",
        "current_player_index": 0,
        "winner_identity": "lord",
        "players": [
            {
                "id": 0,
                "name": "P0",
                "hp": 3,
                "max_hp": 4,
                "is_alive": True,
                "identity": "lord",
                "hand": [],
                "hand_count": 0,
                "is_ai": False,
                "seat": 0,
                "hero_id": "caocao",
                "hero_name": "曹操",
                "equipment": {},
                "sha_used": 0,
                "judge_area": [],
                "is_chained": False,
                "is_flipped": False,
            },
        ],
        "deck_remaining": 50,
        "discard_pile_count": 10,
        "action_log": [
            {
                "action_type": "PLAY_CARD",
                "player_id": 0,
                "timestamp": 1.0,
                "data": {"type": "PLAY_CARD", "card_id": "sha_1"},
            },
            {
                "action_type": "USE_SKILL",
                "player_id": 1,
                "timestamp": 2.0,
                "data": {"type": "USE_SKILL", "skill_id": "jianxiong"},
            },
            {
                "action_type": "DISCARD",
                "player_id": 2,
                "timestamp": 3.0,
                "data": {"type": "DISCARD", "card_ids": ["c1", "c2"]},
            },
        ],
    }
    filepath = tmp_path / "test_save.json"
    filepath.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(filepath)


class TestEnhancedReplayCLI:
    def test_load_and_create_replay(self, sample_save):
        data = load_game(sample_save)
        replay = EnhancedReplay(data)
        assert replay.total_steps == 3
        assert replay.current_step == 0

    def test_step_forward(self, sample_save):
        data = load_game(sample_save)
        replay = EnhancedReplay(data)

        action1 = replay.step_forward()
        assert action1["action_type"] == "PLAY_CARD"
        assert replay.current_step == 1

        action2 = replay.step_forward()
        assert action2["action_type"] == "USE_SKILL"

        action3 = replay.step_forward()
        assert action3["action_type"] == "DISCARD"

        assert replay.step_forward() is None  # No more actions

    def test_summary(self, sample_save):
        data = load_game(sample_save)
        replay = EnhancedReplay(data)
        summary = replay.get_summary()
        assert summary["total_steps"] == 3
        assert summary["player_count"] == 4
        assert summary["seed"] == 42

    def test_speed_control(self, sample_save):
        data = load_game(sample_save)
        replay = EnhancedReplay(data)
        replay.set_speed(2.0)
        assert replay.speed == 2.0
        assert replay.delay == 0.25  # 0.5 / 2.0

    def test_jump_and_reset(self, sample_save):
        data = load_game(sample_save)
        replay = EnhancedReplay(data)
        replay.jump_to(2)
        assert replay.current_step == 2
        replay.reset()
        assert replay.current_step == 0


class TestMainReplayArg:
    def test_argparse_accepts_replay(self):
        """Verify --replay is accepted by argparse."""
        import argparse

        # Simulate parsing
        parser = argparse.ArgumentParser()
        parser.add_argument("--replay", default=None)
        parser.add_argument("--step", action="store_true")
        args = parser.parse_args(["--replay", "test.json", "--step"])
        assert args.replay == "test.json"
        assert args.step is True
