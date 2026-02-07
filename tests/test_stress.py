# -*- coding: utf-8 -*-
"""
压力测试 (M4-T04)
批量运行随机对局，验证引擎稳定性

默认运行 100 局 (CI 环境), 可通过 STRESS_COUNT 环境变量设为 1000
"""

import os
import random
import pytest
from game.engine import GameEngine, GameState


STRESS_COUNT = int(os.environ.get("STRESS_COUNT", "100"))


class TestStressBattle:
    """批量随机对局压力测试"""

    def _run_one(self, seed: int, player_count: int,
                 difficulty: str = "normal") -> dict:
        """运行单场对局，返回结果 dict"""
        engine = GameEngine()
        engine.setup_headless_game(player_count, ai_difficulty=difficulty, seed=seed)
        return engine.run_headless_battle(max_rounds=100)

    def test_stress_100_battles(self):
        """
        运行 STRESS_COUNT 局随机对局，错误率 < 5%
        """
        errors = 0
        timeouts = 0
        rng = random.Random(2026)

        for i in range(STRESS_COUNT):
            seed = rng.randint(0, 2**31)
            pc = rng.choice([2, 3, 4])
            diff = rng.choice(["easy", "normal", "hard"])
            try:
                result = self._run_one(seed, pc, diff)
                if result.get("timeout"):
                    timeouts += 1
            except Exception:
                errors += 1

        error_rate = errors / STRESS_COUNT
        assert error_rate < 0.05, (
            f"{STRESS_COUNT} 局中 {errors} 局出错 (错误率 {error_rate:.1%})"
        )

    def test_stress_all_player_counts(self):
        """2-4人各跑 20 局"""
        rng = random.Random(9999)
        for pc in [2, 3, 4]:
            errors = 0
            for _ in range(20):
                seed = rng.randint(0, 2**31)
                try:
                    self._run_one(seed, pc)
                except Exception:
                    errors += 1
            assert errors <= 1, f"{pc}人局 20 局中 {errors} 局出错"

    def test_stress_hard_difficulty(self):
        """困难 AI 50 局"""
        rng = random.Random(7777)
        errors = 0
        for _ in range(50):
            seed = rng.randint(0, 2**31)
            pc = rng.choice([3, 4])
            try:
                self._run_one(seed, pc, "hard")
            except Exception:
                errors += 1
        assert errors <= 2, f"困难 AI 50 局中 {errors} 局出错"
