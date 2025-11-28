# -*- coding: utf-8 -*-
"""
三国杀游戏单元测试
测试核心功能和游戏逻辑
"""

import sys
import os
import unittest
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from game.card import Card, CardType, CardSubtype, CardSuit, Deck, CardName
from game.hero import Hero, Skill, SkillType, Kingdom, HeroRepository
from game.player import Player, Identity, Equipment
from game.engine import GameEngine, GameState, GamePhase
from game.skill import SkillSystem
from ai.bot import AIBot, AIDifficulty


class TestCard(unittest.TestCase):
    """卡牌类测试"""
    
    def test_card_creation(self):
        """测试卡牌创建"""
        card = Card(
            id="sha_spade_A",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=1,
            description="对一名角色使用"
        )
        
        self.assertEqual(card.name, "杀")
        self.assertEqual(card.card_type, CardType.BASIC)
        self.assertEqual(card.suit, CardSuit.SPADE)
        self.assertEqual(card.number, 1)
    
    def test_card_properties(self):
        """测试卡牌属性"""
        # 红色牌
        red_card = Card(
            id="test_heart",
            name="测试",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.HEART,
            number=5
        )
        self.assertTrue(red_card.is_red)
        self.assertFalse(red_card.is_black)
        self.assertEqual(red_card.suit_symbol, "♥")
        
        # 黑色牌
        black_card = Card(
            id="test_spade",
            name="测试",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=10
        )
        self.assertTrue(black_card.is_black)
        self.assertFalse(black_card.is_red)
        self.assertEqual(black_card.suit_symbol, "♠")
    
    def test_card_number_display(self):
        """测试卡牌点数显示"""
        ace = Card("test", "测试", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 1)
        jack = Card("test", "测试", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 11)
        queen = Card("test", "测试", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 12)
        king = Card("test", "测试", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 13)
        
        self.assertEqual(ace.number_str, "A")
        self.assertEqual(jack.number_str, "J")
        self.assertEqual(queen.number_str, "Q")
        self.assertEqual(king.number_str, "K")


class TestDeck(unittest.TestCase):
    """牌堆类测试"""
    
    def setUp(self):
        """设置测试环境"""
        data_path = Path(__file__).parent.parent / "data" / "cards.json"
        self.deck = Deck(str(data_path))
    
    def test_deck_initialization(self):
        """测试牌堆初始化"""
        self.assertGreater(len(self.deck.draw_pile), 0)
        self.assertEqual(len(self.deck.discard_pile), 0)
    
    def test_draw_cards(self):
        """测试摸牌"""
        initial_count = len(self.deck.draw_pile)
        cards = self.deck.draw(5)
        
        self.assertEqual(len(cards), 5)
        self.assertEqual(len(self.deck.draw_pile), initial_count - 5)
    
    def test_discard_cards(self):
        """测试弃牌"""
        cards = self.deck.draw(3)
        self.deck.discard(cards)
        
        self.assertEqual(len(self.deck.discard_pile), 3)
    
    def test_reshuffle(self):
        """测试洗牌"""
        # 抽完所有牌
        while self.deck.remaining > 5:
            cards = self.deck.draw(5)
            self.deck.discard(cards)
        
        # 继续抽牌应该自动将弃牌堆洗入
        remaining = self.deck.remaining
        discarded = self.deck.discarded
        
        cards = self.deck.draw(remaining + 1)
        self.assertGreater(len(cards), 0)


class TestHero(unittest.TestCase):
    """武将类测试"""
    
    def setUp(self):
        """设置测试环境"""
        data_path = Path(__file__).parent.parent / "data" / "heroes.json"
        self.repo = HeroRepository(str(data_path))
    
    def test_hero_loading(self):
        """测试武将加载"""
        self.assertGreater(len(self.repo), 0)
    
    def test_get_hero(self):
        """测试获取武将"""
        liubei = self.repo.get_hero("liubei")
        self.assertIsNotNone(liubei)
        self.assertEqual(liubei.name, "刘备")
        self.assertEqual(liubei.kingdom, Kingdom.SHU)
    
    def test_hero_skills(self):
        """测试武将技能"""
        liubei = self.repo.get_hero("liubei")
        self.assertTrue(liubei.has_skill("rende"))
        self.assertTrue(liubei.has_skill("jijiang"))
        
        rende = liubei.get_skill("rende")
        self.assertIsNotNone(rende)
        self.assertEqual(rende.name, "仁德")
    
    def test_kingdom(self):
        """测试势力"""
        caocao = self.repo.get_hero("caocao")
        self.assertEqual(caocao.kingdom, Kingdom.WEI)
        self.assertEqual(caocao.kingdom_name, "魏")


class TestPlayer(unittest.TestCase):
    """玩家类测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.player = Player(id=0, name="测试玩家", is_ai=False)
        
        # 创建测试武将
        from game.hero import Skill, SkillType
        skills = [
            Skill(id="rende", name="仁德", description="测试技能",
                  skill_type=SkillType.ACTIVE)
        ]
        hero = Hero(
            id="test_hero",
            name="测试武将",
            kingdom=Kingdom.SHU,
            max_hp=4,
            gender="male",
            title="测试",
            skills=skills
        )
        self.player.set_hero(hero)
    
    def test_player_initialization(self):
        """测试玩家初始化"""
        self.assertEqual(self.player.hp, 4)
        self.assertEqual(self.player.max_hp, 4)
        self.assertTrue(self.player.is_alive)
    
    def test_player_with_lord_identity(self):
        """测试主公身份（额外1点体力）"""
        player = Player(id=1, name="主公", identity=Identity.LORD)
        
        hero = Hero(
            id="test_hero",
            name="测试",
            kingdom=Kingdom.SHU,
            max_hp=4,
            gender="male",
            title="测试",
            skills=[]
        )
        player.set_hero(hero)
        
        self.assertEqual(player.hp, 5)  # 主公+1
        self.assertEqual(player.max_hp, 5)
    
    def test_draw_cards(self):
        """测试摸牌"""
        card1 = Card("test1", "杀", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 1)
        card2 = Card("test2", "闪", CardType.BASIC, CardSubtype.DODGE, CardSuit.HEART, 2)
        
        self.player.draw_cards([card1, card2])
        
        self.assertEqual(self.player.hand_count, 2)
        self.assertTrue(self.player.has_card("杀"))
        self.assertTrue(self.player.has_card("闪"))
    
    def test_remove_card(self):
        """测试移除手牌"""
        card = Card("test", "杀", CardType.BASIC, CardSubtype.ATTACK, CardSuit.SPADE, 1)
        self.player.draw_cards([card])
        
        result = self.player.remove_card(card)
        
        self.assertTrue(result)
        self.assertEqual(self.player.hand_count, 0)
    
    def test_take_damage(self):
        """测试受到伤害"""
        initial_hp = self.player.hp
        self.player.take_damage(2)
        
        self.assertEqual(self.player.hp, initial_hp - 2)
    
    def test_dying_state(self):
        """测试濒死状态"""
        self.player.take_damage(10)  # 大量伤害
        
        self.assertTrue(self.player.is_dying)
        self.assertLessEqual(self.player.hp, 0)
    
    def test_heal(self):
        """测试回复体力"""
        self.player.take_damage(2)
        healed = self.player.heal(1)
        
        self.assertEqual(healed, 1)
        self.assertEqual(self.player.hp, self.player.max_hp - 1)
    
    def test_heal_max(self):
        """测试回复不超过上限"""
        healed = self.player.heal(10)
        
        self.assertEqual(healed, 0)  # 已经满血
        self.assertEqual(self.player.hp, self.player.max_hp)
    
    def test_hand_limit(self):
        """测试手牌上限"""
        self.assertEqual(self.player.hand_limit, self.player.hp)
        
        self.player.take_damage(2)
        self.assertEqual(self.player.hand_limit, self.player.hp)
    
    def test_equipment(self):
        """测试装备"""
        weapon = Card("weapon", "诸葛连弩", CardType.EQUIPMENT, 
                     CardSubtype.WEAPON, CardSuit.DIAMOND, 1, range=1)
        
        old = self.player.equip_card(weapon)
        
        self.assertIsNone(old)  # 没有旧装备
        self.assertIsNotNone(self.player.equipment.weapon)
        self.assertEqual(self.player.equipment.attack_range, 1)


class TestEquipment(unittest.TestCase):
    """装备类测试"""
    
    def test_weapon_equip(self):
        """测试装备武器"""
        equipment = Equipment()
        weapon = Card("weapon", "青龙偃月刀", CardType.EQUIPMENT,
                     CardSubtype.WEAPON, CardSuit.SPADE, 5, range=3)
        
        old = equipment.equip(weapon)
        
        self.assertIsNone(old)
        self.assertEqual(equipment.weapon, weapon)
        self.assertEqual(equipment.attack_range, 3)
    
    def test_armor_equip(self):
        """测试装备防具"""
        equipment = Equipment()
        armor = Card("armor", "八卦阵", CardType.EQUIPMENT,
                    CardSubtype.ARMOR, CardSuit.SPADE, 2)
        
        old = equipment.equip(armor)
        
        self.assertIsNone(old)
        self.assertEqual(equipment.armor, armor)
    
    def test_horse_equip(self):
        """测试装备坐骑"""
        equipment = Equipment()
        
        minus_horse = Card("horse_minus", "赤兔", CardType.EQUIPMENT,
                          CardSubtype.HORSE_MINUS, CardSuit.HEART, 5)
        plus_horse = Card("horse_plus", "的卢", CardType.EQUIPMENT,
                         CardSubtype.HORSE_PLUS, CardSuit.CLUB, 5)
        
        equipment.equip(minus_horse)
        equipment.equip(plus_horse)
        
        self.assertEqual(equipment.horse_minus, minus_horse)
        self.assertEqual(equipment.horse_plus, plus_horse)
        self.assertEqual(equipment.distance_to_others, -1)
        self.assertEqual(equipment.distance_from_others, 1)
    
    def test_replace_equipment(self):
        """测试替换装备"""
        equipment = Equipment()
        
        old_weapon = Card("old", "诸葛连弩", CardType.EQUIPMENT,
                         CardSubtype.WEAPON, CardSuit.DIAMOND, 1, range=1)
        new_weapon = Card("new", "青龙偃月刀", CardType.EQUIPMENT,
                         CardSubtype.WEAPON, CardSuit.SPADE, 5, range=3)
        
        equipment.equip(old_weapon)
        replaced = equipment.equip(new_weapon)
        
        self.assertEqual(replaced, old_weapon)
        self.assertEqual(equipment.weapon, new_weapon)


class TestGameEngine(unittest.TestCase):
    """游戏引擎测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.engine = GameEngine()
        self.engine.setup_game(4, human_player_index=0)
    
    def test_game_setup(self):
        """测试游戏设置"""
        self.assertEqual(len(self.engine.players), 4)
        self.assertEqual(self.engine.state, GameState.CHOOSING_HEROES)
    
    def test_identity_distribution(self):
        """测试身份分配"""
        # 确保有且只有一个主公
        lords = [p for p in self.engine.players if p.identity == Identity.LORD]
        self.assertEqual(len(lords), 1)
        
        # 确保第一个玩家是主公
        self.assertEqual(self.engine.players[0].identity, Identity.LORD)
    
    def test_hero_assignment(self):
        """测试武将分配"""
        # 分配武将
        choices = {
            0: "liubei",
            1: "caocao",
            2: "sunquan",
            3: "guanyu"
        }
        self.engine.choose_heroes(choices)
        
        for player in self.engine.players:
            self.assertIsNotNone(player.hero)
    
    def test_game_start(self):
        """测试游戏开始"""
        # 分配武将
        choices = {i: hero.id for i, hero in 
                  enumerate(self.engine.hero_repo.get_all_heroes()[:4])}
        self.engine.choose_heroes(choices)
        
        self.engine.start_game()
        
        self.assertEqual(self.engine.state, GameState.IN_PROGRESS)
        
        # 检查初始手牌
        for player in self.engine.players:
            self.assertEqual(player.hand_count, 4)
    
    def test_distance_calculation(self):
        """测试距离计算"""
        # 分配武将并开始游戏
        choices = {i: hero.id for i, hero in 
                  enumerate(self.engine.hero_repo.get_all_heroes()[:4])}
        self.engine.choose_heroes(choices)
        self.engine.start_game()
        
        # 相邻玩家距离为1
        p0, p1, p2, p3 = self.engine.players
        
        self.assertEqual(self.engine.calculate_distance(p0, p1), 1)
        self.assertEqual(self.engine.calculate_distance(p0, p3), 1)
        
        # 对面玩家距离为2
        self.assertEqual(self.engine.calculate_distance(p0, p2), 2)
    
    def test_attack_range(self):
        """测试攻击范围"""
        choices = {i: hero.id for i, hero in 
                  enumerate(self.engine.hero_repo.get_all_heroes()[:4])}
        self.engine.choose_heroes(choices)
        self.engine.start_game()
        
        p0 = self.engine.players[0]
        
        # 默认攻击范围是1
        targets = self.engine.get_targets_in_range(p0)
        self.assertEqual(len(targets), 2)  # 相邻两个玩家


class TestAIBot(unittest.TestCase):
    """AI机器人测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.player = Player(id=0, name="AI", is_ai=True, identity=Identity.LORD)
        self.bot = AIBot(self.player, AIDifficulty.NORMAL)
    
    def test_bot_creation(self):
        """测试AI创建"""
        self.assertEqual(self.bot.difficulty, AIDifficulty.NORMAL)
        self.assertEqual(self.bot.player, self.player)
    
    def test_difficulty_levels(self):
        """测试不同难度级别"""
        easy_bot = AIBot(self.player, AIDifficulty.EASY)
        normal_bot = AIBot(self.player, AIDifficulty.NORMAL)
        hard_bot = AIBot(self.player, AIDifficulty.HARD)
        
        self.assertEqual(easy_bot.difficulty, AIDifficulty.EASY)
        self.assertEqual(normal_bot.difficulty, AIDifficulty.NORMAL)
        self.assertEqual(hard_bot.difficulty, AIDifficulty.HARD)


class TestSkillSystem(unittest.TestCase):
    """技能系统测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.engine = GameEngine()
        self.engine.setup_game(2, human_player_index=0)
        self.skill_system = SkillSystem(self.engine)
        self.engine.set_skill_system(self.skill_system)
    
    def test_skill_check(self):
        """测试技能可用性检查"""
        # 设置武将
        self.engine.choose_heroes({0: "sunquan", 1: "caocao"})
        self.engine.start_game()
        
        player = self.engine.players[0]  # 孙权
        
        # 制衡需要手牌
        can_use = self.skill_system.can_use_skill("zhiheng", player)
        self.assertTrue(can_use)  # 有初始手牌
    
    def test_skill_usage_limit(self):
        """测试技能使用次数限制"""
        self.engine.choose_heroes({0: "sunquan", 1: "caocao"})
        self.engine.start_game()
        
        player = self.engine.players[0]
        
        # 使用一次制衡
        player.skill_used["zhiheng"] = 1
        
        # 制衡每回合限一次
        can_use = self.skill_system.can_use_skill("zhiheng", player)
        self.assertFalse(can_use)


class TestGameScenarios(unittest.TestCase):
    """游戏场景测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.engine = GameEngine()
    
    def test_two_player_game(self):
        """测试2人游戏"""
        self.engine.setup_game(2, 0)
        self.assertEqual(len(self.engine.players), 2)
        
        # 身份：主公 vs 反贼
        identities = [p.identity for p in self.engine.players]
        self.assertIn(Identity.LORD, identities)
        self.assertIn(Identity.REBEL, identities)
    
    def test_three_player_game(self):
        """测试3人游戏"""
        self.engine.setup_game(3, 0)
        self.assertEqual(len(self.engine.players), 3)
        
        # 身份：主公、反贼、内奸
        identities = [p.identity for p in self.engine.players]
        self.assertIn(Identity.LORD, identities)
    
    def test_four_player_game(self):
        """测试4人游戏"""
        self.engine.setup_game(4, 0)
        self.assertEqual(len(self.engine.players), 4)
        
        # 身份：主公、忠臣、反贼、内奸
        identities = [p.identity for p in self.engine.players]
        self.assertEqual(len(set(identities)), 4)


class TestVictoryConditions(unittest.TestCase):
    """胜利条件测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.engine = GameEngine()
        self.engine.setup_game(4, 0)
        
        # 设置武将
        heroes = list(self.engine.hero_repo.get_all_heroes()[:4])
        for i, player in enumerate(self.engine.players):
            import copy
            player.set_hero(copy.deepcopy(heroes[i]))
    
    def test_lord_death_rebel_wins(self):
        """测试主公死亡反贼获胜"""
        # 找到主公
        lord = None
        for p in self.engine.players:
            if p.identity == Identity.LORD:
                lord = p
                break
        
        # 主公死亡
        lord.die()
        
        # 检查游戏结束
        self.engine.check_game_over()
        
        self.assertEqual(self.engine.state, GameState.FINISHED)
        self.assertEqual(self.engine.winner_identity, Identity.REBEL)
    
    def test_all_enemies_dead_lord_wins(self):
        """测试所有敌人死亡主公获胜"""
        # 杀死所有反贼和内奸
        for p in self.engine.players:
            if p.identity in [Identity.REBEL, Identity.SPY]:
                p.die()
        
        # 检查游戏结束
        self.engine.check_game_over()
        
        self.assertEqual(self.engine.state, GameState.FINISHED)
        self.assertEqual(self.engine.winner_identity, Identity.LORD)


def run_tests():
    """运行所有测试"""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
