"""Phase 4 enhancement tests (P3-1, P3-3, P3-4)."""

import gzip
import json
import tempfile
from pathlib import Path

import pytest

from ai.decision_log import AIDecision, AIDecisionLogger
from tools.profiling import report_metrics, reset_metrics, timed

# ==================== P3-1: AI Decision Logger ====================


class TestAIDecisionLogger:
    def test_log_enabled(self):
        dl = AIDecisionLogger(enabled=True)
        dl.log(AIDecision(player_id=0, action="use_sha", score=0.9))
        assert len(dl.history) == 1

    def test_log_disabled(self):
        dl = AIDecisionLogger(enabled=False)
        dl.log(AIDecision(player_id=0, action="use_sha"))
        assert len(dl.history) == 0

    def test_toggle_enabled(self):
        dl = AIDecisionLogger(enabled=False)
        dl.log(AIDecision(action="skip"))
        dl.enabled = True
        dl.log(AIDecision(action="use_sha"))
        assert len(dl.history) == 1

    def test_clear(self):
        dl = AIDecisionLogger()
        dl.log(AIDecision(action="a"))
        dl.log(AIDecision(action="b"))
        dl.clear()
        assert len(dl.history) == 0

    def test_export_json(self, tmp_path):
        dl = AIDecisionLogger()
        dl.log(AIDecision(player_id=1, action="use_sha", score=0.8, reason="threat"))
        dl.log(AIDecision(player_id=2, action="use_tao", score=0.6))

        out = tmp_path / "decisions.json"
        dl.export_json(out)

        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data[0]["action"] == "use_sha"
        assert data[1]["player_id"] == 2

    def test_summary_empty(self):
        dl = AIDecisionLogger()
        s = dl.summary()
        assert s["total"] == 0

    def test_summary_with_data(self):
        dl = AIDecisionLogger()
        dl.log(AIDecision(action="use_sha", ai_tier="hard", score=0.9))
        dl.log(AIDecision(action="use_sha", ai_tier="hard", score=0.7))
        dl.log(AIDecision(action="skip", ai_tier="easy", score=0.1))
        s = dl.summary()
        assert s["total"] == 3
        assert s["actions"]["use_sha"] == 2
        assert s["tiers"]["hard"] == 2
        assert pytest.approx(s["avg_score"], rel=0.01) == (0.9 + 0.7 + 0.1) / 3


# ==================== P3-4: Profiling ====================


class TestProfiling:
    def setup_method(self):
        reset_metrics()

    def test_timed_decorator(self):
        @timed
        def sample():
            return 42

        result = sample()
        assert result == 42
        report = report_metrics()
        key = [k for k in report if "sample" in k][0]
        assert report[key]["calls"] == 1
        assert report[key]["total_ms"] >= 0

    def test_timed_multiple_calls(self):
        @timed
        def add(a, b):
            return a + b

        add(1, 2)
        add(3, 4)
        add(5, 6)
        report = report_metrics()
        key = [k for k in report if "add" in k][0]
        assert report[key]["calls"] == 3

    def test_reset_metrics(self):
        @timed
        def noop():
            pass

        noop()
        assert len(report_metrics()) > 0
        reset_metrics()
        assert len(report_metrics()) == 0

    def test_report_structure(self):
        @timed
        def calc():
            return sum(range(100))

        calc()
        report = report_metrics()
        key = list(report.keys())[0]
        assert "calls" in report[key]
        assert "total_ms" in report[key]
        assert "avg_ms" in report[key]
        assert "max_ms" in report[key]


# ==================== P3-3: Replay System ====================


class TestReplaySystem:
    def test_replay_recorder_and_player(self):
        from game.replay import ReplayEvent, ReplayPlayer, ReplayRecorder

        recorder = ReplayRecorder()
        recorder.start({"player_count": 2, "seed": 42})

        recorder.record(
            ReplayEvent(
                turn=1,
                phase="play",
                actor="AI_1",
                action="use_sha",
                targets=["AI_2"],
                cards=["sha_spade_7"],
                result="hit",
            )
        )
        recorder.record(
            ReplayEvent(
                turn=1,
                phase="discard",
                actor="AI_1",
                action="discard",
                targets=[],
                cards=["shan_diamond_2"],
                result="ok",
            )
        )

        # Save and reload
        with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as f:
            path = f.name
        recorder.save(path)

        player = ReplayPlayer(path)
        assert player.metadata["seed"] == 42
        assert len(player.events) == 2

        e1 = player.next_event()
        assert e1["action"] == "use_sha"
        e2 = player.next_event()
        assert e2["action"] == "discard"
        assert player.next_event() is None

        player.reset()
        assert player.next_event()["turn"] == 1

        Path(path).unlink(missing_ok=True)

    def test_empty_recorder(self):
        from game.replay import ReplayRecorder

        recorder = ReplayRecorder()
        recorder.start({"player_count": 4})

        with tempfile.NamedTemporaryFile(suffix=".json.gz", delete=False) as f:
            path = f.name
        recorder.save(path)

        data = json.loads(gzip.open(path, "rt", encoding="utf-8").read())
        assert data["events"] == []
        Path(path).unlink(missing_ok=True)
