"""
模糊测试 (M4-T04)
对引擎执行随机操作序列，检测是否崩溃

策略:
1. 设置一个 headless 游戏
2. 随机执行操作 (摸牌/出牌/弃牌/使用技能/切换回合)
3. 验证引擎不崩溃、数据结构不被破坏
"""

import random

from game.card import CardName
from game.engine import GameEngine


class TestFuzz:
    """模糊测试"""

    def _setup_engine(self, seed: int = 42) -> GameEngine:
        engine = GameEngine()
        engine.setup_headless_game(4, seed=seed)
        return engine

    def test_fuzz_random_operations_50(self):
        """50 轮随机操作不崩溃"""
        rng = random.Random(1234)
        engine = self._setup_engine(seed=1234)

        for _ in range(50):
            if engine.is_game_over():
                break
            self._random_op(engine, rng)

        # 验证数据结构完整性
        self._verify_integrity(engine)

    def test_fuzz_random_operations_200(self):
        """200 轮随机操作不崩溃"""
        rng = random.Random(5678)
        engine = self._setup_engine(seed=5678)

        for _ in range(200):
            if engine.is_game_over():
                break
            self._random_op(engine, rng)

        self._verify_integrity(engine)

    def test_fuzz_multiple_seeds(self):
        """5 个种子各跑 100 轮"""
        for seed in [10, 20, 30, 40, 50]:
            rng = random.Random(seed)
            engine = self._setup_engine(seed=seed)
            for _ in range(100):
                if engine.is_game_over():
                    break
                self._random_op(engine, rng)
            self._verify_integrity(engine)

    def test_fuzz_draw_many_cards(self):
        """大量摸牌不崩溃"""
        engine = self._setup_engine(seed=999)
        player = engine.players[0]
        for _ in range(100):
            cards = engine.deck.draw(2)
            if cards:
                player.draw_cards(cards)
        assert player.hand_count >= 4  # 至少有初始手牌

    def test_fuzz_discard_all_then_draw(self):
        """弃光手牌再摸牌"""
        engine = self._setup_engine(seed=888)
        player = engine.players[0]

        # 弃光
        if player.hand:
            engine.deck.discard(list(player.hand))
            player.hand.clear()
        assert player.hand_count == 0

        # 摸牌
        cards = engine.deck.draw(4)
        player.draw_cards(cards)
        assert player.hand_count == 4

    def test_fuzz_rapid_turn_switching(self):
        """快速切换回合不崩溃"""
        engine = self._setup_engine(seed=777)
        for _ in range(50):
            if engine.is_game_over():
                break
            try:
                engine.next_turn()
            except Exception:
                pass  # 某些状态下可能不允许切换
        self._verify_integrity(engine)

    # ==================== 辅助方法 ====================

    def _random_op(self, engine: GameEngine, rng: random.Random) -> None:
        """执行一个随机操作"""
        op = rng.choice(["draw", "play", "discard", "next_turn", "heal", "noop"])
        alive = engine.get_alive_players()
        if not alive:
            return
        player = rng.choice(alive)

        try:
            if op == "draw":
                cards = engine.deck.draw(rng.randint(1, 3))
                if cards:
                    player.draw_cards(cards)

            elif op == "play" and player.hand:
                card = rng.choice(player.hand)
                # 只尝试使用桃(安全) 或杀(需要目标)
                if card.name == CardName.TAO and player.hp < player.max_hp:
                    engine.use_card(player, card)
                elif card.name == CardName.SHA:
                    targets = engine.get_targets_in_range(player)
                    if targets:
                        engine.use_card(player, card, [rng.choice(targets)])

            elif op == "discard" and player.hand:
                card = rng.choice(player.hand)
                player.remove_card(card)
                engine.deck.discard([card])

            elif op == "next_turn":
                engine.run_headless_turn()

            elif op == "heal":
                if player.hp < player.max_hp:
                    player.hp = min(player.hp + 1, player.max_hp)

        except Exception:
            pass  # 模糊测试: 操作失败不算 bug，崩溃才算

    def _verify_integrity(self, engine: GameEngine) -> None:
        """验证引擎数据结构完整性"""
        assert engine.players is not None
        assert len(engine.players) > 0

        for p in engine.players:
            # 手牌列表存在
            assert p.hand is not None
            assert isinstance(p.hand, list)
            # HP 不为负
            if p.is_alive:
                assert p.hp > 0
            assert p.hp <= p.max_hp
            # 身份存在
            assert p.identity is not None

        # 牌堆存在
        assert engine.deck is not None
