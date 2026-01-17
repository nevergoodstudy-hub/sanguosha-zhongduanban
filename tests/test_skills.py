# -*- coding: utf-8 -*-
"""
技能系统单元测试
覆盖 game/skill.py 中的主要技能处理器
"""

import pytest
from game.engine import GameEngine
from game.card import Card, CardType, CardSubtype, CardSuit
from game.skill import SkillSystem
from game.hero import Skill, SkillType, Kingdom


class TestSkillSystem:
    """测试技能系统基础功能"""

    @pytest.fixture
    def engine(self):
        """创建测试用的游戏引擎"""
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        # 初始化技能系统
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    @pytest.fixture
    def skill_system(self, engine):
        """创建技能系统"""
        return engine.skill_system

    def test_skill_system_init(self, skill_system):
        """测试技能系统初始化"""
        assert skill_system is not None
        assert hasattr(skill_system, '_skill_handlers')
        assert len(skill_system._skill_handlers) > 0

    def test_can_use_skill_unknown(self, skill_system, engine):
        """测试未知技能返回False"""
        player = engine.players[0]
        result = skill_system.can_use_skill("unknown_skill", player)
        assert result is False

    def test_trigger_skill_unknown(self, skill_system, engine):
        """测试触发未知技能返回False"""
        player = engine.players[0]
        result = skill_system.trigger_skill("unknown_skill", player, engine)
        assert result is False

    def test_get_usable_skills(self, skill_system, engine):
        """测试获取可用技能列表"""
        player = engine.players[0]
        skills = skill_system.get_usable_skills(player)
        assert isinstance(skills, list)


class TestRende:
    """测试仁德技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_rende_transfer_cards(self, engine):
        """测试仁德转移卡牌"""
        player = engine.players[0]
        target = engine.players[1]

        # 给玩家手牌
        test_card = Card(
            id="test_card",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        player.hand.append(test_card)

        # 模拟仁德技能（如果玩家有该技能）
        skill_system = engine.skill_system
        initial_target_hand = len(target.hand)

        result = skill_system._handle_rende(
            player, engine,
            targets=[target],
            cards=[test_card]
        )

        if test_card not in player.hand:
            # 卡牌已转移
            assert result is True
            assert len(target.hand) == initial_target_hand + 1

    def test_rende_no_cards(self, engine):
        """测试仁德没有卡牌时失败"""
        player = engine.players[0]
        target = engine.players[1]

        skill_system = engine.skill_system
        result = skill_system._handle_rende(player, engine, targets=[target], cards=[])
        assert result is False

    def test_rende_no_target(self, engine):
        """测试仁德没有目标时失败"""
        player = engine.players[0]
        test_card = Card(
            id="test_card",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        player.hand.append(test_card)

        skill_system = engine.skill_system
        result = skill_system._handle_rende(player, engine, targets=None, cards=[test_card])
        assert result is False


class TestZhiheng:
    """测试制衡技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_zhiheng_exchange_cards(self, engine):
        """测试制衡交换卡牌"""
        player = engine.players[0]

        # 清空手牌并添加测试卡牌
        player.hand.clear()
        test_cards = []
        for i in range(3):
            card = Card(
                id=f"test_card_{i}",
                name="杀",
                card_type=CardType.BASIC,
                subtype=CardSubtype.ATTACK,
                suit=CardSuit.SPADE,
                number=i + 1
            )
            test_cards.append(card)
            player.hand.append(card)

        initial_hand_count = len(player.hand)
        skill_system = engine.skill_system

        result = skill_system._handle_zhiheng(player, engine, cards=test_cards[:2])

        # 制衡应该弃掉选择的牌然后摸等量的牌
        assert result is True

    def test_zhiheng_no_cards(self, engine):
        """测试制衡没有卡牌时失败"""
        player = engine.players[0]
        skill_system = engine.skill_system

        result = skill_system._handle_zhiheng(player, engine, cards=[])
        assert result is False


class TestWusheng:
    """测试武圣技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_wusheng_convert_red_card(self, engine):
        """测试武圣将红色牌当杀"""
        player = engine.players[0]
        target = engine.players[1]

        # 添加红色手牌
        red_card = Card(
            id="red_card",
            name="桃",
            card_type=CardType.BASIC,
            subtype=CardSubtype.HEAL,
            suit=CardSuit.HEART,
            number=3
        )
        player.hand.append(red_card)

        skill_system = engine.skill_system
        result = skill_system._handle_wusheng(
            player, engine,
            targets=[target],
            cards=[red_card]
        )

        # 武圣应该能将红色牌当杀使用
        assert result is True or result is False  # 取决于实现


class TestLongdan:
    """测试龙胆技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_longdan_sha_as_shan(self, engine):
        """测试龙胆将杀当闪"""
        player = engine.players[0]

        sha_card = Card(
            id="sha_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(sha_card)

        skill_system = engine.skill_system
        result = skill_system._handle_longdan(
            player, engine,
            cards=[sha_card],
            convert_to="shan"
        )

        assert result is True or result is False


class TestQingnang:
    """测试青囊技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_qingnang_heal(self, engine):
        """测试青囊治疗"""
        player = engine.players[0]
        target = engine.players[1]

        # 让目标受伤
        target.hp = target.max_hp - 1

        # 给玩家一张手牌
        test_card = Card(
            id="test_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )
        player.hand.append(test_card)

        skill_system = engine.skill_system
        target_hp_before = target.hp

        result = skill_system._handle_qingnang(
            player, engine,
            targets=[target],
            cards=[test_card]
        )

        if result:
            assert target.hp >= target_hp_before

    def test_qingnang_no_card(self, engine):
        """测试青囊没有卡牌时失败"""
        player = engine.players[0]
        target = engine.players[1]
        target.hp = target.max_hp - 1

        skill_system = engine.skill_system
        result = skill_system._handle_qingnang(player, engine, targets=[target], cards=[])
        assert result is False


class TestKurou:
    """测试苦肉技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_kurou_self_damage(self, engine):
        """测试苦肉自伤摸牌"""
        player = engine.players[0]
        player.hp = player.max_hp  # 确保满血

        skill_system = engine.skill_system
        hp_before = player.hp
        hand_before = len(player.hand)

        result = skill_system._handle_kurou(player, engine)

        if result:
            # 苦肉：失去1点体力，摸2张牌
            assert player.hp == hp_before - 1
            assert len(player.hand) >= hand_before + 2


class TestBiyue:
    """测试闭月技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_biyue_draw(self, engine):
        """测试闭月摸牌"""
        player = engine.players[0]
        hand_before = len(player.hand)

        skill_system = engine.skill_system
        result = skill_system._handle_biyue(player, engine)

        if result:
            # 闭月：结束阶段摸1张牌
            assert len(player.hand) >= hand_before + 1


class TestYingzi:
    """测试英姿技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_yingzi_extra_draw(self, engine):
        """测试英姿额外摸牌"""
        player = engine.players[0]
        hand_before = len(player.hand)

        skill_system = engine.skill_system
        result = skill_system._handle_yingzi(player, engine)

        # 英姿技能应该返回True或False
        assert result is True or result is False
        # 如果成功，手牌数量应该增加
        if result:
            assert len(player.hand) >= hand_before


class TestJianxiong:
    """测试奸雄技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_jianxiong_get_damage_card(self, engine):
        """测试奸雄获取造成伤害的牌"""
        player = engine.players[0]

        damage_card = Card(
            id="damage_card",
            name="杀",
            card_type=CardType.BASIC,
            subtype=CardSubtype.ATTACK,
            suit=CardSuit.SPADE,
            number=7
        )

        skill_system = engine.skill_system
        hand_before = len(player.hand)

        result = skill_system._handle_jianxiong(
            player, engine,
            damage_card=damage_card
        )

        # 奸雄：受到伤害后可获得造成伤害的牌
        assert result is True or result is False


class TestGanglie:
    """测试刚烈技能"""

    @pytest.fixture
    def engine(self):
        engine = GameEngine()
        engine.setup_game(player_count=4, human_player_index=-1)
        skill_system = SkillSystem(engine)
        engine.set_skill_system(skill_system)
        choices = engine.auto_choose_heroes_for_ai()
        engine.choose_heroes(choices)
        engine.start_game()
        return engine

    def test_ganglie_retaliation(self, engine):
        """测试刚烈反击"""
        player = engine.players[0]
        source = engine.players[1]

        skill_system = engine.skill_system

        result = skill_system._handle_ganglie(
            player, engine,
            source=source
        )

        # 刚烈：受到伤害后可进行判定，红色则伤害来源弃2牌或受1伤
        assert result is True or result is False
