"""
存档系统测试 (M4-T06)
"""

import json
import os
import tempfile

import pytest

from game.engine import GameEngine
from game.save_system import (
    _MIGRATIONS,
    SAVE_VERSION,
    SCHEMA_VERSION,
    EnhancedReplay,
    apply_migrations,
    delete_save,
    list_saves,
    load_game,
    save_game,
    serialize_card,
    serialize_engine,
    serialize_player,
)


class TestSerializeCard:
    def test_serialize_basic_card(self):
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        player = engine.players[0]
        if player.hand:
            card = player.hand[0]
            data = serialize_card(card)
            assert "name" in data
            assert "suit" in data
            assert "number" in data
            assert "card_type" in data


class TestSerializePlayer:
    def test_serialize_player_fields(self):
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        player = engine.players[0]
        data = serialize_player(player)

        assert data["id"] == player.id
        assert data["name"] == player.name
        assert data["hp"] == player.hp
        assert data["max_hp"] == player.max_hp
        assert data["is_alive"] == player.is_alive
        assert data["identity"] is not None
        assert "hand" in data
        assert "equipment" in data

    def test_serialize_hand_cards(self):
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        player = engine.players[0]
        data = serialize_player(player)
        assert len(data["hand"]) == len(player.hand)


class TestSerializeEngine:
    def test_serialize_full_state(self):
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        data = serialize_engine(engine)

        assert data["save_version"] == SAVE_VERSION
        assert data["schema_version"] == SCHEMA_VERSION
        assert data["player_count"] == 4
        assert data["state"] == "in_progress"
        assert data["round_count"] >= 1
        assert len(data["players"]) == 4
        assert "saved_at" in data

    def test_serialize_is_json_safe(self):
        """序列化结果可被 JSON 编码"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        data = serialize_engine(engine)
        raw = json.dumps(data, ensure_ascii=False)
        restored = json.loads(raw)
        assert restored["player_count"] == 4

    def test_serialize_after_battle(self):
        """对局结束后也能序列化"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        engine.run_headless_battle(max_rounds=50)
        data = serialize_engine(engine)
        assert data["state"] in ("finished", "in_progress")


class TestSaveLoadFile:
    def test_save_and_load_roundtrip(self):
        """保存 → 加载 → 数据一致"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            filepath = f.name

        try:
            save_game(engine, filepath)
            data = load_game(filepath)
            assert data["save_version"] == SAVE_VERSION
            assert data["player_count"] == 4
            assert len(data["players"]) == 4
        finally:
            os.unlink(filepath)

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_game("nonexistent_save.json")

    def test_save_creates_file(self):
        engine = GameEngine()
        engine.setup_headless_game(2, seed=42)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            filepath = f.name

        try:
            result = save_game(engine, filepath)
            assert os.path.exists(result)
            assert result == filepath
        finally:
            os.unlink(filepath)


class TestListAndDeleteSaves:
    def test_list_saves_empty_dir(self):
        saves = list_saves("nonexistent_dir_12345")
        assert saves == []

    def test_delete_save(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("{}")
            filepath = f.name

        assert os.path.exists(filepath)
        result = delete_save(filepath)
        assert result is True
        assert not os.path.exists(filepath)

    def test_delete_nonexistent(self):
        result = delete_save("no_such_file_xyz.json")
        assert result is False


class TestEnhancedReplay:
    def _make_replay(self, steps: int = 5) -> EnhancedReplay:
        actions = [{"step": i, "action": f"act_{i}"} for i in range(steps)]
        save_data = {
            "action_log": actions,
            "player_count": 4,
            "round_count": 10,
            "game_seed": 42,
        }
        return EnhancedReplay(save_data)

    def test_init(self):
        replay = self._make_replay(5)
        assert replay.total_steps == 5
        assert replay.current_step == 0
        assert replay.speed == 1.0

    def test_step_forward(self):
        replay = self._make_replay(3)
        action = replay.step_forward()
        assert action["step"] == 0
        assert replay.current_step == 1

        action = replay.step_forward()
        assert action["step"] == 1

    def test_step_forward_past_end(self):
        replay = self._make_replay(1)
        replay.step_forward()
        action = replay.step_forward()
        assert action is None

    def test_step_back(self):
        replay = self._make_replay(5)
        replay.step_forward()
        replay.step_forward()
        assert replay.current_step == 2

        result = replay.step_back()
        assert result is True
        assert replay.current_step == 1

    def test_step_back_at_start(self):
        replay = self._make_replay(5)
        result = replay.step_back()
        assert result is False

    def test_jump_to(self):
        replay = self._make_replay(10)
        assert replay.jump_to(5) is True
        assert replay.current_step == 5
        assert replay.jump_to(0) is True
        assert replay.jump_to(-1) is False
        assert replay.jump_to(11) is False

    def test_reset(self):
        replay = self._make_replay(5)
        replay.step_forward()
        replay.step_forward()
        replay.reset()
        assert replay.current_step == 0

    def test_progress(self):
        replay = self._make_replay(10)
        assert replay.progress == 0.0
        replay.jump_to(5)
        assert replay.progress == 0.5
        replay.jump_to(10)
        assert replay.progress == 1.0

    def test_progress_empty(self):
        replay = EnhancedReplay({"action_log": []})
        assert replay.progress == 1.0

    def test_speed(self):
        replay = self._make_replay()
        replay.set_speed(2.0)
        assert replay.speed == 2.0
        assert replay.delay == 0.25

        replay.set_speed(0.1)  # clamped to 0.25
        assert replay.speed == 0.25

        replay.set_speed(10.0)  # clamped to 4.0
        assert replay.speed == 4.0

    def test_current_action(self):
        replay = self._make_replay(3)
        assert replay.current_action["step"] == 0
        replay.step_forward()
        assert replay.current_action["step"] == 1

    def test_get_summary(self):
        replay = self._make_replay(5)
        summary = replay.get_summary()
        assert summary["total_steps"] == 5
        assert summary["player_count"] == 4
        assert summary["seed"] == 42


class TestSchemaMigrations:
    """存档 schema 迁移链测试"""

    def test_v1_to_v2_adds_missing_fields(self):
        """v1 存档 (无 schema_version) 应被迁移到 v2"""
        v1_data = {
            "save_version": "1.0.0",
            "players": [
                {"id": 1, "name": "P1", "hp": 4},
                {"id": 2, "name": "P2", "hp": 3},
            ],
        }
        result = apply_migrations(v1_data)
        assert result["schema_version"] == SCHEMA_VERSION
        for p in result["players"]:
            assert p["judge_area"] == []
            assert p["is_chained"] is False
            assert p["is_flipped"] is False

    def test_v2_data_unchanged(self):
        """已经是 v2 的存档不应被修改"""
        v2_data = {
            "schema_version": 2,
            "players": [{"id": 1, "judge_area": [{"name": "闪电"}]}],
        }
        result = apply_migrations(v2_data)
        assert result["schema_version"] == 2
        assert result["players"][0]["judge_area"] == [{"name": "闪电"}]

    def test_future_schema_raises(self):
        """高于当前版本的 schema 应报错"""
        future_data = {"schema_version": 999}
        with pytest.raises(ValueError, match="高于当前"):
            apply_migrations(future_data)

    def test_migration_preserves_existing_fields(self):
        """v1 存档中已有的 judge_area 不应被覆盖"""
        v1_data = {
            "players": [
                {"id": 1, "judge_area": [{"name": "乐不思蜀"}], "is_chained": True},
            ],
        }
        result = apply_migrations(v1_data)
        assert result["players"][0]["judge_area"] == [{"name": "乐不思蜀"}]
        assert result["players"][0]["is_chained"] is True
        assert result["players"][0]["is_flipped"] is False

    def test_migration_registry_has_v1_to_v2(self):
        """迁移注册表应包含 v1→v2 路径"""
        assert 1 in _MIGRATIONS
        target, fn = _MIGRATIONS[1]
        assert target == 2
        assert callable(fn)

    def test_load_game_applies_migration(self):
        """load_game() 应自动应用迁移"""
        v1_data = {
            "save_version": "1.0.0",
            "players": [{"id": 1, "name": "P1", "hp": 4}],
        }
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        ) as f:
            json.dump(v1_data, f)
            filepath = f.name

        try:
            data = load_game(filepath)
            assert data["schema_version"] == SCHEMA_VERSION
            assert data["players"][0]["judge_area"] == []
        finally:
            os.unlink(filepath)
