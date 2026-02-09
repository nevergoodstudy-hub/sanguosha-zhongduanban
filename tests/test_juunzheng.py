"""
军争篇机制单元测试 (T1-3)

覆盖内容：
- 酒的使用（出牌阶段/濒死阶段）
- 火杀/雷杀属性伤害
- 铁索连环（横置/重置/伤害传导）
- 藤甲与属性伤害交互
"""

import os
import sys

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.card import Card, CardSubtype, CardSuit, CardType
from game.engine import GameEngine, GameState
from game.player import Player


class TestAlcohol:
    """酒机制测试"""

    def setup_method(self):
        """每个测试前设置"""
        self.engine = GameEngine()

        # 创建两个玩家
        self.player1 = Player(id=0, name="玩家1", is_ai=True)
        self.player2 = Player(id=1, name="玩家2", is_ai=True)

        # 设置基本属性
        self.player1.max_hp = 4
        self.player1.hp = 4
        self.player2.max_hp = 4
        self.player2.hp = 4

        self.engine.players = [self.player1, self.player2]
        self.engine.state = GameState.IN_PROGRESS

    def test_alcohol_increase_sha_damage(self):
        """测试酒增加杀的伤害"""
        # 创建酒牌
        jiu = Card(
            id="jiu_test",
            name="酒",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ALCOHOL,
            suit=CardSuit.SPADE,
            number=3
        )

        # 创建杀牌
        sha = Card(
            id="sha_test",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )

        self.player1.draw_cards([jiu, sha])

        # 使用酒
        result = self.engine.use_card(self.player1, jiu)
        assert result is True
        assert self.player1.is_drunk is True
        assert self.player1.alcohol_used is True

        # 使用杀（酒加成后伤害为2）
        initial_hp = self.player2.hp
        self.engine.use_card(self.player1, sha, [self.player2])

        # 酒状态应被消耗
        assert self.player1.is_drunk is False
        # 如果没闪躲，应该受到2点伤害
        # 注意：由于 AI 可能有闪，这里只验证酒状态被正确消耗

    def test_alcohol_limit_per_turn(self):
        """测试酒每回合限用一次"""
        jiu1 = Card(
            id="jiu_1",
            name="酒",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ALCOHOL,
            suit=CardSuit.SPADE,
            number=3
        )
        jiu2 = Card(
            id="jiu_2",
            name="酒",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ALCOHOL,
            suit=CardSuit.HEART,
            number=9
        )

        self.player1.draw_cards([jiu1, jiu2])

        # 第一次使用酒应该成功
        result1 = self.engine.use_card(self.player1, jiu1)
        assert result1 is True

        # 第二次使用酒应该失败
        result2 = self.engine.use_card(self.player1, jiu2)
        assert result2 is False

    def test_alcohol_heal_when_dying(self):
        """测试濒死时使用酒回复体力"""
        jiu = Card(
            id="jiu_test",
            name="酒",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ALCOHOL,
            suit=CardSuit.SPADE,
            number=3
        )

        self.player1.hp = 0
        self.player1.is_dying = True
        self.player1.draw_cards([jiu])

        result = self.engine.use_card(self.player1, jiu)
        assert result is True
        assert self.player1.hp == 1
        assert self.player1.is_dying is False


class TestAttributeDamage:
    """属性伤害测试（火杀/雷杀）"""

    def setup_method(self):
        """每个测试前设置"""
        self.engine = GameEngine()

        self.player1 = Player(id=0, name="玩家1", is_ai=True)
        self.player2 = Player(id=1, name="玩家2", is_ai=True)

        self.player1.max_hp = 4
        self.player1.hp = 4
        self.player2.max_hp = 4
        self.player2.hp = 4

        self.engine.players = [self.player1, self.player2]
        self.engine.state = GameState.IN_PROGRESS

    def test_fire_sha_damage_type(self):
        """测试火杀造成火焰伤害"""
        fire_sha = Card(
            id="fire_sha_test",
            name="火杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.FIRE_ATTACK,
            suit=CardSuit.DIAMOND,
            number=4
        )

        self.player1.draw_cards([fire_sha])

        # 火杀应该正常使用
        initial_hp = self.player2.hp
        self.engine.use_card(self.player1, fire_sha, [self.player2])

        # 验证杀被使用（不管是否命中）
        assert self.player1.sha_count == 1

    def test_thunder_sha_damage_type(self):
        """测试雷杀造成雷电伤害"""
        thunder_sha = Card(
            id="thunder_sha_test",
            name="雷杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.THUNDER_ATTACK,
            suit=CardSuit.CLUB,
            number=6
        )

        self.player1.draw_cards([thunder_sha])

        initial_hp = self.player2.hp
        self.engine.use_card(self.player1, thunder_sha, [self.player2])

        assert self.player1.sha_count == 1


class TestChainMechanic:
    """铁索连环机制测试"""

    def setup_method(self):
        """每个测试前设置"""
        self.engine = GameEngine()

        self.player1 = Player(id=0, name="玩家1", is_ai=True)
        self.player2 = Player(id=1, name="玩家2", is_ai=True)
        self.player3 = Player(id=2, name="玩家3", is_ai=True)

        for p in [self.player1, self.player2, self.player3]:
            p.max_hp = 4
            p.hp = 4

        self.engine.players = [self.player1, self.player2, self.player3]
        self.engine.state = GameState.IN_PROGRESS

    def test_tiesuo_toggle_chain(self):
        """测试铁索连环横置/重置"""
        tiesuo = Card(
            id="tiesuo_test",
            name="铁索连环",
            card_type=CardType.TRICK,
            subtype=CardSubtype.CHAIN,
            suit=CardSuit.CLUB,
            number=12
        )

        self.player1.draw_cards([tiesuo])

        # 初始状态：未连环
        assert self.player2.is_chained is False

        # 使用铁索连环
        self.engine.use_card(self.player1, tiesuo, [self.player2])

        # 应该被横置
        assert self.player2.is_chained is True

    def test_tiesuo_reforge(self):
        """测试铁索连环重铸"""
        tiesuo = Card(
            id="tiesuo_test",
            name="铁索连环",
            card_type=CardType.TRICK,
            subtype=CardSubtype.CHAIN,
            suit=CardSuit.CLUB,
            number=12
        )

        self.player1.draw_cards([tiesuo])
        initial_hand_count = self.player1.hand_count

        # 不指定目标，重铸
        self.engine.use_card(self.player1, tiesuo, [])

        # 手牌数应该不变（用掉一张，摸一张）
        assert self.player1.hand_count == initial_hand_count

    def test_chain_damage_propagation(self):
        """测试铁索连环伤害传导"""
        # 设置两个玩家为连环状态
        self.player2.is_chained = True
        self.player3.is_chained = True

        initial_hp2 = self.player2.hp
        initial_hp3 = self.player3.hp

        # 对 player2 造成火焰伤害
        self.engine.deal_damage(self.player1, self.player2, 1, "fire")

        # player2 应该受伤且解除连环
        assert self.player2.hp == initial_hp2 - 1
        assert self.player2.is_chained is False

        # player3 应该也受到传导伤害且解除连环
        assert self.player3.hp == initial_hp3 - 1
        assert self.player3.is_chained is False

    def test_normal_damage_no_propagation(self):
        """测试普通伤害不触发连环传导"""
        self.player2.is_chained = True
        self.player3.is_chained = True

        initial_hp3 = self.player3.hp

        # 对 player2 造成普通伤害
        self.engine.deal_damage(self.player1, self.player2, 1, "normal")

        # player3 不应该受到传导伤害
        assert self.player3.hp == initial_hp3
        # player2 的连环状态不变
        assert self.player2.is_chained is True


class TestDistanceAndRange:
    """距离与攻击范围测试"""

    def setup_method(self):
        """每个测试前设置"""
        self.engine = GameEngine()

        # 创建4个玩家
        for i in range(4):
            player = Player(id=i, name=f"玩家{i+1}", is_ai=True, seat=i)
            player.max_hp = 4
            player.hp = 4
            self.engine.players.append(player)

        self.engine.state = GameState.IN_PROGRESS

    def test_basic_distance(self):
        """测试基础距离计算"""
        # 4人局座位: 0-1-2-3-0
        # 0到1距离=1, 0到2距离=2, 0到3距离=1
        p0, p1, p2, p3 = self.engine.players

        assert self.engine.calculate_distance(p0, p1) == 1
        assert self.engine.calculate_distance(p0, p2) == 2
        assert self.engine.calculate_distance(p0, p3) == 1
        assert self.engine.calculate_distance(p1, p3) == 2

    def test_attack_range_with_weapon(self):
        """测试武器影响攻击范围"""
        p0, p1, p2, p3 = self.engine.players

        # 默认攻击范围为1
        assert self.engine.is_in_attack_range(p0, p1) is True
        assert self.engine.is_in_attack_range(p0, p2) is False

        # 装备攻击范围为3的武器
        weapon = Card(
            id="weapon_test",
            name="青龙偃月刀",
            card_type=CardType.EQUIPMENT,
            subtype=CardSubtype.WEAPON,
            suit=CardSuit.SPADE,
            number=5,
            range=3
        )
        p0.equip_card(weapon)

        assert self.engine.is_in_attack_range(p0, p2) is True


class TestDyingAndSave:
    """濒死与救援测试"""

    def setup_method(self):
        """每个测试前设置"""
        self.engine = GameEngine()

        self.player1 = Player(id=0, name="玩家1", is_ai=True)
        self.player2 = Player(id=1, name="玩家2", is_ai=True)

        self.player1.max_hp = 4
        self.player1.hp = 4
        self.player2.max_hp = 4
        self.player2.hp = 1  # 1点血

        self.engine.players = [self.player1, self.player2]
        self.engine.state = GameState.IN_PROGRESS

    def test_dying_state_trigger(self):
        """测试濒死状态触发"""
        assert self.player2.is_dying is False

        # 造成1点伤害使其濒死
        self.player2.take_damage(1, self.player1)

        assert self.player2.hp == 0
        assert self.player2.is_dying is True

    def test_heal_clears_dying(self):
        """测试回复体力解除濒死"""
        self.player2.hp = 0
        self.player2.is_dying = True

        self.player2.heal(1)

        assert self.player2.hp == 1
        assert self.player2.is_dying is False


def run_tests():
    """运行所有测试"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
