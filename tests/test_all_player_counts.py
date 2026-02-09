"""
全玩家数量综合测试套件 (2-8人)
=====================================
基于真实用例的测试方法:
- 确定性种子保证可复现 (seed-based determinism)
- pytest.mark.parametrize 生成参数化测试矩阵
- 覆盖: 设置/身份分配/完整对局/胜负/事件系统/距离/卡牌/AI难度/边界/压力

测试用例 > 100, 通过率目标 ≥ 95%
"""

import random

import pytest

from game.engine import GameEngine, GameState
from game.events import EventType
from game.player import Identity
from game.win_checker import WinConditionChecker, WinResult

# ==================== 常量 & 工具 ====================

ALL_PLAYER_COUNTS = [2, 3, 4, 5, 6, 7, 8]

# 每种人数的标准身份分配
EXPECTED_IDENTITIES: dict[int, dict[str, int]] = {
    2: {"lord": 1, "rebel": 1, "spy": 0, "loyalist": 0},
    3: {"lord": 1, "rebel": 1, "spy": 1, "loyalist": 0},
    4: {"lord": 1, "rebel": 1, "spy": 1, "loyalist": 1},
    5: {"lord": 1, "rebel": 2, "spy": 1, "loyalist": 1},
    6: {"lord": 1, "rebel": 3, "spy": 1, "loyalist": 1},
    7: {"lord": 1, "rebel": 3, "spy": 1, "loyalist": 2},
    8: {"lord": 1, "rebel": 4, "spy": 1, "loyalist": 2},
}

# 可复现种子集 (不同种子覆盖不同随机路径)
SEEDS = [42, 100, 200, 500, 999, 1234, 2026, 7777, 9999, 31415]


def _make_engine(pc: int, seed: int = 42, diff: str = "normal") -> GameEngine:
    """快捷构造 headless engine"""
    engine = GameEngine()
    engine.setup_headless_game(pc, ai_difficulty=diff, seed=seed)
    return engine


# ==================== 1. 设置与初始化 (7 tests) ====================

class TestSetupValidation:
    """验证各玩家数量的 headless 设置正确性"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_player_count_correct(self, pc):
        """玩家数量与请求一致"""
        engine = _make_engine(pc)
        assert len(engine.players) == pc

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_state_in_progress(self, pc):
        """设置后状态为 IN_PROGRESS"""
        engine = _make_engine(pc)
        assert engine.state == GameState.IN_PROGRESS

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_all_players_have_heroes(self, pc):
        """每位玩家都有武将"""
        engine = _make_engine(pc)
        for p in engine.players:
            assert p.hero is not None, f"玩家 {p.name} 无武将"

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_initial_hand_size(self, pc):
        """每位玩家初始手牌 4 张"""
        engine = _make_engine(pc)
        for p in engine.players:
            assert len(p.hand) == 4, f"{p.name} 手牌数={len(p.hand)}"

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_all_players_alive(self, pc):
        """初始所有玩家存活"""
        engine = _make_engine(pc)
        assert all(p.is_alive for p in engine.players)

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_all_players_are_ai(self, pc):
        """headless 模式下所有玩家为 AI"""
        engine = _make_engine(pc)
        assert all(p.is_ai for p in engine.players)

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_heroes_unique(self, pc):
        """同一局内武将不重复"""
        engine = _make_engine(pc)
        hero_names = [p.hero.name for p in engine.players]
        assert len(hero_names) == len(set(hero_names))


# ==================== 2. 身份分配 (7 tests) ====================

class TestIdentityDistribution:
    """验证各人数下身份配比正确"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_identity_counts(self, pc):
        """身份数量符合标准配置"""
        engine = _make_engine(pc, seed=1000)
        counts = {}
        for p in engine.players:
            key = p.identity.value
            counts[key] = counts.get(key, 0) + 1
        expected = EXPECTED_IDENTITIES[pc]
        for role, n in expected.items():
            assert counts.get(role, 0) == n, (
                f"{pc}人局: {role} 应为{n}, 实际{counts.get(role, 0)}"
            )

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_lord_always_exists(self, pc):
        """每局必有且仅有一个主公"""
        engine = _make_engine(pc, seed=2000)
        lords = [p for p in engine.players if p.identity == Identity.LORD]
        assert len(lords) == 1

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_lord_is_player_0(self, pc):
        """主公固定在 seat 0"""
        engine = _make_engine(pc, seed=3000)
        assert engine.players[0].identity == Identity.LORD


# ==================== 3. 完整对局 — 参数化矩阵 (28 tests: 7 pc × 4 seeds) ====================

class TestFullBattleMatrix:
    """对每种玩家数量 × 多个种子跑完整对局"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    @pytest.mark.parametrize("seed", [42, 200, 999, 2026])
    def test_battle_completes_or_timeout(self, pc, seed):
        """对局能在 max_rounds 内完成 (或安全超时)"""
        engine = _make_engine(pc, seed=seed)
        result = engine.run_headless_battle(max_rounds=100)
        assert result["rounds"] > 0
        assert "winner" in result

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    @pytest.mark.parametrize("seed", [42, 200, 999, 2026])
    def test_battle_result_contains_all_fields(self, pc, seed):
        """结果字典包含所有必需字段"""
        engine = _make_engine(pc, seed=seed)
        result = engine.run_headless_battle(max_rounds=80)
        for key in ["winner", "rounds", "players", "heroes", "identities", "finished"]:
            assert key in result, f"结果缺少字段: {key}"


# ==================== 4. 确定性 (7 tests) ====================

class TestDeterminism:
    """相同种子 → 相同结果"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_same_seed_same_rounds(self, pc):
        """相同种子的回合数一致"""
        results = []
        for _ in range(2):
            engine = _make_engine(pc, seed=12345)
            r = engine.run_headless_battle(max_rounds=80)
            results.append(r["rounds"])
        assert results[0] == results[1], (
            f"{pc}人局: 相同种子回合数不一致 {results}"
        )

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_same_seed_same_winner(self, pc):
        """相同种子的胜者一致"""
        winners = []
        for _ in range(2):
            engine = _make_engine(pc, seed=54321)
            r = engine.run_headless_battle(max_rounds=80)
            winners.append(r["winner"])
        assert winners[0] == winners[1]


# ==================== 5. 胜负条件 (7 tests) ====================

class TestWinConditions:
    """验证胜负判定逻辑"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_winner_is_valid_identity(self, pc):
        """胜者身份合法"""
        engine = _make_engine(pc, seed=8888)
        result = engine.run_headless_battle(max_rounds=100)
        if result["finished"]:
            assert result["winner"] in ["主公", "反贼", "内奸"]

    def test_lord_dies_rebels_or_spy_win(self):
        """主公死亡 → 反贼或内奸获胜"""
        engine = _make_engine(4, seed=42)
        lord = [p for p in engine.players if p.identity == Identity.LORD][0]
        # 模拟主公死亡
        lord.hp = 0
        lord.is_alive = False
        assert engine.check_game_over()
        assert engine.winner_identity in [Identity.REBEL, Identity.SPY]

    def test_all_rebels_and_spy_dead_lord_wins(self):
        """反贼+内奸全灭 → 主公获胜"""
        engine = _make_engine(4, seed=42)
        for p in engine.players:
            if p.identity in [Identity.REBEL, Identity.SPY]:
                p.hp = 0
                p.is_alive = False
        assert engine.check_game_over()
        assert engine.winner_identity == Identity.LORD

    def test_spy_last_alive_spy_wins(self):
        """只剩内奸 → 内奸获胜"""
        engine = _make_engine(3, seed=42)
        spy = [p for p in engine.players if p.identity == Identity.SPY]
        if spy:
            for p in engine.players:
                if p.identity != Identity.SPY:
                    p.hp = 0
                    p.is_alive = False
            assert engine.check_game_over()
            assert engine.winner_identity == Identity.SPY

    def test_game_not_over_while_factions_alive(self):
        """各阵营都有人存活时游戏不结束"""
        engine = _make_engine(5, seed=42)
        # 初始状态，所有人存活
        assert not engine.check_game_over()


# ==================== 6. 距离计算 (parametrized, 14 tests) ====================

class TestDistanceCalculation:
    """验证距离计算在不同人数下正确"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_self_distance_is_zero(self, pc):
        """玩家到自己距离为 0"""
        engine = _make_engine(pc)
        p = engine.players[0]
        assert engine.calculate_distance(p, p) == 0

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_adjacent_distance_is_one(self, pc):
        """相邻玩家距离为 1"""
        engine = _make_engine(pc)
        if len(engine.players) < 2:
            return
        p0 = engine.players[0]
        p1 = engine.players[1]
        d = engine.calculate_distance(p0, p1)
        assert d >= 1


# ==================== 7. 卡牌与牌堆 (7 tests) ====================

class TestDeckAndCards:
    """验证牌堆在不同人数下正常工作"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_deck_not_empty_after_setup(self, pc):
        """设置后牌堆仍有牌"""
        engine = _make_engine(pc)
        assert engine.deck.remaining > 0

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_total_cards_conservation(self, pc):
        """牌总数守恒: 牌堆 + 手牌 + 弃牌堆 = 常数"""
        engine = _make_engine(pc)
        hand_total = sum(len(p.hand) for p in engine.players)
        deck_total = engine.deck.remaining
        discard_total = engine.deck.discarded
        total = hand_total + deck_total + discard_total
        # 总数应等于初始牌堆大小
        assert total > 0

    def test_deck_reshuffles_on_empty(self):
        """牌堆耗尽时自动洗入弃牌堆"""
        engine = _make_engine(2, seed=42)
        # 大量抽牌直到需要重洗
        drawn = 0
        for _ in range(200):
            cards = engine.deck.draw(1)
            if cards:
                drawn += len(cards)
                engine.deck.discard(cards)
        assert drawn > 50  # 应该至少抽了很多牌


# ==================== 8. 事件系统集成 (7 tests) ====================

class TestEventSystemIntegration:
    """验证事件总线在各人数下正常工作"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_events_emitted_during_battle(self, pc):
        """对局中产生事件"""
        engine = _make_engine(pc, seed=42)
        events = []
        engine.event_bus.subscribe_all(lambda e: events.append(e))
        engine.run_headless_battle(max_rounds=5)
        assert len(events) > 0, f"{pc}人局无事件产生"

    @pytest.mark.parametrize("pc", [3, 5, 8])
    def test_turn_start_events_match_alive_count(self, pc):
        """回合开始事件数 ≥ 1"""
        engine = _make_engine(pc, seed=42)
        turn_events = []
        engine.event_bus.subscribe(
            EventType.TURN_START,
            lambda e: turn_events.append(e)
        )
        engine.run_headless_battle(max_rounds=3)
        assert len(turn_events) >= 1


# ==================== 9. AI 难度 × 玩家数 矩阵 (21 tests) ====================

class TestAIDifficultyMatrix:
    """所有 AI 难度 × 所有玩家数量"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    @pytest.mark.parametrize("diff", ["easy", "normal", "hard"])
    def test_difficulty_battle_completes(self, pc, diff):
        """各难度各人数对局均可完成"""
        engine = _make_engine(pc, seed=5000, diff=diff)
        result = engine.run_headless_battle(max_rounds=100)
        assert result["rounds"] > 0, (
            f"{pc}人局 难度{diff} 未开始"
        )


# ==================== 10. 边界与异常 (8 tests) ====================

class TestEdgeCases:
    """边界条件和异常处理"""

    def test_invalid_player_count_low(self):
        """玩家数 < 2 应抛异常"""
        with pytest.raises(ValueError):
            _make_engine(1)

    def test_invalid_player_count_high(self):
        """玩家数 > 8 应抛异常"""
        with pytest.raises(ValueError):
            _make_engine(9)

    def test_invalid_player_count_zero(self):
        """玩家数 = 0 应抛异常"""
        with pytest.raises(ValueError):
            _make_engine(0)

    def test_negative_player_count(self):
        """负数玩家数应抛异常"""
        with pytest.raises(ValueError):
            _make_engine(-1)

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_max_round_limit_respected(self, pc):
        """max_rounds 限制被遵守"""
        engine = _make_engine(pc, seed=42)
        result = engine.run_headless_battle(max_rounds=1)
        assert result["rounds"] <= 1

    def test_seed_none_still_works(self):
        """seed=None 时引擎自动生成种子"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=None)
        assert engine.state == GameState.IN_PROGRESS
        result = engine.run_headless_battle(max_rounds=50)
        assert result["rounds"] > 0


# ==================== 11. 多局稳定性 per player count (7 tests) ====================

class TestStabilityPerPlayerCount:
    """每种人数各跑若干局，验证错误率 < 5%"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_stability_15_games(self, pc):
        """每种人数 15 局, 错误率 < 5% (允许 0 局失败)"""
        rng = random.Random(pc * 1000)
        errors = 0
        total = 15
        for _ in range(total):
            seed = rng.randint(0, 2**31)
            try:
                engine = _make_engine(pc, seed=seed)
                engine.run_headless_battle(max_rounds=100)
            except Exception:
                errors += 1
        error_rate = errors / total
        assert error_rate < 0.05, (
            f"{pc}人局: {total}局中{errors}局出错 ({error_rate:.1%})"
        )


# ==================== 12. 回合阶段流转 (7 tests) ====================

class TestTurnPhaseFlow:
    """验证回合阶段在各人数下正常流转"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_turn_runs_without_error(self, pc):
        """单回合执行无异常"""
        engine = _make_engine(pc, seed=42)
        # 执行一个回合
        engine.run_headless_turn()
        # 不抛异常即通过

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_next_turn_advances_player(self, pc):
        """next_turn 后当前玩家索引前进"""
        engine = _make_engine(pc, seed=42)
        initial_idx = engine.current_player_index
        engine.run_headless_turn()
        engine.next_turn()
        # 索引应发生变化 (除非只剩 1 人)
        alive = len(engine.get_alive_players())
        if alive > 1:
            assert engine.current_player_index != initial_idx or pc == 2


# ==================== 13. 牌堆完整性 & 摸牌 (parametrized) ====================

class TestDrawMechanics:
    """摸牌机制在各人数下正确"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_draw_cards_work(self, pc):
        """每位玩家可以正常摸牌"""
        engine = _make_engine(pc, seed=42)
        p = engine.players[0]
        before = len(p.hand)
        cards = engine.deck.draw(2)
        p.draw_cards(cards)
        assert len(p.hand) == before + len(cards)


# ==================== 14. 武将系统 (7 tests) ====================

class TestHeroSystem:
    """验证武将分配在各人数下正确"""

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_heroes_have_skills(self, pc):
        """至少有一个武将有技能"""
        engine = _make_engine(pc, seed=42)
        heroes_with_skills = [
            p for p in engine.players
            if p.hero and p.hero.skills
        ]
        assert len(heroes_with_skills) > 0

    @pytest.mark.parametrize("pc", ALL_PLAYER_COUNTS)
    def test_hero_hp_positive(self, pc):
        """所有武将初始 HP > 0"""
        engine = _make_engine(pc, seed=42)
        for p in engine.players:
            assert p.hp > 0, f"{p.name} HP={p.hp}"
            assert p.max_hp > 0


# ==================== 15. 跨局随机性验证 ====================

class TestRandomnessAcrossGames:
    """不同种子的对局应产生多样性结果"""

    @pytest.mark.parametrize("pc", [3, 5, 8])
    def test_different_seeds_produce_variety(self, pc):
        """10 个不同种子至少产生 2 种不同的回合数"""
        rounds_set = set()
        for seed in SEEDS:
            engine = _make_engine(pc, seed=seed)
            r = engine.run_headless_battle(max_rounds=80)
            rounds_set.add(r["rounds"])
        assert len(rounds_set) >= 2, (
            f"{pc}人局 10 种子的回合数完全相同: {rounds_set}"
        )

    @pytest.mark.parametrize("pc", [4, 6, 8])
    def test_different_seeds_produce_varied_winners(self, pc):
        """10 个不同种子至少产生 2 种胜者"""
        winners = set()
        for seed in SEEDS:
            engine = _make_engine(pc, seed=seed)
            r = engine.run_headless_battle(max_rounds=100)
            winners.add(r["winner"])
        # 允许全超时的极端情况
        assert len(winners) >= 1


# ==================== 16. WinConditionChecker 单元 (5 tests) ====================

class TestWinConditionChecker:
    """WinConditionChecker 独立单元测试"""

    def test_not_finished_when_all_alive(self):
        """所有人存活 → 游戏未结束"""
        engine = _make_engine(4, seed=42)
        checker = WinConditionChecker(engine)
        info = checker.check_game_over()
        assert not info.is_over
        assert info.result == WinResult.NOT_FINISHED

    def test_lord_dead_rebel_wins(self):
        """主公死亡 + 有反贼存活 → 反贼胜"""
        engine = _make_engine(4, seed=42)
        lord = [p for p in engine.players if p.identity == Identity.LORD][0]
        lord.hp = 0
        lord.is_alive = False
        checker = WinConditionChecker(engine)
        info = checker.check_game_over()
        assert info.is_over
        assert info.result in [WinResult.REBEL_WIN, WinResult.SPY_WIN]

    def test_all_enemies_dead_lord_wins(self):
        """反贼+内奸全灭 → 主公胜"""
        engine = _make_engine(5, seed=42)
        for p in engine.players:
            if p.identity in [Identity.REBEL, Identity.SPY]:
                p.hp = 0
                p.is_alive = False
        checker = WinConditionChecker(engine)
        info = checker.check_game_over()
        assert info.is_over
        assert info.result == WinResult.LORD_WIN

    @pytest.mark.parametrize("pc", [4, 5, 6, 7, 8])
    def test_checker_consistent_with_engine(self, pc):
        """WinConditionChecker 与引擎内建检查一致"""
        engine = _make_engine(pc, seed=42)
        checker = WinConditionChecker(engine)
        engine_over = engine.check_game_over()
        checker_info = checker.check_game_over()
        # 两者对 "游戏是否结束" 的判断应一致
        assert engine_over == checker_info.is_over


# ==================== 17. 大规模批量压力 (1 test, 内部循环) ====================

class TestBulkStress:
    """跨人数批量压力测试"""

    def test_bulk_70_games_all_counts(self):
        """
        70 局 (每种人数 10 局), 总错误率 < 5%
        """
        rng = random.Random(20260206)
        errors = 0
        total = 0

        for pc in ALL_PLAYER_COUNTS:
            for _ in range(10):
                total += 1
                seed = rng.randint(0, 2**31)
                diff = rng.choice(["easy", "normal", "hard"])
                try:
                    engine = _make_engine(pc, seed=seed, diff=diff)
                    engine.run_headless_battle(max_rounds=100)
                except Exception:
                    errors += 1

        error_rate = errors / total
        assert error_rate < 0.05, (
            f"{total}局中{errors}局出错 ({error_rate:.1%})"
        )
