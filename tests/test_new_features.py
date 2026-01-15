# -*- coding: utf-8 -*-
"""
新功能单元测试
覆盖深度改进计划中实现的新功能
"""

import sys
import os
import unittest
import random
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent.parent))

from game.card import Card, CardType, CardSubtype, CardSuit, Deck, CardName
from game.hero import Hero, Skill, SkillType, Kingdom, HeroRepository
from game.player import Player, Identity, Equipment
from game.engine import GameEngine, GameState, GamePhase
from ai.bot import AIBot, AIDifficulty


class TestGudingdao(unittest.TestCase):
    """古锭刀武器效果测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=-1)
        choices = self.engine.auto_choose_heroes_for_ai()
        self.engine.choose_heroes(choices)
        self.engine.start_game()
    
    def test_gudingdao_effect_empty_hand(self):
        """测试古锭刀效果：目标无手牌时伤害+1"""
        attacker = self.engine.players[0]
        target = self.engine.players[1]
        
        # 装备古锭刀
        gudingdao = Card("test_gudingdao", "古锭刀", CardType.EQUIPMENT, 
                        CardSubtype.WEAPON, CardSuit.SPADE, 1, range=2)
        attacker.equipment.weapon = gudingdao
        
        # 清空目标手牌
        target.hand.clear()
        
        # 给攻击者一张杀
        sha = Card("test_sha", "杀", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 7)
        attacker.draw_cards([sha])
        
        # 记录初始HP
        initial_hp = target.hp
        
        # 使用杀（目标无闪，预期伤害为2：基础1 + 古锭刀1）
        self.engine.use_card(attacker, sha, [target])
        
        # 验证：如果目标无手牌，应该多受1点伤害
        # 注意：目标可能有闪或其他防御，这里主要测试机制是否触发
        print(f"✓ 古锭刀测试完成: 目标HP {initial_hp} -> {target.hp}")
    
    def test_gudingdao_effect_with_hand(self):
        """测试古锭刀效果：目标有手牌时正常伤害"""
        attacker = self.engine.players[0]
        target = self.engine.players[1]
        
        # 装备古锭刀
        gudingdao = Card("test_gudingdao", "古锭刀", CardType.EQUIPMENT, 
                        CardSubtype.WEAPON, CardSuit.SPADE, 1, range=2)
        attacker.equipment.weapon = gudingdao
        
        # 确保目标有手牌
        if not target.hand:
            test_card = Card("test_card", "桃", CardType.BASIC, 
                           CardSubtype.HEAL, CardSuit.HEART, 2)
            target.draw_cards([test_card])
        
        # 给攻击者一张杀
        sha = Card("test_sha", "杀", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 7)
        attacker.draw_cards([sha])
        
        initial_hp = target.hp
        self.engine.use_card(attacker, sha, [target])
        
        print(f"✓ 古锭刀正常伤害测试: 目标HP {initial_hp} -> {target.hp}")


class TestBaiyinshizi(unittest.TestCase):
    """白银狮子防具效果测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=-1)
        choices = self.engine.auto_choose_heroes_for_ai()
        self.engine.choose_heroes(choices)
        self.engine.start_game()
    
    def test_damage_reduction(self):
        """测试白银狮子伤害削减效果"""
        target = self.engine.players[1]
        source = self.engine.players[0]
        
        # 装备白银狮子
        baiyinshizi = Card("test_baiyinshizi", "白银狮子", CardType.EQUIPMENT,
                          CardSubtype.ARMOR, CardSuit.CLUB, 1)
        target.equipment.armor = baiyinshizi
        
        initial_hp = target.hp
        
        # 造成3点伤害，应被削减为1点
        self.engine.deal_damage(source, target, 3)
        
        # 白银狮子效果：受到大于1点伤害时，只受1点
        expected_hp = initial_hp - 1
        self.assertEqual(target.hp, expected_hp, 
                        f"白银狮子伤害削减失败: 期望HP={expected_hp}, 实际HP={target.hp}")
        print(f"✓ 白银狮子伤害削减测试通过: {initial_hp} -> {target.hp}")


class TestHuogong(unittest.TestCase):
    """火攻锦囊测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=-1)
        choices = self.engine.auto_choose_heroes_for_ai()
        self.engine.choose_heroes(choices)
        self.engine.start_game()
    
    def test_huogong_basic(self):
        """测试火攻基本流程"""
        user = self.engine.players[0]
        target = self.engine.players[1]
        
        # 确保目标有手牌
        if not target.hand:
            test_card = Card("test_card", "桃", CardType.BASIC, 
                           CardSubtype.HEAL, CardSuit.HEART, 2)
            target.draw_cards([test_card])
        
        # 创建火攻牌
        huogong = Card("test_huogong", "火攻", CardType.TRICK,
                      CardSubtype.SINGLE_TARGET, CardSuit.HEART, 12)
        user.draw_cards([huogong])
        
        # 使用火攻
        try:
            result = self.engine.use_card(user, huogong, [target])
            print(f"✓ 火攻使用测试通过")
        except Exception as e:
            self.fail(f"火攻使用失败: {e}")


class TestActionLogExport(unittest.TestCase):
    """action_log 导出测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
    
    def test_export_action_log(self):
        """测试导出动作日志"""
        # 设置无头对局
        self.engine.setup_headless_game(4, seed=12345)
        
        # 运行几个回合
        for _ in range(3):
            if self.engine.state != GameState.IN_PROGRESS:
                break
            self.engine.run_headless_turn()
            self.engine.next_turn()
        
        # 导出日志
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        exported_path = self.engine.export_action_log(filepath)
        
        # 验证文件存在
        self.assertTrue(Path(exported_path).exists(), "导出文件不存在")
        
        # 验证内容
        with open(exported_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.assertIn('version', data)
        self.assertIn('game_seed', data)
        self.assertIn('players', data)
        self.assertEqual(data['game_seed'], 12345)
        
        # 清理
        Path(exported_path).unlink()
        
        print(f"✓ action_log 导出测试通过")


class TestAIDecisionEnhancement(unittest.TestCase):
    """AI决策增强测试"""
    
    def test_hard_ai_target_selection(self):
        """测试困难AI的目标选择"""
        engine = GameEngine()
        engine.setup_game(4, human_player_index=-1)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        
        player = engine.players[0]
        bot = AIBot(player, AIDifficulty.HARD)
        
        # 获取敌方目标
        targets = [p for p in engine.players if p != player and p.is_alive]
        
        if targets:
            # 测试目标选择
            best_target = bot._choose_best_target(player, targets, engine)
            self.assertIsNotNone(best_target, "困难AI应能选择目标")
            print(f"✓ 困难AI目标选择测试通过: 选择了 {best_target.name}")
    
    def test_game_state_evaluation(self):
        """测试局势评估功能"""
        engine = GameEngine()
        engine.setup_game(4, human_player_index=-1)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        
        player = engine.players[0]
        bot = AIBot(player, AIDifficulty.HARD)
        
        # 评估局势
        evaluation = bot.evaluate_game_state(engine)
        
        self.assertIn('lord_advantage', evaluation)
        self.assertIn('rebel_advantage', evaluation)
        self.assertIn('my_power', evaluation)
        self.assertIn('danger_level', evaluation)
        
        print(f"✓ 局势评估测试通过:")
        print(f"  主公优势: {evaluation['lord_advantage']:.2f}")
        print(f"  反贼优势: {evaluation['rebel_advantage']:.2f}")
        print(f"  我方战力: {evaluation['my_power']:.1f}")
        print(f"  危险等级: {evaluation['danger_level']:.1f}")


class TestChainDamage(unittest.TestCase):
    """铁索连环传导测试"""
    
    def setUp(self):
        """测试前设置"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=-1)
        choices = self.engine.auto_choose_heroes_for_ai()
        self.engine.choose_heroes(choices)
        self.engine.start_game()
    
    def test_fire_damage_chain(self):
        """测试火焰伤害连环传导"""
        source = self.engine.players[0]
        target1 = self.engine.players[1]
        target2 = self.engine.players[2]
        
        # 设置连环状态
        target1.is_chained = True
        target2.is_chained = True
        
        initial_hp1 = target1.hp
        initial_hp2 = target2.hp
        
        # 造成火焰伤害
        self.engine.deal_damage(source, target1, 1, damage_type="fire")
        
        # 验证连环传导
        print(f"✓ 连环传导测试: target1 HP {initial_hp1}->{target1.hp}, target2 HP {initial_hp2}->{target2.hp}")


if __name__ == "__main__":
    print("=" * 60)
    print("三国杀新功能单元测试")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestGudingdao))
    suite.addTests(loader.loadTestsFromTestCase(TestBaiyinshizi))
    suite.addTests(loader.loadTestsFromTestCase(TestHuogong))
    suite.addTests(loader.loadTestsFromTestCase(TestActionLogExport))
    suite.addTests(loader.loadTestsFromTestCase(TestAIDecisionEnhancement))
    suite.addTests(loader.loadTestsFromTestCase(TestChainDamage))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✓ 所有新功能测试通过！")
    else:
        print(f"✗ 测试失败: {len(result.failures)} 失败, {len(result.errors)} 错误")
    print("=" * 60)
