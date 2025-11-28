# -*- coding: utf-8 -*-
"""
三国杀自动化对局测试
模拟完整的多人游戏对战，确保游戏流程无错误
"""

import sys
import os
import unittest
import random
import copy
from pathlib import Path
from typing import List, Dict, Optional
from io import StringIO

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.card import Card, CardType, CardSubtype, CardSuit, Deck
from game.hero import Hero, Skill, SkillType, Kingdom, HeroRepository
from game.player import Player, Identity, Equipment
from game.engine import GameEngine, GameState, GamePhase
from game.skill import SkillSystem
from ai.bot import AIBot, AIDifficulty


class AutoBattleSimulator:
    """自动对局模拟器"""
    
    def __init__(self, player_count: int, max_rounds: int = 100):
        """
        初始化模拟器
        
        Args:
            player_count: 玩家数量 (2-8)
            max_rounds: 最大回合数，防止死循环
        """
        self.player_count = player_count
        self.max_rounds = max_rounds
        self.engine: Optional[GameEngine] = None
        self.ai_bots: Dict[int, AIBot] = {}
        self.errors: List[str] = []
        self.logs: List[str] = []
        
    def setup_game(self) -> bool:
        """设置游戏"""
        try:
            self.engine = GameEngine()
            self.engine.setup_game(self.player_count, human_player_index=-1)  # -1表示全AI
            
            # 自动选择武将
            choices = self.engine.auto_choose_heroes_for_ai()
            self.engine.choose_heroes(choices)
            
            # 初始化AI
            for player in self.engine.players:
                difficulty = random.choice([AIDifficulty.EASY, AIDifficulty.NORMAL, AIDifficulty.HARD])
                bot = AIBot(player, difficulty)
                self.ai_bots[player.id] = bot
            
            # 开始游戏
            self.engine.start_game()
            return True
            
        except Exception as e:
            self.errors.append(f"游戏设置失败: {str(e)}")
            import traceback
            self.errors.append(traceback.format_exc())
            return False
    
    def run_single_turn(self, player: Player) -> bool:
        """执行单个回合"""
        try:
            if not player.is_alive:
                return True
            
            # 重置回合状态
            player.reset_turn()
            
            # 准备阶段
            self.engine.phase_prepare(player)
            
            # 判定阶段（暂时跳过延时锦囊判定）
            self.engine.phase = GamePhase.JUDGE
            
            # 摸牌阶段
            self.engine.phase_draw(player)
            
            # 出牌阶段
            self.engine.phase = GamePhase.PLAY
            if player.id in self.ai_bots:
                bot = self.ai_bots[player.id]
                bot.play_phase(player, self.engine)
            
            # 弃牌阶段
            self.engine.phase_discard(player)
            
            # 结束阶段
            self.engine.phase_end(player)
            
            return True
            
        except Exception as e:
            self.errors.append(f"回合执行失败 ({player.name}): {str(e)}")
            import traceback
            self.errors.append(traceback.format_exc())
            return False
    
    def run_game(self) -> Dict:
        """
        运行完整游戏
        
        Returns:
            游戏结果统计
        """
        if not self.setup_game():
            return {
                "success": False,
                "errors": self.errors,
                "rounds": 0
            }
        
        rounds = 0
        while not self.engine.check_game_over() and rounds < self.max_rounds:
            rounds += 1
            
            for player in self.engine.players:
                if self.engine.check_game_over():
                    break
                    
                if not player.is_alive:
                    continue
                
                if not self.run_single_turn(player):
                    return {
                        "success": False,
                        "errors": self.errors,
                        "rounds": rounds
                    }
            
            self.engine.round_count += 1
        
        # 统计结果
        alive_players = [p for p in self.engine.players if p.is_alive]
        dead_players = [p for p in self.engine.players if not p.is_alive]
        
        return {
            "success": len(self.errors) == 0,
            "errors": self.errors,
            "rounds": rounds,
            "winner": self.engine.winner_identity,
            "alive_count": len(alive_players),
            "dead_count": len(dead_players),
            "timeout": rounds >= self.max_rounds
        }


class TestAutoBattle(unittest.TestCase):
    """自动对局测试"""
    
    def test_2_player_battle(self):
        """测试2人对战"""
        simulator = AutoBattleSimulator(player_count=2, max_rounds=50)
        result = simulator.run_game()
        
        if not result["success"]:
            print(f"\n2人对战错误:")
            for err in result["errors"]:
                print(err)
        
        self.assertTrue(result["success"], f"2人对战失败: {result['errors']}")
        print(f"\n✓ 2人对战完成，共{result['rounds']}回合")
    
    def test_3_player_battle(self):
        """测试3人对战"""
        simulator = AutoBattleSimulator(player_count=3, max_rounds=50)
        result = simulator.run_game()
        
        if not result["success"]:
            print(f"\n3人对战错误:")
            for err in result["errors"]:
                print(err)
        
        self.assertTrue(result["success"], f"3人对战失败: {result['errors']}")
        print(f"\n✓ 3人对战完成，共{result['rounds']}回合")
    
    def test_4_player_battle(self):
        """测试4人对战"""
        simulator = AutoBattleSimulator(player_count=4, max_rounds=80)
        result = simulator.run_game()
        
        if not result["success"]:
            print(f"\n4人对战错误:")
            for err in result["errors"]:
                print(err)
        
        self.assertTrue(result["success"], f"4人对战失败: {result['errors']}")
        print(f"\n✓ 4人对战完成，共{result['rounds']}回合")
    
    def test_5_player_battle(self):
        """测试5人对战"""
        simulator = AutoBattleSimulator(player_count=5, max_rounds=100)
        result = simulator.run_game()
        
        if not result["success"]:
            print(f"\n5人对战错误:")
            for err in result["errors"]:
                print(err)
        
        self.assertTrue(result["success"], f"5人对战失败: {result['errors']}")
        print(f"\n✓ 5人对战完成，共{result['rounds']}回合")
    
    def test_6_player_battle(self):
        """测试6人对战"""
        simulator = AutoBattleSimulator(player_count=6, max_rounds=100)
        result = simulator.run_game()
        
        if not result["success"]:
            print(f"\n6人对战错误:")
            for err in result["errors"]:
                print(err)
        
        self.assertTrue(result["success"], f"6人对战失败: {result['errors']}")
        print(f"\n✓ 6人对战完成，共{result['rounds']}回合")
    
    def test_8_player_battle(self):
        """测试8人对战"""
        simulator = AutoBattleSimulator(player_count=8, max_rounds=150)
        result = simulator.run_game()
        
        if not result["success"]:
            print(f"\n8人对战错误:")
            for err in result["errors"]:
                print(err)
        
        self.assertTrue(result["success"], f"8人对战失败: {result['errors']}")
        print(f"\n✓ 8人对战完成，共{result['rounds']}回合")
    
    def test_multiple_battles(self):
        """测试多局连续对战"""
        battle_count = 5
        success_count = 0
        
        for i in range(battle_count):
            player_count = random.choice([2, 3, 4, 5, 6])
            simulator = AutoBattleSimulator(player_count=player_count, max_rounds=80)
            result = simulator.run_game()
            
            if result["success"]:
                success_count += 1
            else:
                print(f"\n第{i+1}局({player_count}人)失败:")
                for err in result["errors"]:
                    print(err)
        
        print(f"\n✓ 多局测试: {success_count}/{battle_count} 成功")
        self.assertEqual(success_count, battle_count)


class TestGameFlow(unittest.TestCase):
    """游戏流程测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
    
    def test_game_initialization(self):
        """测试游戏初始化"""
        for player_count in [2, 3, 4, 5, 6, 7, 8]:
            engine = GameEngine()
            engine.setup_game(player_count, human_player_index=-1)
            
            self.assertEqual(len(engine.players), player_count)
            self.assertEqual(engine.state, GameState.CHOOSING_HEROES)
            print(f"✓ {player_count}人游戏初始化成功")
    
    def test_identity_distribution(self):
        """测试身份分配"""
        identity_configs = {
            2: {Identity.LORD: 1, Identity.REBEL: 1},
            3: {Identity.LORD: 1, Identity.REBEL: 1, Identity.SPY: 1},
            4: {Identity.LORD: 1, Identity.LOYALIST: 1, Identity.REBEL: 1, Identity.SPY: 1},
            5: {Identity.LORD: 1, Identity.LOYALIST: 1, Identity.REBEL: 2, Identity.SPY: 1},
            6: {Identity.LORD: 1, Identity.LOYALIST: 1, Identity.REBEL: 3, Identity.SPY: 1},
            7: {Identity.LORD: 1, Identity.LOYALIST: 2, Identity.REBEL: 3, Identity.SPY: 1},
            8: {Identity.LORD: 1, Identity.LOYALIST: 2, Identity.REBEL: 4, Identity.SPY: 1},
        }
        
        for player_count, expected in identity_configs.items():
            engine = GameEngine()
            engine.setup_game(player_count, human_player_index=-1)
            
            # 统计身份分布
            actual = {}
            for player in engine.players:
                actual[player.identity] = actual.get(player.identity, 0) + 1
            
            self.assertEqual(actual, expected, f"{player_count}人身份分配错误")
            print(f"✓ {player_count}人身份分配正确")
    
    def test_hero_assignment(self):
        """测试武将分配"""
        engine = GameEngine()
        engine.setup_game(4, human_player_index=-1)
        
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        
        # 验证每个玩家都有武将
        for player in engine.players:
            self.assertIsNotNone(player.hero)
            self.assertGreater(player.max_hp, 0)
            print(f"✓ {player.name} -> {player.hero.name}")
    
    def test_initial_hand_cards(self):
        """测试初始手牌"""
        engine = GameEngine()
        engine.setup_game(4, human_player_index=-1)
        
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        
        for player in engine.players:
            self.assertEqual(player.hand_count, 4, f"{player.name} 初始手牌数错误")
        
        print("✓ 初始手牌分发正确（每人4张）")
    
    def test_deck_operations(self):
        """测试牌堆操作"""
        engine = GameEngine()
        engine.setup_game(4, human_player_index=-1)
        
        initial_count = engine.deck.remaining
        
        # 摸牌
        cards = engine.deck.draw(5)
        self.assertEqual(len(cards), 5)
        self.assertEqual(engine.deck.remaining, initial_count - 5)
        
        # 弃牌
        engine.deck.discard(cards)
        
        print(f"✓ 牌堆操作正确，剩余{engine.deck.remaining}张")


class TestCardUsage(unittest.TestCase):
    """卡牌使用测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=-1)
        choices = self.engine.auto_choose_heroes_for_ai()
        self.engine.choose_heroes(choices)
        self.engine.start_game()
    
    def test_use_sha(self):
        """测试使用杀"""
        player = self.engine.players[0]
        target = self.engine.players[1]
        
        # 创建一张杀
        sha = Card("test_sha", "杀", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 1)
        player.draw_cards([sha])
        
        # 使用杀
        try:
            self.engine.use_card(player, sha, [target])
            print("✓ 使用【杀】成功")
        except Exception as e:
            self.fail(f"使用【杀】失败: {e}")
    
    def test_use_tao(self):
        """测试使用桃"""
        player = self.engine.players[0]
        player.hp = player.max_hp - 1
        
        # 创建一张桃
        tao = Card("test_tao", "桃", CardType.BASIC, CardSubtype.HEAL, CardSuit.HEART, 2)
        player.draw_cards([tao])
        
        old_hp = player.hp
        self.engine.use_card(player, tao)
        
        self.assertEqual(player.hp, old_hp + 1)
        print("✓ 使用【桃】成功")
    
    def test_use_equipment(self):
        """测试装备武器"""
        player = self.engine.players[0]
        
        # 创建武器 (使用range参数)
        weapon = Card("test_weapon", "青龙偃月刀", CardType.EQUIPMENT, CardSubtype.WEAPON, 
                     CardSuit.SPADE, 5, range=3)
        player.draw_cards([weapon])
        
        self.engine.use_card(player, weapon)
        
        self.assertEqual(player.equipment.attack_range, 3)
        print("✓ 装备武器成功")


class TestDamageAndDeath(unittest.TestCase):
    """伤害和死亡测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=-1)
        choices = self.engine.auto_choose_heroes_for_ai()
        self.engine.choose_heroes(choices)
        self.engine.start_game()
    
    def test_deal_damage(self):
        """测试造成伤害"""
        source = self.engine.players[0]
        target = self.engine.players[1]
        
        old_hp = target.hp
        self.engine.deal_damage(source, target, 1)
        
        self.assertEqual(target.hp, old_hp - 1)
        print("✓ 伤害结算正确")
    
    def test_player_death(self):
        """测试玩家死亡"""
        source = self.engine.players[0]
        target = self.engine.players[1]
        
        # 清空手牌防止桃
        target.hand.clear()
        
        # 造成致命伤害
        self.engine.deal_damage(source, target, target.hp)
        
        self.assertTrue(not target.is_alive)
        print("✓ 玩家死亡处理正确")


class TestDistanceCalculation(unittest.TestCase):
    """距离计算测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=-1)
        choices = self.engine.auto_choose_heroes_for_ai()
        self.engine.choose_heroes(choices)
        self.engine.start_game()
    
    def test_base_distance(self):
        """测试基础距离"""
        p0 = self.engine.players[0]
        p1 = self.engine.players[1]
        p2 = self.engine.players[2]
        p3 = self.engine.players[3]
        
        # 4人场：相邻距离1，对面距离2
        d01 = self.engine.calculate_distance(p0, p1)
        d02 = self.engine.calculate_distance(p0, p2)
        d03 = self.engine.calculate_distance(p0, p3)
        
        self.assertEqual(d01, 1)
        self.assertEqual(d02, 2)
        self.assertEqual(d03, 1)
        print(f"✓ 距离计算正确: 0→1={d01}, 0→2={d02}, 0→3={d03}")
    
    def test_horse_distance_modifier(self):
        """测试坐骑距离修正"""
        p0 = self.engine.players[0]
        p1 = self.engine.players[1]
        
        # 装备-1马（攻击马）
        p0.equipment.horse_minus = Card("test_horse", "-1马", CardType.EQUIPMENT, 
                                        CardSubtype.HORSE_MINUS, CardSuit.SPADE, 5,
                                        distance_modifier=-1)
        
        d = self.engine.calculate_distance(p0, p1)
        # 基础距离1 - 1(攻击马) = 0，但最小为1
        self.assertEqual(d, 1)
        print("✓ 坐骑距离修正正确")


class TestWinConditions(unittest.TestCase):
    """胜利条件测试"""
    
    def test_rebel_wins_by_killing_lord(self):
        """测试反贼击杀主公获胜"""
        engine = GameEngine()
        engine.setup_game(4, human_player_index=-1)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        
        # 找到主公
        lord = next(p for p in engine.players if p.identity == Identity.LORD)
        
        # 模拟主公死亡
        lord.hp = 0
        lord.is_alive = False
        
        # 调用check_game_over触发判断
        game_over = engine.check_game_over()
        self.assertTrue(game_over)
        print("✓ 主公死亡判定正确")


def run_stress_test(battle_count: int = 20):
    """
    运行压力测试
    
    Args:
        battle_count: 对局数量
    """
    print(f"\n{'='*60}")
    print(f"三国杀自动化压力测试 - {battle_count}局")
    print(f"{'='*60}\n")
    
    results = {
        "total": battle_count,
        "success": 0,
        "failed": 0,
        "timeout": 0,
        "errors": []
    }
    
    for i in range(battle_count):
        player_count = random.choice([2, 3, 4, 5, 6, 7, 8])
        simulator = AutoBattleSimulator(player_count=player_count, max_rounds=100)
        result = simulator.run_game()
        
        status = "✓" if result["success"] else "✗"
        timeout_mark = " (超时)" if result.get("timeout") else ""
        
        print(f"[{i+1:3d}/{battle_count}] {player_count}人对战 {status} "
              f"回合:{result['rounds']:3d}{timeout_mark}")
        
        if result["success"]:
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].extend(result["errors"])
        
        if result.get("timeout"):
            results["timeout"] += 1
    
    print(f"\n{'='*60}")
    print(f"测试完成:")
    print(f"  总计: {results['total']}")
    print(f"  成功: {results['success']}")
    print(f"  失败: {results['failed']}")
    print(f"  超时: {results['timeout']}")
    print(f"{'='*60}")
    
    if results["errors"]:
        print("\n错误详情:")
        for err in results["errors"][:10]:  # 只显示前10个错误
            print(err)
    
    return results


if __name__ == "__main__":
    # 运行单元测试
    print("运行自动化对局测试...\n")
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestGameFlow))
    suite.addTests(loader.loadTestsFromTestCase(TestCardUsage))
    suite.addTests(loader.loadTestsFromTestCase(TestDamageAndDeath))
    suite.addTests(loader.loadTestsFromTestCase(TestDistanceCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestWinConditions))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoBattle))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 如果所有测试通过，运行压力测试
    if result.wasSuccessful():
        print("\n所有单元测试通过！开始压力测试...\n")
        run_stress_test(10)
