"""对战历史记录系统测试 (P3-3)"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from game.match_history import MatchHistory, MatchResult, PlayerStat


def _make_result(**overrides) -> MatchResult:
    """辅助：创建测试用 MatchResult。"""
    defaults = dict(
        winner="lord",
        player_count=5,
        rounds=10,
        duration_seconds=300.0,
        players=[
            PlayerStat(
                name="P1",
                hero="曹操",
                identity="lord",
                is_ai=False,
                survived=True,
                kills=2,
                damage_dealt=5,
            ),
            PlayerStat(
                name="P2",
                hero="关羽",
                identity="loyalist",
                is_ai=True,
                survived=True,
                kills=1,
                damage_dealt=3,
            ),
            PlayerStat(
                name="P3",
                hero="吕布",
                identity="rebel",
                is_ai=True,
                survived=False,
                kills=0,
                damage_dealt=2,
            ),
            PlayerStat(
                name="P4",
                hero="周瑜",
                identity="rebel",
                is_ai=True,
                survived=False,
                kills=1,
                damage_dealt=4,
            ),
            PlayerStat(
                name="P5",
                hero="貂蝉",
                identity="spy",
                is_ai=True,
                survived=False,
                kills=0,
                damage_dealt=1,
            ),
        ],
    )
    defaults.update(overrides)
    return MatchResult(**defaults)


@pytest.fixture
def tmp_path_file():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d) / "test_history.json"


class TestMatchResult:
    """MatchResult 数据类测试。"""

    def test_default_values(self):
        r = MatchResult()
        assert r.match_id == ""
        assert r.winner == ""
        assert r.player_count == 0
        assert r.players == []
        assert r.mode == "standard"

    def test_with_players(self):
        r = _make_result()
        assert r.winner == "lord"
        assert r.player_count == 5
        assert len(r.players) == 5
        assert r.players[0].hero == "曹操"


class TestMatchHistory:
    """MatchHistory 管理器测试。"""

    def test_record_assigns_id(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        mid = h.record(_make_result())
        assert mid == "match_000001"
        mid2 = h.record(_make_result(winner="rebel"))
        assert mid2 == "match_000002"

    def test_record_preserves_custom_id(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        r = _make_result()
        r.match_id = "custom_001"
        mid = h.record(r)
        assert mid == "custom_001"

    def test_get_recent(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        for i in range(5):
            h.record(_make_result(rounds=i + 1))
        recent = h.get_recent(3)
        assert len(recent) == 3
        # 最近的在前
        assert recent[0].rounds == 5
        assert recent[2].rounds == 3

    def test_get_by_id(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        mid = h.record(_make_result())
        found = h.get_by_id(mid)
        assert found is not None
        assert found.winner == "lord"
        assert h.get_by_id("nonexistent") is None

    def test_save_and_load(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        h.record(_make_result(winner="lord", rounds=10))
        h.record(_make_result(winner="rebel", rounds=8))
        h.save()

        # 重新加载
        h2 = MatchHistory(tmp_path_file)
        h2.load()
        assert len(h2.records) == 2
        assert h2.records[0].winner == "lord"
        assert h2.records[1].winner == "rebel"
        assert h2.records[0].players[0].hero == "曹操"

    def test_load_nonexistent_file(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        h.load()
        assert h.records == []

    def test_load_corrupted_file(self, tmp_path_file):
        tmp_path_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path_file.write_text("not json", encoding="utf-8")
        h = MatchHistory(tmp_path_file)
        h.load()
        assert h.records == []

    def test_clear(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        h.record(_make_result())
        h.record(_make_result())
        assert len(h.records) == 2
        h.clear()
        assert len(h.records) == 0


class TestMatchStats:
    """统计功能测试。"""

    def test_empty_stats(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        stats = h.get_stats()
        assert stats == {"total_matches": 0}

    def test_basic_stats(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        h.record(_make_result(winner="lord", rounds=10, duration_seconds=300))
        h.record(_make_result(winner="rebel", rounds=8, duration_seconds=200))
        h.record(_make_result(winner="lord", rounds=12, duration_seconds=400))

        stats = h.get_stats()
        assert stats["total_matches"] == 3
        assert stats["win_distribution"]["lord"] == 2
        assert stats["win_distribution"]["rebel"] == 1
        assert stats["avg_rounds"] == 10.0
        assert stats["avg_duration_seconds"] == 300.0

    def test_human_win_rate(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        # 人类是主公，主公赢
        h.record(_make_result(winner="lord"))
        # 人类是主公，反贼赢
        h.record(_make_result(winner="rebel"))
        stats = h.get_stats()
        assert stats["human_win_rate"] == 0.5

    def test_hero_stats(self, tmp_path_file):
        h = MatchHistory(tmp_path_file)
        h.record(_make_result(winner="lord"))
        h.record(_make_result(winner="rebel"))
        hero_stats = h.get_hero_stats()
        # 曹操 (lord) 出现 2 次，赢了 1 次
        assert hero_stats["曹操"]["total"] == 2
        assert hero_stats["曹操"]["wins"] == 1
        # 吕布 (rebel) 出现 2 次，赢了 1 次
        assert hero_stats["吕布"]["total"] == 2
        assert hero_stats["吕布"]["wins"] == 1


class TestPlayerWon:
    """_player_won 静态方法测试。"""

    def test_lord_wins(self):
        assert MatchHistory._player_won("lord", "lord") is True
        assert MatchHistory._player_won("loyalist", "lord") is True
        assert MatchHistory._player_won("rebel", "lord") is False
        assert MatchHistory._player_won("spy", "lord") is False

    def test_rebel_wins(self):
        assert MatchHistory._player_won("rebel", "rebel") is True
        assert MatchHistory._player_won("lord", "rebel") is False

    def test_spy_wins(self):
        assert MatchHistory._player_won("spy", "spy") is True
        assert MatchHistory._player_won("lord", "spy") is False

    def test_unknown_winner(self):
        assert MatchHistory._player_won("lord", "unknown") is False


class TestPersistenceRoundtrip:
    """持久化往返测试。"""

    def test_id_continuity_after_reload(self, tmp_path_file):
        """reload 后 next_id 应正确延续。"""
        h = MatchHistory(tmp_path_file)
        h.record(_make_result())
        h.record(_make_result())
        h.save()

        h2 = MatchHistory(tmp_path_file)
        h2.load()
        mid = h2.record(_make_result())
        assert mid == "match_000003"

    def test_full_roundtrip_preserves_all_fields(self, tmp_path_file):
        """所有字段在 save/load 后完整保留。"""
        h = MatchHistory(tmp_path_file)
        r = _make_result(
            winner="spy",
            rounds=20,
            duration_seconds=999.5,
            mode="network",
        )
        h.record(r)
        h.save()

        h2 = MatchHistory(tmp_path_file)
        h2.load()
        loaded = h2.records[0]
        assert loaded.winner == "spy"
        assert loaded.rounds == 20
        assert loaded.duration_seconds == 999.5
        assert loaded.mode == "network"
        assert loaded.players[0].name == "P1"
        assert loaded.players[0].damage_dealt == 5
        assert loaded.players[2].survived is False
