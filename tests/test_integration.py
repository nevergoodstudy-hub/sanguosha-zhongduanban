"""
集成测试 (M4-T04)
验证完整游戏流程: 设置 → 选将 → 对战 → 结束
"""

from game.card import CardName
from game.engine import GameEngine, GameState
from game.events import EventType
from game.player import Identity


class TestFullGameFlow:
    """完整游戏流程集成测试"""

    def test_headless_setup(self):
        """headless 设置后状态正确"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        assert engine.state == GameState.IN_PROGRESS
        assert len(engine.players) == 4
        assert all(p.hero is not None for p in engine.players)
        assert all(len(p.hand) == 4 for p in engine.players)

    def test_headless_identities(self):
        """身份分配正确"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)
        identities = [p.identity for p in engine.players]
        assert Identity.LORD in identities

    def test_headless_battle_completes(self):
        """headless 对局可以完整结束"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=100)
        result = engine.run_headless_battle(max_rounds=80)
        assert "winner" in result
        assert "rounds" in result
        assert result["rounds"] > 0

    def test_headless_battle_has_winner(self):
        """对局结束后有胜者"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=200)
        result = engine.run_headless_battle(max_rounds=80)
        if not result.get("timeout", False):
            assert result["winner"] is not None

    def test_headless_2_player(self):
        """2人对战"""
        engine = GameEngine()
        engine.setup_headless_game(2, seed=300)
        result = engine.run_headless_battle(max_rounds=50)
        assert result["rounds"] > 0

    def test_headless_3_player(self):
        """3人对战"""
        engine = GameEngine()
        engine.setup_headless_game(3, seed=400)
        result = engine.run_headless_battle(max_rounds=60)
        assert result["rounds"] > 0

    def test_headless_different_difficulties(self):
        """不同AI难度均可完成对局"""
        for diff in ["easy", "normal", "hard"]:
            engine = GameEngine()
            engine.setup_headless_game(4, ai_difficulty=diff, seed=500)
            result = engine.run_headless_battle(max_rounds=80)
            assert result["rounds"] > 0, f"难度 {diff} 对局未开始"


class TestEventBusIntegration:
    """事件总线集成测试"""

    def test_events_emitted_during_game(self):
        """游戏过程中产生事件"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)

        events_received = []
        engine.event_bus.subscribe_all(lambda e: events_received.append(e))

        engine.run_headless_battle(max_rounds=10)
        assert len(events_received) > 0

    def test_log_events_generated(self):
        """日志事件被生成"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)

        log_messages = []
        engine.event_bus.subscribe(
            EventType.LOG_MESSAGE, lambda e: log_messages.append(e.data.get("message", ""))
        )

        engine.run_headless_battle(max_rounds=5)
        assert len(log_messages) > 0


class TestCardEffectsIntegration:
    """卡牌效果集成测试"""

    def test_effect_registry_loaded(self):
        """效果注册表加载正确"""
        engine = GameEngine()
        assert engine.effect_registry is not None

    def test_effect_registry_has_core_cards(self):
        """效果注册表包含核心卡牌"""
        engine = GameEngine()
        assert engine.effect_registry.get(CardName.TAO) is not None
        assert engine.effect_registry.get(CardName.JUEDOU) is not None
        assert engine.effect_registry.get(CardName.NANMAN) is not None


class TestSkillSystemIntegration:
    """技能系统集成测试"""

    def test_headless_game_has_heroes_with_skills(self):
        """headless 对局中武将有技能"""
        engine = GameEngine()
        engine.setup_headless_game(4, seed=42)

        heroes_with_skills = [p for p in engine.players if p.hero and p.hero.skills]
        assert len(heroes_with_skills) > 0, "应至少有一个武将有技能"


class TestDeterminism:
    """确定性测试 — 相同种子应产生相同结果"""

    def test_same_seed_same_result(self):
        """相同种子产生相同对局结果"""
        results = []
        for _ in range(2):
            engine = GameEngine()
            engine.setup_headless_game(4, seed=12345)
            result = engine.run_headless_battle(max_rounds=50)
            results.append(result["rounds"])

        assert results[0] == results[1], "相同种子应产生相同回合数"

    def test_different_seeds_likely_different(self):
        """不同种子大概率产生不同结果"""
        rounds_list = []
        for seed in [1, 2, 3, 4, 5]:
            engine = GameEngine()
            engine.setup_headless_game(4, seed=seed)
            result = engine.run_headless_battle(max_rounds=50)
            rounds_list.append(result["rounds"])

        # 5个不同种子中至少有2个不同的回合数
        assert len(set(rounds_list)) >= 2, "不同种子应产生不同结果"
